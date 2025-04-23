#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# In this file it is permitted to catch exceptions on a broad basis since there
# are many things that can go wrong with file handling and xml parsing:
#    pylint: disable=bare-except,broad-except
# We're not quite at the level of documenting all the classes and functions yet :-)
#    pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring
# It'll be a while before we refactor this file, but when we do then these should be reenabled again!
#    pylint: disable=too-many-lines,too-many-statements,too-many-arguments,too-many-locals
#    pylint: disable=too-many-nested-blocks,too-many-branches
# logging strings, we don't log enough to worry about lazy evaluation
#    pylint: enable=logging-format-interpolation,logging-not-lazy

'''
Create pdf files from CEWE .mcf photo books (cewe-fotobuch)
version 0.11 (Dec 2019)

This script reads CEWE .mcf and .mcfx files using the lxml library
and compiles a pdf file using the reportlab python pdf library.
Execute from same path as .mcf file!

Only basic elements such as images and text are supported.
The feature support is neither complete nor fully correct.
Results may be wrong, incomplete or not produced at all.
This script doesn't work according to the original format
specification but according to estimated meaning.
Feel free to improve!

The script was tested to run with A4 books from CEWE
tested
dm-Fotowelt: compatibilityVersion="6.4.2" programversion="7.0.1" programversionBuild="20191025"

documentations:
-reportlab: www.reportlab.com/software/opensource/
-lxml: http://lxml.de/tutorial.html
-PIL: http://effbot.org/imagingbook/image.htm

--

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


# extend the search path so Cairo will find its dlls.
# only needed when the program is frozen (i.e. compiled).
import sys

import logging
import logging.config

import os.path
import os
import tempfile
import html

import gc

import argparse  # to parse arguments
import configparser  # to read config file, see https://docs.python.org/3/library/configparser.html

from enum import Enum
from io import BytesIO
from math import sqrt, floor

from pathlib import Path

import reportlab.lib.pagesizes
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table
# from reportlab.lib.styles import getSampleStyleSheet

import PIL

from packaging.version import parse as parse_version
from lxml import etree

from ceweInfo import CeweInfo, AlbumInfo, ProductStyle
from clipArt import getClipConfig, loadClipart, readClipArtConfigXML
from colorFrame import ColorFrame
from configUtils import getConfigurationBool, getConfigurationInt
from extraLoggers import mustsee, configlogger, VerifyMessageCounts, printMessageCountSummaries
from fontHandling import getMissingFontSubstitute, findAndRegisterFonts
from imageUtils import autorot
from lineScales import LineScales
from mcfx import unpackMcfx
from passepartout import Passepartout
from pathutils import findFileInDirs
from text import AppendItemTextInStyle, AppendSpanEnd, AppendSpanStart, AppendText, CollectFontInfo, CreateParagraphStyle, Dequote, noteFontSubstitution


# PageType is a concept for processing in this code, not something used by CEWE
class PageType(Enum):
    Unknown = 0 # this must be an error
    Normal = 1
    SingleSide = 2 # don't quite know what this is yet
    Cover = 3 # front / back cover
    EmptyPage = 4 # the intentional blanks inside the front and back covers (both have pagenr 0)
    BackInsideCover = 5 # the obligatory empty page to the right of the last page in keep double pages

    def __str__(self):
        return self.name # to print the enum name without the class


# work around a breaking change in pil 10.0.0, see
#   https://stackoverflow.com/questions/76616042/attributeerror-module-pil-image-has-no-attribute-antialias
if parse_version(PIL.__version__) >= parse_version('9.1.0'):
    # PIL.Image.LANCZOS was claimed closer to the old ANTIALIAS than PIL.Image.Resampling.LANCZOS
    # although you can find text which claims the latter is best (and also that the two LANCZOS
    # definitions are in fact identical!)
    pil_antialias = PIL.Image.LANCZOS  # pylint: disable=no-member
else:
    pil_antialias = PIL.Image.ANTIALIAS  # pylint: disable=no-member

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Running in a PyInstaller bundle, ref https://pyinstaller.org/en/stable/runtime-information.html#run-time-information
    # Add the local directory to the PATH. This is needed for compiled (i.e. frozen)
    #  programs on Windows to find dlls (cairo dlls, in particular).
    realpath = os.path.realpath(sys.argv[0])
    exename = os.path.basename(realpath)
    dllpath = os.path.dirname(realpath)
    print(f"Frozen python {exename} running from {dllpath}")
    if dllpath not in os.environ["PATH"]:
        print(f"Adding {dllpath} to PATH")
        if not os.environ["PATH"].endswith(os.pathsep):
            os.environ["PATH"] += os.pathsep
        os.environ["PATH"] += dllpath

# make it possible for PIL.Image to open .heic files if the album editor stores them directly
# ref https://github.com/bash0/cewe2pdf/issues/130
try:
    from pillow_heif import register_heif_opener # the absence of heif handling is handled so pylint: disable=import-error
    register_heif_opener()
except ModuleNotFoundError as heifex:
    logging.warning(f"{heifex.msg}: direct use of .heic images is not available without pillow_heif available")

# ### settings ####
image_res = 150  # dpi  The resolution of normal images will be reduced to this value, if it is higher.
bg_res = 150  # dpi The resolution of background images will be reduced to this value, if it is higher.
image_quality = 86  # 0=worst, 100=best. This is the JPEG quality option.
# ##########

# .mcf units are 0.1 mm
# Tabs seem to be in 8mm pitch
tab_pitch = 80

f = reportlab.lib.pagesizes.mm/10 # == 72/254, converts from mcf (unit=0.1mm) to reportlab (unit=inch/72)

tempFileList = []  # we need to remove all the temporary files at the end

# reportlab defaults
# pdf_styles = getSampleStyleSheet()
# pdf_styleN = pdf_styles['Normal']
pdf_flowableList = []

clipartDict = dict[int, str]()    # a dictionary for clipart element IDs to file name
clipartPathList = tuple[str]()
passepartoutDict = None    # will be dict[int, str] for passepartout designElementIDs to file name
passepartoutFolders = tuple[str]() # global variable with the folders for passepartout frames
defaultConfigSection = None


def getPageElementForPageNumber(fotobook, pageNumber):
    return fotobook.find(f"./page[@pagenr='{floor(2 * (pageNumber / 2))}']")


# This is only used for the <background .../> tags. The stock backgrounds use this element.
def processBackground(backgroundTags, bg_notFoundDirList, cewe_folder, backgroundLocations,  # noqa: C901
                      productstyle, pagetype, pdf, ph, pw):
    areaHeight = ph
    areaWidth = pw
    areaXOffset = 0

    if pagetype == PageType.EmptyPage:
        # EmptyPage is used when we're processing the inside cover / first page pair
        # for the second time after already processing it once as SingleSide
        if AlbumInfo.isAlbumSingleSide(productstyle):
            # don't draw the inside cover pages at all (both with pagenr="0" but at page numbers 1 and pagecount-1)
            return
        if AlbumInfo.isAlbumDoubleSide(productstyle):
            # if we just return here, then everything looks "nice" because this inside
            # front cover page comes out with the background of the first inner side.
            # But "nice" is not the same as the cewe album. If you want white inside cover pages, set the ini file
            # option to True and continue to output the page with the background that the empty page defines
            areaWidth = areaWidth / 2

    if pagetype == PageType.BackInsideCover:
        if AlbumInfo.isAlbumSingleSide(productstyle):
            # don't draw the inside cover pages at all (both with pagenr="0" but at page numbers 1 and pagecount-1)
            return
        if AlbumInfo.isAlbumDoubleSide(productstyle):
            areaWidth = areaWidth / 2
            areaXOffset = areaXOffset + areaWidth

    if pagetype in [PageType.EmptyPage,PageType.BackInsideCover] and not getConfigurationBool(defaultConfigSection, "insideCoverWhite", "False"):
        # return without drawing the background, thus accepting whatever was underneath. If the config option
        # is set to true then the inside cover pages will be set to the cewe specified default, white
        return

    if backgroundTags is not None and len(backgroundTags) > 0:
        # look for a tag that has an alignment attribute
        for curTag in backgroundTags:
            if curTag.get('alignment') is not None:
                backgroundTag = curTag
                break

        if pagetype == PageType.Normal and AlbumInfo.isAlbumDoubleSide(productstyle) and backgroundTag.get('alignment') == "3":
            areaWidth = areaWidth / 2
            areaXOffset = areaXOffset + areaWidth

        if (cewe_folder and backgroundTag is not None
                and backgroundTag.get('designElementId') is not None):
            bg = backgroundTag.get('designElementId')
            # example: fading="0" hue="270" rotation="0" type="1"
            backgroundFading = 0 # backgroundFading not used yet pylint: disable=unused-variable # noqa: F841
            if "fading" in backgroundTag.attrib:
                if float(backgroundTag.get('fading')) != 0:
                    logging.warning(f"value of background attribute not supported: fading = {backgroundTag.get('fading')}")
            backgroundHue = 0 # backgroundHue not used yet pylint: disable=unused-variable # noqa: F841
            if "hue" in backgroundTag.attrib:
                if float(backgroundTag.get('hue')) != 0:
                    logging.warning(f"value of background attribute not supported: hue =  {backgroundTag.get('hue')}")
            backgroundRotation = 0 # backgroundRotation not used yet pylint: disable=unused-variable # noqa: F841
            if "rotation" in backgroundTag.attrib:
                if float(backgroundTag.get('rotation')) != 0:
                    logging.warning(f"value of background attribute not supported: rotation =  {backgroundTag.get('rotation')}")
            backgroundType = 1 # backgroundType not used yet pylint: disable=unused-variable # noqa: F841
            if "type" in backgroundTag.attrib:
                if int(backgroundTag.get('type')) != 1:
                    logging.warning(
                        f"value of background attribute not supported: type =  {backgroundTag.get('type')}")
            try:
                bgPath = ""
                bgPath = findFileInDirs([bg + '.bmp', bg + '.webp', bg + '.jpg'], backgroundLocations)
                logging.debug(f"Reading background file: {bgPath}")

                # webp doesn't work with PIL.Image.open in Anaconda 5.3.0 on Win10
                imObj = PIL.Image.open(bgPath)
                # create a in-memory byte array of the image file
                im = bytes()
                memFileHandle = BytesIO(im)
                imObj = imObj.convert("RGB")
                imObj.save(memFileHandle, 'jpeg')
                memFileHandle.seek(0)

                # pdf.drawImage(ImageReader(bgpath), f * ax, 0, width=f * aw, height=f * ah)
                #   but im = ImageReader(bgpath) does not work with 1-bit images,so ...
                pdf.drawImage(ImageReader(memFileHandle), f * areaXOffset, 0, width=f * areaWidth, height=f * areaHeight)

            except Exception:
                if bgPath not in bg_notFoundDirList:
                    logging.error("Could not find background or error when adding to pdf")
                    logging.exception('Exception')
                bg_notFoundDirList.add(bgPath)
    return


def processAreaImageTag(imageTag, area, areaHeight, areaRot, areaWidth, imagedir,
                        productstyle, mcfBaseFolder, pagetype, pdf, pw, transx, transy):
    # open raw image file
    if imageTag.get('filename') is None:
        return
    imagePath = os.path.join(
        mcfBaseFolder, imagedir, imageTag.get('filename'))
    # the layout software copies the images to another collection folder
    imagePath = imagePath.replace('safecontainer:/', '')
    im = PIL.Image.open(imagePath)

    if imageTag.get('backgroundPosition') == 'RIGHT_OR_BOTTOM':
        # display on the right page
        if AlbumInfo.isAlbumDoubleSide(productstyle):
            img_transx = transx + f * pw/2
        else:
            img_transx = transx + f * pw
    else:
        img_transx = transx

    # correct for exif rotation
    im = autorot(im)
    # get the cutout position and scale
    imleft = float(imageTag.find('cutout').get('left').replace(',', '.'))
    imtop = float(imageTag.find('cutout').get('top').replace(',', '.'))
    # imageWidth_px, imageHeight_px = im.size
    imScale = float(imageTag.find('cutout').get('scale'))

    # we need to take care of changes introduced by passepartout elements, before further image processing
    passepartoutid = imageTag.get('passepartoutDesignElementId')
    frameClipartFileName = None
    maskClipartFileName = None
    frameDeltaX_mcfunit = 0
    frameDeltaY_mcfunit = 0
    frameAlpha = 255
    imgCropWidth_mcfunit = areaWidth
    imgCropHeight_mcfunit = areaHeight
    if passepartoutid is not None:
        # re-generate the index of designElementId to .xml files, if it does not exist
        passepartoutid = int(passepartoutid)    # we need to work with a number below
        global passepartoutDict # pylint: disable=global-statement
        if passepartoutDict is None:
            configlogger.info("Regenerating passepartout index from .XML files.")
            # the folder list may in fact be modified by buildElementIdIndex so disable pylint complaints
            passepartoutDict = Passepartout.buildElementIdIndex(passepartoutFolders)
        # read information from .xml file
        try:
            pptXmlFileName = passepartoutDict[passepartoutid]
        except: # noqa: E722
            pptXmlFileName = None
        if pptXmlFileName is None:
            logging.error(f"Can't find passepartout for {passepartoutid}")
        else:
            pptXmlFileName = passepartoutDict[passepartoutid]
            pptXmlInfo = Passepartout.extractInfoFromXml(pptXmlFileName, passepartoutid)
            frameClipartFileName = Passepartout.getClipartFullName(pptXmlInfo)
            maskClipartFileName = Passepartout.getMaskFullName(pptXmlInfo)
            logging.debug(f"Using mask file: {maskClipartFileName}")
            # draw the passepartout clipart file.
            # Adjust the position of the real image depending on the frame
            if pptXmlInfo.fotoarea_x is not None:
                frameDeltaX_mcfunit = pptXmlInfo.fotoarea_x * areaWidth
                frameDeltaY_mcfunit = pptXmlInfo.fotoarea_y * areaHeight
                imgCropWidth_mcfunit = pptXmlInfo.fotoarea_width * areaWidth
                imgCropHeight_mcfunit = pptXmlInfo.fotoarea_height * areaHeight

    # without cropping: to get from a image pixel width to the areaWidth in .mcf-units, the image pixel width is multiplied by the scale factor.
    # to get from .mcf units are divided by the scale factor to get to image pixel units.

    # crop image
    # currently the values can result in pixel coordinates outside the original image size
    # Pillow will fill these areas with black pixels. That's ok, but not documented anywhere.
    # For normal image display without passepartout there should be no black pixels visible,
    # because the CEWE software doesn't allow the creation of such parameters that would result in them.
    # For frames, the situation might arrise, but then the mask is applied.

    # first calcualte cropping coordinate for normal case
    cropLeft = int(0.5 - imleft/imScale + 0*frameDeltaX_mcfunit/imScale)
    cropUpper = int(0.5 - imtop/imScale + 0*frameDeltaY_mcfunit/imScale)
    cropRight = int(0.5 - imleft/imScale + 0*frameDeltaX_mcfunit/imScale + imgCropWidth_mcfunit / imScale)
    cropLower = int(0.5 - imtop/imScale + 0*frameDeltaY_mcfunit/imScale + imgCropHeight_mcfunit / imScale)

    im = im.crop((cropLeft, cropUpper, cropRight, cropLower))

    # scale image
    # re-scale the image if it is much bigger than final resolution in PDF
    # set desired DPI based on where the image is used. The background gets a lower DPI.
    if imageTag.tag == 'imagebackground' and pagetype != 'cover':
        res = bg_res
    else:
        res = image_res
    # 254 -> convert from mcf unit (0.1mm) to inch (1 inch = 25.4 mm)
    new_w = int(0.5 + imgCropWidth_mcfunit * res / 254.)
    new_h = int(0.5 + imgCropHeight_mcfunit * res / 254.)
    factor = sqrt(new_w * new_h / float(im.size[0] * im.size[1]))
    if factor <= 0.8:
        im = im.resize(
            (new_w, new_h), pil_antialias)
    im.load()

    # apply the frame mask from the passepartout to the image
    if maskClipartFileName is not None:
        maskClp = loadClipart(maskClipartFileName, clipartPathList)
        im = maskClp.applyAsAlphaMaskToFoto(im)

    # re-compress image
    jpeg = tempfile.NamedTemporaryFile() # pylint:disable=consider-using-with
    # we need to close the temporary file, because otherwise the call to im.save will fail on Windows.
    jpeg.close()
    if im.mode in ('RGBA', 'P'):
        im.save(jpeg.name, "PNG")
    else:
        im.save(jpeg.name, "JPEG",
                quality=image_quality)

    # place image
    logging.debug(f"image: {imageTag.get('filename')}")
    pdf.translate(img_transx, transy)   # we need to go to the center for correct rotation
    pdf.rotate(-areaRot)   # rotation around center of area

    # calculate the non-symmetric shift of the center, given the left pos and the width.
    frameShiftX_mcf = -(frameDeltaX_mcfunit-((areaWidth - imgCropWidth_mcfunit) - frameDeltaX_mcfunit))/2
    frameShiftY_mcf = (frameDeltaY_mcfunit-((areaHeight - imgCropHeight_mcfunit) - frameDeltaY_mcfunit))/2
    pdf.translate(-frameShiftX_mcf * f, -frameShiftY_mcf * f) # for adjustments from passepartout
    pdf.drawImage(ImageReader(jpeg.name),
        f * -0.5 * imgCropWidth_mcfunit,
        f * -0.5 * imgCropHeight_mcfunit,
        width=f * imgCropWidth_mcfunit,
        height=f * imgCropHeight_mcfunit,
        mask='auto')
    pdf.translate(frameShiftX_mcf * f, frameShiftY_mcf * f) # for adjustments from passepartout

    # we need to draw our passepartout after the real image, so it overlays it.
    if frameClipartFileName is not None:
        # we set the transx, transy, and areaRot for the clipart to zero, because our current pdf object
        # already has these transformations applied. So don't do it twice.
        # flipX and flipY are also set to false because it cause an exception in PIL
        # therefore, even if the CEWE software offers the possibility to flip the clipart frame, cewe2pdf
        # remains unable to render it
        colorreplacements, flipX, flipY = getClipConfig(imageTag) # pylint: disable=unused-variable
        insertClipartFile(frameClipartFileName, colorreplacements, 0, areaWidth, areaHeight, frameAlpha, pdf, 0, 0, False, False, None)

    for decorationTag in area.findall('decoration'):
        processAreaDecorationTag(decorationTag, areaHeight, areaWidth, pdf)

    pdf.rotate(areaRot)
    pdf.translate(-img_transx, -transy)

    # we now have temporary file, that we need to delete after pdf creation
    tempFileList.append(jpeg.name)


def processAreaDecorationTag(decoration, areaHeight, areaWidth, pdf):
    # Draw a single cell table to represent border decoration (a box around the object)
    # We assume that this is called from inside the rotation and translation operation

    for border in decoration.findall('border'):
        if "enabled" in border.attrib:
            enabledAttrib = border.get('enabled')
            if enabledAttrib != '1':
                return

        bwidth = 1
        if "width" in border.attrib:
            widthAttrib = border.get('width')
            if widthAttrib is not None:
                bwidth = f * floor(float(widthAttrib)) # units are 1/10 mm

        bcolor = reportlab.lib.colors.blue
        if "color" in border.attrib:
            colorAttrib = border.get('color')
            bcolor = reportlab.lib.colors.HexColor(colorAttrib)

        adjustment = 0
        if "position" in border.attrib:
            positionAttrib = border.get('position')
            if positionAttrib == "inside":
                adjustment = -bwidth * 0.5
            if positionAttrib == "centered":
                adjustment = 0
            if positionAttrib == "outside":
                adjustment = bwidth * 0.5

        frameBottomLeft_x = -0.5 * (f * areaWidth) - adjustment
        frameBottomLeft_y = -0.5 * (f * areaHeight) - adjustment
        frameWidth = f * areaWidth + 2 * adjustment
        frameHeight = f * areaHeight + 2 * adjustment
        frm_table = Table(
            data=[[None]],
            colWidths=frameWidth,
            rowHeights=frameHeight,
            style=[
                # The two (0, 0) in each attribute represent the range of table cells that the style applies to.
                # Since there's only one cell at (0, 0), it's used for both start and end of the range
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('BOX', (0, 0), (0, 0), bwidth, bcolor), # The fourth argument to this style attribute is the border width
                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
            ]
        )
        frm_table.wrapOn(pdf, frameWidth, frameHeight)
        frm_table.drawOn(pdf, frameBottomLeft_x, frameBottomLeft_y)


def processAreaTextTag(textTag, additional_fonts, area, areaHeight, areaRot, areaWidth, pdf, transx, transy): # noqa: C901 (too complex)
    # note: it would be better to use proper html processing here
    htmlxml = etree.XML(textTag.text)
    body = htmlxml.find('.//body')
    bstyle = dict([kv.split(':') for kv in body.get('style').lstrip(' ').rstrip(';').split('; ')])
    try:
        bodyfs = floor(float(bstyle['font-size'].strip("pt")))
    except: # noqa: E722
        bodyfs = 12
    family = bstyle['font-family'].strip("'")
    reportlabFonts = pdf.getAvailableFonts()
    if family in reportlabFonts:
        bodyfont = family
    elif family in additional_fonts:
        bodyfont = family
    else:
        bodyfont = getMissingFontSubstitute(family)
        noteFontSubstitution(family, bodyfont)

    try:
        bweight = int(Dequote(bstyle['font-weight']))
    except: # noqa: E722
        bweight = 400

    # issue https://github.com/bash0/cewe2pdf/issues/58 - margins are not being used
    # assume (based on empirical evidence!) that there is just one table, and collect
    # the margin values.
    tabletmarg = tablebmarg = tablelmarg = tablermarg = 0
    table = htmlxml.find('.//body/table')
    if table is not None:
        tableStyleAttrib = table.get('style')
        if tableStyleAttrib is not None:
            tablestyle = dict([kv.split(':') for kv in
                table.get('style').lstrip(' ').rstrip(';').split('; ')])
            try:
                tabletmarg = floor(float(tablestyle['margin-top'].strip("px")))
                tablebmarg = floor(float(tablestyle['margin-bottom'].strip("px")))
                tablelmarg = floor(float(tablestyle['margin-left'].strip("px")))
                tablermarg = floor(float(tablestyle['margin-right'].strip("px")))
            except: # noqa: E722
                logging.warning(f"Ignoring invalid table margin settings {tableStyleAttrib}")

    pdf.translate(transx, transy)
    pdf.rotate(-areaRot)

    # Get the background color. It is stored in an extra element.
    backgroundColor = None
    backgroundColorAttrib = area.get('backgroundcolor')
    if backgroundColorAttrib is not None:
        # Reorder for alpha value - CEWE uses #AARRGGBB, expected #RRGGBBAA
        backgroundColorInt = int(backgroundColorAttrib)
        backgroundColorRGB = backgroundColorInt & 0x00FFFFFF
        backgroundColorA = (backgroundColorInt & 0xFF000000) >> 24
        backgroundColorRGBA = (backgroundColorRGB << 8) + backgroundColorA
        backgroundColor = reportlab.lib.colors.HexColor(backgroundColorRGBA, False, True)

    # set default para style in case there are no spans to set it.
    pdf_styleN = CreateParagraphStyle(reportlab.lib.colors.black, bodyfont, bodyfs)

    # for debugging the background colour may be useful, but it is not used in production
    # since we started to use ColorFrame to colour the background, and it is thus left
    # unset by CreateParagraphStyle
    # pdf_styleN.backColor = reportlab.lib.colors.HexColor("0xFFFF00")

    htmlparas = body.findall(".//p")
    for p in htmlparas:
        maxfs = 0  # cannot use the bodyfs as a default, there may not actually be any text at body size
        if p.get('align') == 'center':
            pdf_styleN.alignment = reportlab.lib.enums.TA_CENTER
        elif p.get('align') == 'right':
            pdf_styleN.alignment = reportlab.lib.enums.TA_RIGHT
        elif p.get('align') == 'justify':
            pdf_styleN.alignment = reportlab.lib.enums.TA_JUSTIFY
        else:
            pdf_styleN.alignment = reportlab.lib.enums.TA_LEFT

        # there will be a paragraph style with various attributes, most of which we do not handle.
        # But this is where the line spacing is defined, with the line-height attribute
        pLineHeight = 1.0 # normal line spacing by default
        pStyleAttribute = p.get('style')
        if pStyleAttribute is not None:
            pStyle = dict([kv.split(':') for kv in
                p.get('style').lstrip(' ').rstrip(';').split('; ')])
            if 'line-height' in pStyle.keys():
                try:
                    pLineHeight = floor(float(pStyle['line-height'].strip("%")))/100.0
                except: # noqa: E722
                    logging.warning(f"Ignoring invalid paragraph line-height setting {pStyleAttribute}")
        finalLeadingFactor = LineScales.lineScaleForFont(bodyfont) * pLineHeight

        htmlspans = p.findall(".*")
        if len(htmlspans) < 1: # i.e. there are no spans, just a paragraph
            paragraphText = '<para autoLeading="max">'
            paragraphText, maxfs = AppendItemTextInStyle(paragraphText, p.text, p, pdf,
                additional_fonts, bodyfont, bodyfs, bweight, bstyle)
            paragraphText += '</para>'
            usefs = maxfs if maxfs > 0 else bodyfs
            pdf_styleN.leading = usefs * finalLeadingFactor # line spacing (text + leading)
            pdf_flowableList.append(Paragraph(paragraphText, pdf_styleN))

        else:
            paragraphText = '<para autoLeading="max">'

            # there might be untagged text preceding a span. We have to add that to paragraphText
            # first - but we must not terminate the paragraph and add it to the flowable because
            # the first span just continues that leading text
            if p.text is not None:
                paragraphText, maxfs = AppendItemTextInStyle(paragraphText, p.text, p, pdf,
                    additional_fonts, bodyfont, bodyfs, bweight, bstyle)
                usefs = maxfs if maxfs > 0 else bodyfs
                pdf_styleN.leading = usefs * finalLeadingFactor  # line spacing (text + leading)

            # now run round the htmlspans
            for item in htmlspans:
                if item.tag == 'br':
                    br = item
                    # terminate the current pdf para and add it to the flow. The nbsp seems unnecessary
                    # but if it is not there then an empty paragraph goes missing :-(
                    paragraphText += '&nbsp;</para>'
                    usefs = maxfs if maxfs > 0 else bodyfs
                    pdf_styleN.leading = usefs * finalLeadingFactor  # line spacing (text + leading)
                    pdf_flowableList.append(Paragraph(paragraphText, pdf_styleN))
                    # start a new pdf para in the style of the para and add the tail text of this br item
                    paragraphText = '<para autoLeading="max">'
                    paragraphText, maxfs = AppendItemTextInStyle(paragraphText, br.tail, p, pdf,
                        additional_fonts, bodyfont, bodyfs, bweight, bstyle)

                elif item.tag == 'span':
                    span = item
                    spanfont, spanfs, spanweight, spanstyle = CollectFontInfo(span, pdf, additional_fonts, bodyfont, bodyfs, bweight)

                    maxfs = max(maxfs, spanfs)

                    paragraphText = AppendSpanStart(paragraphText, spanfont, spanfs, spanweight, spanstyle, bstyle)

                    if span.text is not None:
                        paragraphText = AppendText(paragraphText, html.escape(span.text))

                    # there might be (one or more, or only one?) line break within the span.
                    brs = span.findall(".//br")
                    if len(brs) > 0:
                        # terminate the "real" span that we started above
                        paragraphText = AppendSpanEnd(paragraphText, spanweight, spanstyle, bstyle)
                        for br in brs:
                            # terminate the current pdf para and add it to the flow
                            paragraphText += '</para>'
                            usefs = maxfs if maxfs > 0 else bodyfs
                            pdf_styleN.leading = usefs * finalLeadingFactor  # line spacing (text + leading)
                            pdf_flowableList.append(Paragraph(paragraphText, pdf_styleN))
                            # start a new pdf para in the style of the current span
                            paragraphText = '<para autoLeading="max">'
                            # now add the tail text of each br in the span style
                            paragraphText, maxfs = AppendItemTextInStyle(paragraphText, br.tail, span, pdf,
                                additional_fonts, bodyfont, bodyfs, bweight, bstyle)
                    else:
                        paragraphText = AppendSpanEnd(paragraphText, spanweight, spanstyle, bstyle)

                    if span.tail is not None:
                        paragraphText = AppendText(paragraphText, html.escape(span.tail))

                else:
                    logging.warning(f"Ignoring unhandled tag {item.tag}")

            # try to create a paragraph with the current text and style. Catch errors.
            try:
                paragraphText += '</para>'
                usefs = maxfs if maxfs > 0 else bodyfs
                pdf_styleN.leading = usefs * finalLeadingFactor  # line spacing (text + leading)
                pdf_flowableList.append(Paragraph(paragraphText, pdf_styleN))
            except Exception:
                logging.exception('Exception')

    # Add a frame object that can contain multiple paragraphs
    leftPad = f * tablelmarg
    rightPad = f * tablermarg
    bottomPad = f * tablebmarg
    topPad = f * tabletmarg
    frameWidth = f * areaWidth
    frameHeight = f * areaHeight
    frameBottomLeft_x = -0.5 * frameWidth
    frameBottomLeft_y = -0.5 * frameHeight

    finalTotalHeight = topPad + bottomPad # built up in the text height check loop
    finalTotalWidth = frameWidth # should never be exceeded in the text height check loop
    availableTextHeight = frameHeight - topPad - bottomPad
    availableTextWidth = frameWidth - leftPad - rightPad

    # Go through all flowables and test if the fit in the frame. If not increase the frame height.
    # To solve the problem, that if each paragraph will fit indivdually, and also all together,
    # we need to keep track of the total summed height+
    for flowableListItem in pdf_flowableList:
        neededTextWidth, neededTextHeight = flowableListItem.wrap(availableTextWidth, availableTextHeight)
        finalTotalHeight += neededTextHeight
        availableTextHeight -= neededTextHeight
        if neededTextWidth > availableTextWidth:
            # I have never seen this happen, but check anyway
            logging.error('A set of paragraphs too wide for its frame. INTERNAL ERROR!')
            finalTotalWidth = neededTextWidth + leftPad + rightPad

    if finalTotalHeight > frameHeight:
        # One of the possible causes here is that wrap function has used an extra line (because
        #  of some slight mismatch in character widths and a frame that matches too precisely?)
        #  so that a word wraps over when it shouldn't. I don't know how to fix that sensibly.
        #  Increasing the height is NOT a good visual solution, because the line wrap is still
        #  not where the user expects it - increasing the width would almost be more sensible!
        # Another suspected cause is in the use of multiple font sizes in one text. Perhaps the
        #  line scale (interline space) gets confused by this?
        logging.warning('A set of paragraphs would not fit inside its frame. Frame height is increased to prevent loss of text.')
        logging.warning(' Try widening the text box just slightly to avoid an unexpected word wrap, or increasing the height yourself')
        logging.warning(f' Most recent paragraph text: {paragraphText}')
        frameHeight = finalTotalHeight
    else:
        frameHeight = max(frameHeight, finalTotalHeight)

    frameWidth = max(frameWidth, finalTotalWidth)

    newFrame = ColorFrame(frameBottomLeft_x, frameBottomLeft_y,
        frameWidth, frameHeight,
        leftPadding=leftPad, bottomPadding=bottomPad,
        rightPadding=rightPad, topPadding=topPad,
        showBoundary=0,  # for debugging useful to set 1
        background=backgroundColor
        )

    # This call should produce an exception, if any of the flowables do not fit inside the frame.
    # But there seems to be a bug, and no exception is triggered.
    # We took care of this by making the frame so large, that it always can fit the flowables.
    # maybe should switch to res=newFrame.split(flowable, pdf) and check the result manually.
    newFrame.addFromList(pdf_flowableList, pdf)

    for decorationTag in area.findall('decoration'):
        processAreaDecorationTag(decorationTag, areaHeight, areaWidth, pdf)

    pdf.rotate(areaRot)
    pdf.translate(-transx, -transy)


def processAreaClipartTag(clipartElement, areaHeight, areaRot, areaWidth, pdf, transx, transy, clipArtDecoration):
    clipartID = int(clipartElement.get('designElementId'))

    # designElementId 0 seems to be a special empty placeholder
    if clipartID == 0:
        return

    # Load the clipart
    fileName = None
    if clipartID in clipartDict:
        fileName = clipartDict[clipartID]
    # verify preconditions to avoid exception loading the clip art file, which would break the page count
    if not fileName:
        logging.error(f"Problem getting file name for clipart ID: {clipartID}")
        return

    alpha = 255
    if clipArtDecoration is not None:
        alphatext = clipArtDecoration.get('alpha') # alpha attribute
        if alphatext is not None:
            alpha = int((float(alphatext)) * 255)

    colorreplacements, flipX, flipY = getClipConfig(clipartElement)
    insertClipartFile(fileName, colorreplacements, transx, areaWidth, areaHeight, alpha, pdf, transy, areaRot, flipX, flipY, clipArtDecoration)


def insertClipartFile(fileName:str, colorreplacements, transx, areaWidth, areaHeight, alpha, pdf, transy, areaRot, flipX, flipY, decoration):
    img_transx = transx

    res = image_res # use the foreground resolution setting for clipart

    # 254 -> convert from mcf unit (0.1mm) to inch (1 inch = 25.4 mm)
    new_w = int(0.5 + areaWidth * res / 254.)
    new_h = int(0.5 + areaHeight * res / 254.)

    clipart = loadClipart(fileName, clipartPathList)
    if len(clipart.svgData) <= 0:
        logging.error(f"Clipart file could not be loaded: {fileName}")
        # avoiding exception in the processing below here
        return

    if len(colorreplacements) > 0:
        clipart.replaceColors(colorreplacements)

    clipart.convertToPngInBuffer(new_w, new_h, alpha, flipX, flipY)  # so we can access the pngMemFile later

    # place image
    logging.debug(f"Clipart file: {fileName}")
    pdf.translate(img_transx, transy)
    pdf.rotate(-areaRot)
    pdf.drawImage(ImageReader(clipart.pngMemFile),
        f * -0.5 * areaWidth, f * -0.5 * areaHeight,
        width=f * areaWidth, height=f * areaHeight, mask='auto')
    if decoration is not None:
        processAreaDecorationTag(decoration, areaHeight, areaWidth, pdf)
    pdf.rotate(areaRot)
    pdf.translate(-img_transx, -transy)


def processElements(additional_fonts, fotobook, imagedir,
                    productstyle, mcfBaseFolder, oddpage, page, pageNumber, pagetype, pdf, ph, pw, lastpage):
    if AlbumInfo.isAlbumDoubleSide(productstyle) and pagetype == PageType.Normal and not oddpage and not lastpage:
        # if we are in double-page mode, all the images are drawn by the odd pages.
        return

    # the mcf file really comes in "bundles" of two pages, so for odd pages we switch back to
    # the page element for the preceding even page to get the elements
    if AlbumInfo.isAlbumProduct(productstyle) and pagetype == PageType.Normal and oddpage:
        page = getPageElementForPageNumber(fotobook, 2*floor(pageNumber/2))

    for area in page.findall('area'):
        areaPos = area.find('position')
        areaLeft = float(areaPos.get('left').replace(',', '.'))
        if pagetype != PageType.SingleSide or len(area.findall('imagebackground')) == 0:
            if oddpage and AlbumInfo.isAlbumSingleSide(productstyle):
                # shift double-page content from other page
                areaLeft -= pw
        areaTop = float(areaPos.get('top').replace(',', '.'))
        areaWidth = float(areaPos.get('width').replace(',', '.'))
        areaHeight = float(areaPos.get('height').replace(',', '.'))
        areaRot = float(areaPos.get('rotation'))

        # check if the image is on current page at all, and if not then skip processing it
        if AlbumInfo.isAlbumSingleSide(productstyle) and pagetype in [PageType.Normal, PageType.Cover]:
            if oddpage:
                # the right edge of image is beyond the left page border
                if (areaLeft+areaWidth) < 0:
                    continue
            else:
                if areaLeft > pw:  # the left image edge is beyond the right page border.
                    continue

        # center positions
        cx = areaLeft + 0.5 * areaWidth
        cy = ph - (areaTop + 0.5 * areaHeight)

        transx = f * cx
        transy = f * cy

        # process images
        for imageTag in area.findall('imagebackground') + area.findall('image'):
            processAreaImageTag(imageTag, area, areaHeight, areaRot, areaWidth, imagedir, productstyle, mcfBaseFolder, pagetype, pdf, pw, transx, transy)

        # process text
        for textTag in area.findall('text'):
            processAreaTextTag(textTag, additional_fonts, area, areaHeight, areaRot, areaWidth, pdf, transx, transy)

        # Clip-Art
        # In the clipartarea there are two similar elements, the <designElementIDs> and the <clipart>.
        # We are using the <clipart> element here
        if area.get('areatype') == 'clipartarea':
            # within clipartarea tags we need the decoration for alpha and border information
            decoration = area.find('decoration')
            for clipartElement in area.findall('clipart'):
                processAreaClipartTag(clipartElement, areaHeight, areaRot, areaWidth, pdf, transx, transy, decoration)
    return


def parseInputPage(fotobook, cewe_folder, mcfBaseFolder, backgroundLocations, imagedir, pdf,
        page, pageNumber, pageCount, pagetype, productstyle, oddpage,
        bg_notFoundDirList, additional_fonts, lastpage):
    logging.info(f"Side {pageNumber} ({pagetype}): parsing pagenr {page.get('pagenr')} of {pageCount}")

    bundlesize = page.find("./bundlesize")
    if bundlesize is not None:
        pw = float(bundlesize.get('width'))
        ph = float(bundlesize.get('height'))
        if AlbumInfo.isAlbumSingleSide(productstyle):
            pw = pw / 2 # reduce the page width to a single page width for single sided
    else:
        # Assume A4 page size
        pw = 2100
        ph = 2970
    pdf.setPageSize((f * pw, f * ph))

    # process background
    # look for all "<background...> tags.
    # the preceding designElementIDs tag only match the same
    #  number for the background attribute if it is a original
    #  stock image, without filters.
    backgroundTags = page.findall('background')
    processBackground(backgroundTags, bg_notFoundDirList, cewe_folder, backgroundLocations, productstyle, pagetype, pdf, ph, pw)

    if AlbumInfo.isAlbumSingleSide(productstyle) and pagetype == PageType.SingleSide:
        # This must be page 1, the inside front cover, so we only do the background. Page 1
        # is processed again with PageType.EmptyPage, and the elements will be done then
        return

    # all elements (images, text,..) for even and odd pages are defined on the even page element!
    processElements(additional_fonts, fotobook, imagedir, productstyle, mcfBaseFolder, oddpage, page, pageNumber, pagetype, pdf, ph, pw, lastpage)


def convertMcf(albumname, keepDoublePages: bool, pageNumbers=None, mcfxTmpDir=None, appDataDir=None, outputFileName=None): # noqa: C901 (too complex)
    global clipartDict  # pylint: disable=global-statement
    global clipartPathList  # pylint: disable=global-statement
    global passepartoutDict  # pylint: disable=global-statement
    global passepartoutFolders  # pylint: disable=global-statement
    global image_res  # pylint: disable=global-statement
    global bg_res  # pylint: disable=global-statement
    global defaultConfigSection  # pylint: disable=global-statement

    clipartDict = {}    # a dictionary for clipart element IDs to file name
    clipartPathList = tuple()
    passepartoutDict = None    # a dictionary for passepartout  desginElementIDs to file name
    passepartoutFolders = tuple[str]() # global variable with the folders for passepartout frames

    albumTitle, dummy = os.path.splitext(os.path.basename(albumname))

    # check for new format (version 7.3.?, ca 2023, issue https://github.com/bash0/cewe2pdf/issues/119)
    mcfxFormat = albumname.endswith(".mcfx")
    if mcfxFormat:
        albumPathObj = Path(albumname).resolve()
        unpackedFolder, mcfxmlname = unpackMcfx(albumPathObj, mcfxTmpDir)
    else:
        unpackedFolder = None
        mcfxmlname = albumname

    # we'll need the album folder to find config files
    albumBaseFolder = str(Path(albumname).resolve().parent)

    # we'll need the mcf folder to find mcf relative image file names
    mcfPathObj = Path(mcfxmlname).resolve()
    mcfBaseFolder = str(mcfPathObj.parent)

    # parse the input mcf xml file
    # read file as binary, so UTF-8 encoding is preserved for xml-parser
    try:
        with open(mcfxmlname, 'rb') as mcffile:
            mcf = etree.parse(mcffile)
    except Exception as e:
        invalidmsg = f"Cannot open mcf file {mcfxmlname}"
        if mcfxFormat:
            invalidmsg = invalidmsg + f" (unpacked from {albumname})"
        invalidmsg = invalidmsg + f": {repr(e)}"
        logging.error(invalidmsg)
        sys.exit(1)

    fotobook = mcf.getroot()
    CeweInfo.ensureAcceptableAlbumMcf(fotobook, albumname, mcfxmlname, mcfxFormat)

    # check output file is acceptable before we do any processing, which is
    # preferable to processing for a long time and *then* discovering that
    # the file is not writable
    if outputFileName is None:
        outputFileName = CeweInfo.getOutputFileName(albumname)
    CeweInfo.ensureAcceptableOutputFile(outputFileName)

    # a null default configuration section means that some capabilities will be missing!
    defaultConfigSection = None
    # find cewe folder using the original cewe_folder.txt file
    try:
        configFolderFileName = findFileInDirs('cewe_folder.txt', (albumBaseFolder, os.path.curdir, os.path.dirname(os.path.realpath(__file__))))
        with open(configFolderFileName, 'r') as cewe_file:  # this works on all relevant platforms so pylint: disable=unspecified-encoding
            cewe_folder = cewe_file.read().strip()
            CeweInfo.checkCeweFolder(cewe_folder)
            keyAccountNumber = CeweInfo.getKeyAccountNumber(cewe_folder)
            keyAccountFolder = CeweInfo.getKeyAccountDataFolder(keyAccountNumber)
            backgroundLocations = CeweInfo.getBaseBackgroundLocations(cewe_folder, keyAccountFolder)

    except: # noqa: E722
        # arrives here if the original cewe_folder.txt file is missing, which we really expect it to be these days.
        logging.info('Trying cewe2pdf.ini from current directory and from the album directory.')
        configuration = configparser.ConfigParser()
        # Try to read the .ini first from the current directory, and second from the directory where the .mcf file is.
        # Order of the files is important, because config entires are
        #  overwritten when they appear in the later config files.
        # We want the config file in the .mcf directory to be the most important file.
        filesread = configuration.read(['cewe2pdf.ini', os.path.join(albumBaseFolder, 'cewe2pdf.ini')])
        if len(filesread) < 1:
            logging.error('You must create cewe_folder.txt or cewe2pdf.ini to specify the cewe_folder')
            sys.exit(1)
        else:
            # Give the user feedback which config-file is used, in case there is a problem.
            mustsee.info(f'Using configuration files, in order: {str(filesread)}')
            defaultConfigSection = configuration['DEFAULT']
            # find cewe folder from ini file
            if 'cewe_folder' not in defaultConfigSection:
                logging.error('You must create cewe_folder.txt or modify cewe2pdf.ini to define cewe_folder')
                sys.exit(1)

            cewe_folder = defaultConfigSection['cewe_folder'].strip()
            CeweInfo.checkCeweFolder(cewe_folder)

            keyAccountNumber = CeweInfo.getKeyAccountNumber(cewe_folder, defaultConfigSection)

            # set the cewe folder and key account number into the environment for later use in the config files
            CeweInfo.SetEnvironmentVariables(cewe_folder, keyAccountNumber)

            keyAccountFolder = CeweInfo.getKeyAccountDataFolder(keyAccountNumber, defaultConfigSection)

            baseBackgroundLocations = CeweInfo.getBaseBackgroundLocations(cewe_folder, keyAccountFolder)

            # add any extra background folders, substituting environment variables
            xbg = defaultConfigSection.get('extraBackgroundFolders', '').splitlines()  # newline separated list of folders
            fxbg = list(filter(lambda bg: (len(bg) != 0), xbg)) # filter out empty entries
            f2xbg = tuple(map(lambda bg: os.path.expandvars(bg), fxbg)) # expand environment vars pylint: disable=unnecessary-lambda
            backgroundLocations = baseBackgroundLocations + f2xbg

            # adds extra clipart ids, with absolute file references
            xca = defaultConfigSection.get('extraClipArts', '').splitlines()  # newline separated list of id, filename pairs
            fxca = list(filter(lambda ca: (len(ca) != 0), xca)) # filter out empty entries
            f2xca = tuple(map(lambda ca: os.path.expandvars(ca), fxca)) # expand environment vars pylint: disable=unnecessary-lambda
            for ca in f2xca:
                definition = ca.split(',')
                if len(definition) == 2:
                    clipartId = int(definition[0])
                    file = definition[1].strip()
                    clipartDict[clipartId] = file

            # read passepartout folders and substitute environment variables
            pptout_rawFolder = defaultConfigSection.get('passepartoutFolders', '').splitlines()  # newline separated list of folders
            pptout_rawFolder.append(cewe_folder)    # add the base folder
            pptout_filtered1 = list(filter(lambda bg: (len(bg) != 0), pptout_rawFolder)) # filter out empty entries
            pptout_filtered2 = tuple(map(lambda bg: os.path.expandvars(bg), pptout_filtered1)) # expand environment vars pylint: disable=unnecessary-lambda
            passepartoutFolders = pptout_filtered2

            # read resolution options
            image_res = getConfigurationInt(defaultConfigSection, 'pdfImageResolution', '150', 100)
            bg_res = getConfigurationInt(defaultConfigSection, 'pdfBackgroundResolution', '150', 100)

    mustsee.info(f'Using image resolution {image_res}, background resolution {bg_res}')

    # See if there is a configured default line scale overriding the coded default.
    # This global default line scale may be reconfigured per font, after font registration
    # is complete, into the fontLineScales mapping
    LineScales.setupDefaultLineScale(defaultConfigSection)

    if keyAccountFolder is not None:
        passepartoutFolders = passepartoutFolders + CeweInfo.getCewePassepartoutFolders(cewe_folder, keyAccountFolder)

    bg_notFoundDirList = set([]) # keep a list of background folders that are not found, to prevent multiple errors for the same cause.

    # Load fonts
    availableFonts = findAndRegisterFonts(defaultConfigSection, appDataDir, albumBaseFolder, cewe_folder)

    # Read any configured non-standard line scales for specified fonts, creating a map of font name to line scale
    LineScales.setupFontLineScales(defaultConfigSection)

    # extract basic album properties
    articleConfigElement = fotobook.find('articleConfig')
    if articleConfigElement is None:
        logging.error(f'{albumname} is an old version. Open it in the album editor and save before retrying the pdf conversion. Exiting.')
        sys.exit(1)

    pageNumberElement = fotobook.find('pagenumbering')
    if pageNumberElement is not None:
        pnpos = int(pageNumberElement.get('position'))
        if pnpos != 0:
            logging.warning(f'Page numbering is not yet implemented')

    pageCount = int(articleConfigElement.get('normalpages')) + 2
    # The normalpages attribute in the mcf is the number of "usable" inside pages, excluding the front and back covers and the blank inside
    #  cover pages. Add 2 so that pagecount represents the actual number of printed pdf pages we expect in the normal single sided
    #  pdf print (a basic album is 26 inside pages, plus front and back cover, i.e. 28). If we use keepDoublePages, then we'll
    #  actually be producing 2 more (the inside covers) but halving the number of final output pdf pages, making 15 double pages.
    # There is also a totalpages attribute in the mcf, but in my files it is 5 more than the normalpages value. Why not 4 more? I
    #  guess that may be because it is a count of the <page> elements and not actually related to the number of printed pages.
    imageFolder = fotobook.get('imagedir')

    # generate a list of available clip-arts
    clipartPathList = readClipArtConfigXML(cewe_folder, keyAccountFolder, clipartDict)

    # find the correct size for the album format (if we know!) and set the product style
    pagesize = reportlab.lib.pagesizes.A4
    productstyle = ProductStyle.AlbumSingleSide
    productname = fotobook.get('productname')
    if productname in AlbumInfo.formats: # IMO this is clearest so pylint: disable=consider-using-get
        pagesize = AlbumInfo.formats[productname]
    if productname in AlbumInfo.styles: # IMO this is clearest so pylint: disable=consider-using-get
        productstyle = AlbumInfo.styles[productname]
    if keepDoublePages:
        if productstyle == ProductStyle.AlbumSingleSide:
            productstyle = ProductStyle.AlbumDoubleSide
        elif productstyle == ProductStyle.MemoryCard:
            logging.warning('keepdoublepages option is irrelevant and ignored for a memory card product')

    # initialize a pdf canvas
    pdf = canvas.Canvas(outputFileName, pagesize=pagesize)
    pdf.setTitle(albumTitle)

    # generate all the requested pages
    processPages(fotobook, mcfBaseFolder, imageFolder, productstyle, pdf, pageCount, pageNumbers,
        cewe_folder, availableFonts, backgroundLocations, bg_notFoundDirList)

    # save final output pdf
    try:
        pdf.save()
    except Exception as ex:
        logging.error(f'Could not save the output file: {str(ex)}')

    pdf = []

    # force the release of objects which might be holding on to picture file references
    # so that they will not prevent the removal of the files as we clean up and exit
    objectscollected = gc.collect()
    logging.info(f'GC collected objects : {objectscollected}')

    printMessageCountSummaries()

    if productstyle == ProductStyle.MemoryCard:
        print()
        print("Use Adobe Acrobat to print the memory cards. Set custom pages per sheet, 4 wide x 6 down")
        print(" and print two copies!")

    VerifyMessageCounts(defaultConfigSection)

    cleanUpTempFiles(tempFileList, unpackedFolder)

    return True


def processPages(fotobook, mcfBaseFolder, imagedir, productstyle, pdf, pageCount, pageNumbers, # noqa: C901
        cewe_folder, availableFonts, backgroundLocations, bg_notFoundDirList):

    def IsBackCover(n):
        return n == (pageCount - 1)

    def IsLastPage(n):
        return n == (pageCount - 2)

    def IsOddPage(n):
        return (n % 2) == 1

    for n in range(pageCount): # starting at 0
        try:
            pagetype = PageType.Unknown
            lastpage = IsLastPage(n) # bool assign is clearer with parens so pylint: disable=superfluous-parens

            # The <page> sections all have a pagenr attribute. The normal pages run from pagenr 1 to pagenr 26 while there are
            # actually FIVE page elements with pagenr 0 in a default album file, 4 coming before pagenr 1 and 1 after pagenr 26
            if AlbumInfo.isAlbumProduct(productstyle) and ((n == 0) or IsBackCover(n)): # clearest like this so pylint: disable=consider-using-in
                fullcoverpages = [i for i in
                    fotobook.findall("./page[@pagenr='0'][@type='FULLCOVER']")
                    + fotobook.findall("./page[@pagenr='0'][@type='fullcover']")
                    if i.find("./area") is not None]
                if len(fullcoverpages) == 1:
                    # in a well-formed album there are two fullcover pages, but only one with an area, which we
                    # have just found. That fullcover "page 0" (bundle) contains all the stuff for the back cover
                    # on the left side, and the front cover on the right sight (and the spine, as it happens)
                    page = fullcoverpages[0]
                    oddpage = (n == 0) # bool assign is clearer with parens so pylint: disable=superfluous-parens
                    pagetype = PageType.Cover
                    pageNumber = n
                    # for double-page-layout: the last page is already the left side of the book cover. So skip rendering the last page
                    if (AlbumInfo.isAlbumDoubleSide(productstyle) and IsBackCover(pageNumber)):
                        page = None
                else:
                    logging.warning("Cannot locate a cover page, is this really an album?")
                    page = None

            elif AlbumInfo.isAlbumProduct(productstyle) and n == 1: # album page 1 is handled specially
                pageNumber = 1
                oddpage = True
                # Look for an empty page 0 that still contains an area element
                page = [i for i in
                        fotobook.findall("./page[@pagenr='0'][@type='EMPTY']")
                        + fotobook.findall("./page[@pagenr='0'][@type='emptypage']")
                        if i.find("./area") is not None or i.find("./background[@alignment='1']") is not None]
                if len(page) >= 1:
                    page = page[0]
                    # If there is on page 1 only text, the area-tag is still on page 0.
                    #  So this will either include the text (which is put in page 0),
                    #  or the packground which is put in page 1.
                else:
                    logging.error(f'Failed to locate initial emptypage when processing page {n}')
                    page = None

                # Look for the the first page and set it up for processing
                realFirstPageList = fotobook.findall("./page[@pagenr='1'][@type='normalpage']")
                if len(realFirstPageList) > 0 and (pageNumbers is None or 0 in pageNumbers):
                    # for this special page we need to do run parseInputPage twice for one output page in the PDF.
                    # The background needs to be drawn first, or it would obscure any other other elements.
                    pagetype = PageType.SingleSide
                    lastpage = False
                    parseInputPage(fotobook, cewe_folder, mcfBaseFolder, backgroundLocations, imagedir, pdf,
                        realFirstPageList[0], pageNumber, pageCount, pagetype, productstyle, oddpage,
                        bg_notFoundDirList, availableFonts, lastpage)
                pagetype = PageType.EmptyPage

            elif AlbumInfo.isAlbumProduct(productstyle) and lastpage: # album last page is special because of inside cover
                pageNumber = n
                if pageNumbers is None or pageNumber in pageNumbers:
                    # process the actual last page
                    oddpage = IsOddPage(pageNumber)
                    page = getPageElementForPageNumber(fotobook, n)
                    pagetype = PageType.Normal
                    parseInputPage(fotobook, cewe_folder, mcfBaseFolder, backgroundLocations, imagedir, pdf,
                        page, pageNumber, pageCount, PageType.Normal, productstyle, oddpage,
                        bg_notFoundDirList, availableFonts, lastpage)

                # Look for an empty page 0 that does NOT contain an area element. That will define
                # the background for the inside cover page to be placed on top of the right side of
                # the page we have just processed
                page = [i for i in
                        fotobook.findall("./page[@pagenr='0'][@type='EMPTY']")
                        + fotobook.findall("./page[@pagenr='0'][@type='emptypage']")
                        if i.find("./area") is None or i.find("./background[@alignment='3']") is not None]
                if len(page) >= 1:
                    # set up to process the special section for the inside cover
                    page = page[0]
                    pageNumber = n + 1
                    oddpage = IsOddPage(pageNumber)
                    pagetype = PageType.BackInsideCover
                else:
                    logging.error(f'Failed to locate final emptypage when processing last page {n}')
                    page = None # catastrophe

            else:
                pageNumber = n
                oddpage = IsOddPage(pageNumber)
                page = getPageElementForPageNumber(fotobook, n)
                pagetype = PageType.Normal

            if pageNumbers is not None and pageNumber not in pageNumbers:
                continue

            if page is not None:
                if pagetype == PageType.Unknown:
                    logging.error(f'Unable to deduce page type for page {pageNumber}')
                    continue
                parseInputPage(fotobook, cewe_folder, mcfBaseFolder, backgroundLocations, imagedir, pdf,
                    page, pageNumber, pageCount, pagetype, productstyle, oddpage,
                    bg_notFoundDirList, availableFonts, lastpage)

                # finish the pdf page and start a new one.
                if not AlbumInfo.isAlbumProduct(productstyle):
                    # it would be neat to duplicate the page for MemoryCard products but showPage
                    # empties the canvas so the user must just print the pdf file twice!
                    pdf.showPage()
                elif AlbumInfo.isAlbumSingleSide(productstyle):
                    pdf.showPage()
                elif oddpage or (pagetype == PageType.Cover and not IsBackCover(n)):
                    # We're creating a AlbumDoubleSide so we only output after the odd pages
                    pdf.showPage()

        except Exception as pageex:
            # if one page fails: continue with next one
            logging.exception("Exception")
            logging.error(f'error on page {n}: {pageex.args[0]}')


def collectArgsAndConvert():
    class CustomArgFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass

    epilogText = "Example:\n   python cewe2pdf.py"
    exampleFile = r"c:\path\to\my\files\my_nice_fotobook.mcf"
    parser = argparse.ArgumentParser(description='Convert a photo-book from .mcf/.mcfx file format to .pdf',
                                     epilog=f"{epilogText} {exampleFile}\n \n",
                                     formatter_class=CustomArgFormatter)
    parser.add_argument('--keepDoublePages', dest='keepDoublePages', action='store_const',
                        const=True, default=False,
                        help='Each page in the .pdf will be a double-sided page, instead of a normal single page.')
    parser.add_argument('--pages', dest='pages', action='store',
        default=None,
        help='Page numbers to render, e.g. 1,2,4-9 (default: None, which of course processes all the pages). '
            'These refer to the inside page numbers as you see them in the album editor - the first user editable inside page is number 1. '
            'If you want the front cover, then ask for page 0. Asking for the back cover explicitly will not work!')
    parser.add_argument('--tmp-dir', dest='mcfxTmp', action='store',
                        default=None,
                        help='Directory for .mcfx file extraction')
    parser.add_argument('--appdata-dir', dest='appData',
                        default=None,
                        help='Directory for persistent app data, eg ttf fonts converted from otf fonts')
    parser.add_argument('--outFile', dest='outFile',
                        default=None,
                        help="The name of the output file, rather than the default <inputFile>.pdf")
    parser.add_argument('inputFile', type=str, nargs='?',
                        help='Just one mcf(x) input file must be specified')

    args = parser.parse_args()

    if args.inputFile is None:
        # from July 2024 you must specify a file name. Check if there are any obvious candidates
        # which we could use in an example text
        fnames = [i for i in os.listdir(os.curdir) if os.path.isfile(i) and (i.endswith('.mcf') or i.endswith('.mcfx'))]
        if len(fnames) >= 1:
            # There is one or more mcf(x) file! Show him how to specify the first such file as an example.
            exampleFile = os.path.join(os.getcwd(), fnames[0])
            if ' ' in exampleFile:
                exampleFile = f'\"{exampleFile}\"'
            parser.epilog = f"{epilogText} {exampleFile}\n \n"
        parser.parse_args(['-h'])
        sys.exit(1)

    pages = None
    if args.pages is not None:
        pages = []
        for expr in args.pages.split(','):
            expr = expr.strip()
            if expr.isnumeric():
                pages.append(int(expr)) # simple number "23"
            elif expr.find('-') > -1:
                # page range: 23-42
                fromTo = expr.split('-', 2)
                if not fromTo[0].isnumeric() or not fromTo[1].isnumeric():
                    logging.error(f'Invalid page range: {expr}')
                    sys.exit(1)
                pageFrom = int(fromTo[0])
                pageTo = int(fromTo[1])
                if pageTo < pageFrom:
                    logging.error(f'Invalid page range: {expr}')
                    sys.exit(1)
                pages = pages + list(range(pageFrom, pageTo + 1))
            else:
                logging.error(f'Invalid page number: {expr}')
                sys.exit(1)

    mcfxTmp = None
    if args.mcfxTmp is not None:
        mcfxTmp = os.path.abspath(args.mcfxTmp)

    appData = None
    if args.appData is not None:
        appData = os.path.abspath(args.appData)

    outFile = None
    if args.outFile is not None:
        outFile = os.path.abspath(args.outFile)

    # convert the file
    return convertMcf(args.inputFile, args.keepDoublePages, pages, mcfxTmp, appData, outputFileName=outFile)


def cleanUpTempFiles(fileList, unpackedFolder):
    for tmpFileName in fileList:
        if os.path.exists(tmpFileName):
            os.remove(tmpFileName)
    if unpackedFolder is not None:
        unpackedFolder.cleanup()


if __name__ == '__main__':
    # only executed when this file is run directly.
    # we need trick to have both: default and fixed formats.
    resultFlag = collectArgsAndConvert()
