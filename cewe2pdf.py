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

import reportlab.lib.colors
import reportlab.lib.pagesizes
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table
from reportlab.lib.styles import ParagraphStyle
# from reportlab.lib.styles import getSampleStyleSheet

import numpy as np
import PIL

from packaging.version import parse as parse_version
from lxml import etree

from ceweInfo import CeweInfo, AlbumInfo, ProductStyle
from clipArt import getClipConfig, loadClipart, readClipArtConfigXML
from colorFrame import ColorFrame
from colorUtils import ReorderColorBytesMcf2Rl
from configUtils import getConfigurationBool, getConfigurationInt
from extraLoggers import mustsee, configlogger, VerifyMessageCounts, printMessageCountSummaries
from fontHandling import getAvailableFont, getMissingFontSubstitute, findAndRegisterFonts, noteFontSubstitution
from imageUtils import autorot
from lineScales import LineScales
from mcfx import unpackMcfx
from pageNumbering import getPageNumberXy, PageNumberingInfo, PageNumberPosition
from passepartout import Passepartout
from pathutils import findFileInDirs
from text import AppendItemTextInStyle, AppendSpanEnd, AppendSpanStart, AppendText
from text import CollectFontInfo, CollectItemFontFamily, CreateParagraphStyle, Dequote
from index import Index
from textart import handleTextArt


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

mcf2rl = reportlab.lib.pagesizes.mm/10 # == 72/254, converts from mcf (unit=0.1mm) to reportlab (unit=inch/72)

tempFileList = []  # we need to remove all the temporary files at the end

# reportlab defaults
# pdf_styles = getSampleStyleSheet()
# pdf_styleN = pdf_styles['Normal']
pdf_flowableList = []

albumIndex = None # set after we have got the configuration information
clipartDict = dict[int, str]()    # a dictionary for clipart element IDs to file name
clipartPathList = tuple[str]()
passepartoutDict = None    # will be dict[int, str] for passepartout designElementIDs to file name
passepartoutFolders = tuple[str]() # global variable with the folders for passepartout frames
defaultConfigSection = None
pageNumberingInfo = None # if the album requests page numbering then we keep the details here


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
                pdf.drawImage(ImageReader(memFileHandle), mcf2rl * areaXOffset, 0, width=mcf2rl * areaWidth, height=mcf2rl * areaHeight)

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
            img_transx = transx + mcf2rl * pw/2
        else:
            img_transx = transx + mcf2rl * pw
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

    for decorationTag in area.findall('decoration'):
        processDecorationShadow(decorationTag, areaHeight, areaWidth, pdf)

    # calculate the non-symmetric shift of the center, given the left pos and the width.
    frameShiftX_mcf = -(frameDeltaX_mcfunit-((areaWidth - imgCropWidth_mcfunit) - frameDeltaX_mcfunit))/2
    frameShiftY_mcf = (frameDeltaY_mcfunit-((areaHeight - imgCropHeight_mcfunit) - frameDeltaY_mcfunit))/2
    pdf.translate(-frameShiftX_mcf * mcf2rl, -frameShiftY_mcf * mcf2rl) # for adjustments from passepartout
    pdf.drawImage(ImageReader(jpeg.name),
        mcf2rl * -0.5 * imgCropWidth_mcfunit,
        mcf2rl * -0.5 * imgCropHeight_mcfunit,
        width=mcf2rl * imgCropWidth_mcfunit,
        height=mcf2rl * imgCropHeight_mcfunit,
        mask='auto')
    pdf.translate(frameShiftX_mcf * mcf2rl, frameShiftY_mcf * mcf2rl) # for adjustments from passepartout

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
        processDecorationBorders(decorationTag, areaHeight, areaWidth, pdf)

    pdf.rotate(areaRot)
    pdf.translate(-img_transx, -transy)

    # we now have temporary file, that we need to delete after pdf creation
    tempFileList.append(jpeg.name)


def processDecorationBorders(decoration, areaHeight, areaWidth, pdf):
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
                bwidth = mcf2rl * floor(float(widthAttrib)) # units are 1/10 mm

        bcolor = reportlab.lib.colors.blue
        if "color" in border.attrib:
            colorAttrib = border.get('color')
            bcolor = reportlab.lib.colors.HexColor(colorAttrib)

        adjustment = 0
        gap = 0
        if "gap" in border.attrib:
            gapAttrib = border.get('gap')
            gap = mcf2rl * floor(float(gapAttrib))
        # position possibilities are: outsideWithGap outside inside centered insideWithGap
        if "position" in border.attrib:
            positionAttrib = border.get('position')
            if positionAttrib == "insideWithGap":
                adjustment = -bwidth * 0.5 - gap
            if positionAttrib == "inside":
                adjustment = -bwidth * 0.5
            if positionAttrib == "centered":
                adjustment = 0
            if positionAttrib == "outside":
                adjustment = bwidth * 0.5
            if positionAttrib == "outsideWithGap":
                adjustment = bwidth * 0.5 + gap

        frameBottomLeft_x = -0.5 * (mcf2rl * areaWidth) - adjustment
        frameBottomLeft_y = -0.5 * (mcf2rl * areaHeight) - adjustment
        frameWidth = mcf2rl * areaWidth + 2 * adjustment
        frameHeight = mcf2rl * areaHeight + 2 * adjustment
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


def findShadowBottomLeft(frameBottomLeft, angle, distance, swidth):
    x, y = frameBottomLeft
    if distance < 0.001:
        # why on earth do I need this special case??
        return x - swidth / 2, y - swidth / 2
    # Compute shadow shift vector
    angle_rad = np.radians(angle - 90)
    shadow_dx = distance * np.cos(angle_rad)
    shadow_dy = -distance * np.sin(angle_rad)  # Flip the Y-axis direction
    # Return shadow rectangle bottom left coordinates
    return x + shadow_dx - swidth / 2, y + shadow_dy - swidth / 2

def intensityToGrey(value):
    colorComponentValue = 1 - (max(1, min(255, value)) / 255)
    return reportlab.lib.colors.Color(colorComponentValue, colorComponentValue, colorComponentValue)

def processDecorationShadow(decoration, areaHeight, areaWidth, pdf):
    if getConfigurationBool(defaultConfigSection, "noShadows", "False"):
        # shadows were implemented in May 2025. Prior to that, you could have specified
        # shadows on your photos for printing by CEWE but you would not have got them
        # in the pdf version. And this might be what you want, so there is an option
        # to stop shadow processing altogether
        return

    # We assume that this is called from inside the rotation and translation operation
    # Ref https://cs.phx.photoprintit.com/hps-hilfe-online/no_no_5026/7.4/faq-fotos.html#q010
    # can't find an english version.

    frameBottomLeft_x = -0.5 * (mcf2rl * areaWidth)
    frameBottomLeft_y = -0.5 * (mcf2rl * areaHeight)
    frameWidth = mcf2rl * areaWidth
    frameHeight = mcf2rl * areaHeight

    for shadow in decoration.findall('shadow'):
        if "shadowEnabled" in shadow.attrib:
            enabledAttrib = shadow.get('shadowEnabled')
            if enabledAttrib != '1':
                continue

        # shadow width simulates "distance away of the light source". If the width is zero,
        # then the light rays are parallel and the shadow is the same size as the object.
        # So the width value is really about how much bigger the shadow is than the object.
        swidth = 1
        if "shadowWidthInMM" in shadow.attrib:
            widthAttrib = shadow.get('shadowWidthInMM')
            if widthAttrib is not None:
                swidth = mcf2rl * floor(float(widthAttrib) * 10) # units are 1 mm not 0.1 mm!

        # sdistance effectively moves the light source to the side of the centre, in the
        # direction of sangle. When sdistance is zero then sangle is irrelevant. When sdistance
        # is non-zero it offsets the shadow from the object, as determined by the sangle.
        sdistance = 10
        if "shadowDistance" in shadow.attrib:
            distanceAttrib = shadow.get('shadowDistance')
            if distanceAttrib is not None:
                sdistance = mcf2rl * floor(float(distanceAttrib))

        intensity = 128
        if "shadowIntensity" in shadow.attrib:
            intensityAttrib = shadow.get('shadowIntensity')
            if intensityAttrib is not None:
                intensity = int(intensityAttrib) # range 1 .. 255, I think

        # you might think that sangle is the angle of the light source, but it is actually
        # the angle where the shadow should appear (exactly 180 degrees opposite). Not
        # unreasonable, when swidth sets the width of the shadow rather than how far away
        # the light source is. I guess the theory is that the users are not physicists!
        sangle = 135
        if "shadowAngle" in shadow.attrib:
            angleAttrib = shadow.get('shadowAngle')
            if angleAttrib is not None:
                sangle = floor(float(angleAttrib))
        if sangle < 0.0: # mcf range -179 .. +180
            sangle = sangle + 360 # range 0 .. 359

        shadowBottomLeft_x, shadowBottomLeft_y = \
            findShadowBottomLeft((frameBottomLeft_x, frameBottomLeft_y), sangle, sdistance, swidth)
        shadowWidth = frameWidth + swidth
        shadowHeight = frameHeight + swidth
        shadowColor = intensityToGrey(intensity) # reportlab.lib.colors.grey

        frm_table = Table(
            data=[[None]],
            colWidths=shadowWidth,
            rowHeights=shadowHeight,
            style=[
                # The two (0, 0) in each attribute represent the range of table cells that the style applies to.
                # Since there's only one cell at (0, 0), it's used for both start and end of the range
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('BACKGROUND', (0, 0), (0, 0), shadowColor),
                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
            ]
        )
        frm_table.wrapOn(pdf, shadowWidth, shadowHeight)
        frm_table.drawOn(pdf, shadowBottomLeft_x, shadowBottomLeft_y)


def warnAndIgnoreEnabledDecorationShadow(decoration):
    if getConfigurationBool(defaultConfigSection, "noShadows", "False"):
        return
    for shadow in decoration.findall('shadow'):
        if "shadowEnabled" in shadow.attrib:
            enabledAttrib = shadow.get('shadowEnabled')
            if enabledAttrib == '1':
                logging.warning("Ignoring shadow specified on text, that is not implemented!")
                continue


def processAreaTextTag(textTag, additional_fonts, area, areaHeight, areaRot, areaWidth, pdf, transx, transy, pgno): # noqa: C901 (too complex)
    # note: it would be better to use proper html processing here
    
    # Preprocess text to fix CEWE bugs: merge duplicate style attributes
    # CEWE sometimes generates invalid XML like: <li style="..." style="...">
    # We need to merge these into a single style attribute
    import re
    
    def merge_duplicate_styles(match):
        """Merge duplicate style attributes in a single tag."""
        full_tag = match.group(0)  # e.g., '<li style="..." style="...">'
        
        # Find all style="..." attributes in this specific tag
        style_pattern = r'style="([^"]*)"'
        styles = re.findall(style_pattern, full_tag)
        
        if len(styles) <= 1:
            # No duplicates, return unchanged
            return full_tag
        
        # Log warning about duplicate styles with context
        # Extract tag name for context
        tag_name_match = re.match(r'<(\w+)', full_tag)
        tag_name = tag_name_match.group(1) if tag_name_match else 'unknown'
        
        # Get position of this tag in the original text to show nearby text content
        tag_pos = textTag.text.find(full_tag)
        if tag_pos >= 0:
            # Find some actual text content near this tag (not HTML tags)
            # Look ahead after this tag for text content
            search_start = tag_pos + len(full_tag)
            search_end = min(len(textTag.text), search_start + 200)
            nearby = textTag.text[search_start:search_end]
            # Extract text between tags
            text_content = re.sub(r'<[^>]*>', '', nearby)[:20].strip()
            context = f"near text: '{text_content}'" if text_content else "at start/end"
        else:
            context = ""
        
        logging.warning(f"Merging duplicate 'style' attributes in <{tag_name}> tag ({len(styles)} instances) {context}")
        logging.warning(f"  Styles: {styles}")
        
        # Merge all style values
        merged_parts = []
        for s in styles:
            s = s.strip()
            if s:
                # Ensure ends with semicolon for proper CSS
                if not s.endswith(';'):
                    s += ';'
                merged_parts.append(s)
        merged_style = ' '.join(merged_parts).strip()
        
        # Replace: keep first style="..." and remove all subsequent ones
        # First, remove ALL style attributes
        tag_without_styles = re.sub(style_pattern, '', full_tag)
        
        # Then add the merged style back as the first attribute
        # Find position after tag name to insert style
        tag_name_match = re.match(r'(<\w+)(\s|>)', tag_without_styles)
        if tag_name_match:
            prefix = tag_name_match.group(1)  # e.g., '<li'
            rest = tag_without_styles[len(prefix):]  # everything after tag name
            return f'{prefix} style="{merged_style}"{rest}'
        
        # Fallback: shouldn't reach here, but return original if parsing fails
        return full_tag
    
    # Process each opening tag, merging duplicate style attributes
    text_content = re.sub(r'<\w+[^>]*>', merge_duplicate_styles, textTag.text)
    
    # Validate that we haven't lost any actual text content (only fixed attributes)
    # Strip all HTML tags and compare character counts
    original_text_only = re.sub(r'<[^>]*>', '', textTag.text)
    processed_text_only = re.sub(r'<[^>]*>', '', text_content)
    
    if len(original_text_only) != len(processed_text_only):
        logging.error("=" * 80)
        logging.error("PREPROCESSING VALIDATION FAILED: Text content length changed!")
        logging.error(f"Original text-only length: {len(original_text_only)}")
        logging.error(f"Processed text-only length: {len(processed_text_only)}")
        logging.error(f"Difference: {len(processed_text_only) - len(original_text_only)} characters")
        logging.error("-" * 80)
        logging.error("Original text-only content:")
        logging.error(original_text_only)
        logging.error("-" * 80)
        logging.error("Processed text-only content:")
        logging.error(processed_text_only)
        logging.error("=" * 80)
        raise ValueError("Text preprocessing corrupted content - text length mismatch")
    
    try:
        htmlxml = etree.XML(text_content)
        # Log what we successfully parsed
        body = htmlxml.find('.//body')
        if body is not None:
            # Log all direct children of body to see structure
            body_children = list(body)
        else:
            logging.warning("No <body> tag found in parsed HTML!")
    except etree.XMLSyntaxError as e:
        # Log detailed error information for debugging XML parsing issues
        logging.error("=" * 80)
        logging.error("XML PARSING ERROR in text area")
        logging.error(f"Error: {e}")
        logging.error(f"Original text content ({len(textTag.text)} characters):")
        logging.error(textTag.text)
        logging.error("-" * 80)
        logging.error(f"Preprocessed text content ({len(text_content)} characters):")
        logging.error(text_content)
        logging.error("-" * 80)
        
        # Try to highlight the problematic portion based on column number
        if hasattr(e, 'position') and e.position:
            col = e.position[1] if len(e.position) > 1 else None
        else:
            # Try to extract column from error message (e.g., "column 3838")
            import re
            match = re.search(r'column (\d+)', str(e))
            col = int(match.group(1)) if match else None
        
        if col is not None:
            # Show context around the error (30 chars before and after)
            start = max(0, col - 30)
            end = min(len(text_content), col + 30)
            context = text_content[start:end]
            marker_pos = min(30, col - start)
            
            logging.error(f"Context around column {col} in preprocessed text:")
            logging.error(f"  {context}")
            logging.error(f"  {' ' * marker_pos}^ (error position)")
        
        logging.error("=" * 80)
        # Re-throw the error for now
        raise
    
    body = htmlxml.find('.//body')
    bstyle = dict([kv.split(':') for kv in body.get('style').lstrip(' ').rstrip(';').split('; ')])
    try:
        bodyfs = floor(float(bstyle['font-size'].strip("pt")))
    except: # noqa: E722
        bodyfs = 12
    family = bstyle['font-family'].strip("'")
    bodyfont = getAvailableFont(family, pdf, additional_fonts)

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
    leftPad = mcf2rl * tablelmarg
    rightPad = mcf2rl * tablermarg
    bottomPad = mcf2rl * tablebmarg
    topPad = mcf2rl * tabletmarg

    # if this is text art, then we do the whole thing differently.
    cwtextart = area.findall('decoration/cwtextart')
    if len(cwtextart) > 0:
        pdf.translate(transx, transy)
        pdf.rotate(-areaRot)
        for decorationTag in area.findall('decoration'):
            processDecorationBorders(decorationTag, areaHeight, areaWidth, pdf)
        bodyhtml = etree.tostring(body, pretty_print=True, encoding="unicode")
        radius = topPad - leftPad # is this really what they use for the radius?
        handleTextArt(pdf, radius, bodyhtml, cwtextart)
        pdf.rotate(areaRot)
        pdf.translate(-transx, -transy)
        return

    pdf.translate(transx, transy)
    pdf.rotate(-areaRot)

    # we don't do shadowing on texts, but we could at least warn about that...
    for decorationTag in area.findall('decoration'):
        warnAndIgnoreEnabledDecorationShadow(decorationTag)

    # Get the background color. It is stored in an extra element.
    backgroundColor = None
    backgroundColorAttrib = area.get('backgroundcolor')
    if backgroundColorAttrib is not None:
        backgroundColor = ReorderColorBytesMcf2Rl(backgroundColorAttrib)

    # set default para style in case there are no spans to set it.
    pdf_styleN = CreateParagraphStyle(reportlab.lib.colors.black, bodyfont, bodyfs)

    # for debugging the background colour may be useful, but it is not used in production
    # since we started to use ColorFrame to colour the background, and it is thus left
    # unset by CreateParagraphStyle
    # pdf_styleN.backColor = reportlab.lib.colors.HexColor("0xFFFF00")

    # There may be multiple "index entry" paragraphs in the text area.
    # Concatenating them to just one index entry seems to work in practice
    indexEntryText = None

    # Track all direct children of body to validate we process everything
    all_body_children = list(body)
    unprocessed_children = set(all_body_children)  # Will remove elements as we process them
    
    htmlparas = body.findall(".//p")
    
    for p in htmlparas:
        # Mark this paragraph as processed
        unprocessed_children.discard(p)
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
        logging.debug(f"Paragraph has {len(htmlspans)} child elements")
        for child in htmlspans[:3]:  # Log first 3 to see what they are
            logging.debug(f"  Child tag: {child.tag}")
        if len(htmlspans) < 1: # i.e. there are no spans, just a paragraph
            paragraphText = '<para autoLeading="max">'
            paragraphText, maxfs = AppendItemTextInStyle(paragraphText, p.text, p, pdf,
                additional_fonts, bodyfont, bodyfs, bweight, bstyle)
            paragraphText += '</para>'
            usefs = maxfs if maxfs > 0 else bodyfs
            pdf_styleN.leading = usefs * finalLeadingFactor # line spacing (text + leading)
            pdf_flowableList.append(Paragraph(paragraphText, pdf_styleN))
            originalFont = CollectItemFontFamily(p, family)
            if albumIndex.CheckForIndexEntry(originalFont, bodyfs):
                indexEntryText = Index.AppendIndexText(indexEntryText, p.text)

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
                        originalFont = CollectItemFontFamily(span, family)
                        if albumIndex.CheckForIndexEntry(originalFont, spanfs):
                            indexEntryText = Index.AppendIndexText(indexEntryText, span.text)

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
                    logging.warning(f"Ignoring unhandled tag {item.tag} in text area (tag content: {etree.tostring(item, encoding='unicode')[:100]}...)")

            # try to create a paragraph with the current text and style. Catch errors.
            try:
                paragraphText += '</para>'
                usefs = maxfs if maxfs > 0 else bodyfs
                pdf_styleN.leading = usefs * finalLeadingFactor  # line spacing (text + leading)
                pdf_flowableList.append(Paragraph(paragraphText, pdf_styleN))
            except Exception:
                logging.exception('Exception')

    # Process <ul> (unordered list) elements - bulleted lists
    htmllists = body.findall("ul")
    
    for ul in htmllists:
        # Mark this list as processed
        unprocessed_children.discard(ul)
        
        listitems = ul.findall("li")
        
        for li in listitems:
            maxfs = 0
            
            # Create a copy of the style for this list item with hanging indent
            list_styleN = ParagraphStyle('list_item', parent=pdf_styleN)
            # Hanging indent: first line at 0, subsequent lines indented
            # Calculate indent based on font size - approximately 2x the font size 
            # accounts for bullet width + space
            bullet_indent = bodyfs * 1.65  # Adjust multiplier if needed (1.5 - 2.5 range)
            list_styleN.leftIndent = bullet_indent  # Where wrapped lines start
            list_styleN.firstLineIndent = -bullet_indent/2  # Pull first line (with bullet) back halfway position 0
            bullet_txt = '• '

            # Check alignment (though lists are typically left-aligned)
            if li.get('align') == 'center':
                list_styleN.alignment = reportlab.lib.enums.TA_CENTER
            elif li.get('align') == 'right':
                list_styleN.alignment = reportlab.lib.enums.TA_RIGHT
            elif li.get('align') == 'justify':
                list_styleN.alignment = reportlab.lib.enums.TA_JUSTIFY
            else:
                list_styleN.alignment = reportlab.lib.enums.TA_LEFT
            
            # Get line height from <li> style if present
            pLineHeight = 1.0
            liStyleAttribute = li.get('style')
            if liStyleAttribute is not None:
                liStyle = dict([kv.split(':') for kv in
                    li.get('style').lstrip(' ').rstrip(';').split('; ')])
                if 'line-height' in liStyle.keys():
                    try:
                        pLineHeight = floor(float(liStyle['line-height'].strip("%")))/100.0
                    except: # noqa: E722
                        logging.warning(f"Ignoring invalid list item line-height setting {liStyleAttribute}")
            finalLeadingFactor = LineScales.lineScaleForFont(bodyfont) * pLineHeight
            
            # Start paragraph - we'll add bullet inside the styled text
            paragraphText = '<para autoLeading="max">'
            
            # Check if there are child elements (spans, br, etc.)
            lispans = li.findall(".*")
            
            if len(lispans) < 1:
                # Simple list item with just text, no spans
                # Prepend bullet to the text so it gets styled
                bullet_plus_text = bullet_txt + (li.text != None and li.text or "")
                paragraphText, maxfs = AppendItemTextInStyle(paragraphText, bullet_plus_text, li, pdf,
                    additional_fonts, bodyfont, bodyfs, bweight, bstyle)
                paragraphText += '</para>'
                usefs = maxfs if maxfs > 0 else bodyfs
                list_styleN.leading = usefs * finalLeadingFactor
                pdf_flowableList.append(Paragraph(paragraphText, list_styleN))
            else:
                # List item with spans and other formatting
                bullet_plus_text = bullet_txt + (li.text != None and li.text or "")
                paragraphText, maxfs = AppendItemTextInStyle(paragraphText, bullet_plus_text, li, pdf,
                    additional_fonts, bodyfont, bodyfs, bweight, bstyle)
                paragraphText, maxfs = AppendItemTextInStyle(paragraphText, bullet_plus_text, li, pdf,
                    additional_fonts, bodyfont, bodyfs, bweight, bstyle)
                usefs = maxfs if maxfs > 0 else bodyfs
                list_styleN.leading = usefs * finalLeadingFactor
                
                # Process child elements (spans, br, etc.)
                for item in lispans:
                    if item.tag == 'br':
                        br = item
                        # For lists, we don't typically break into multiple paragraphs on <br>
                        # Instead, insert a line break within the same paragraph
                        paragraphText += '<br/>'
                        if br.tail:
                            paragraphText, maxfs = AppendItemTextInStyle(paragraphText, br.tail, li, pdf,
                                additional_fonts, bodyfont, bodyfs, bweight, bstyle)
                    
                    elif item.tag == 'span':
                        span = item
                        spanfont, spanfs, spanweight, spanstyle = CollectFontInfo(span, pdf, additional_fonts, bodyfont, bodyfs, bweight)
                        
                        maxfs = max(maxfs, spanfs)
                        
                        paragraphText = AppendSpanStart(paragraphText, spanfont, spanfs, spanweight, spanstyle, bstyle)
                        
                        if span.text is not None:
                            paragraphText = AppendText(paragraphText, html.escape(span.text))
                        
                        # Handle line breaks within spans
                        brs = span.findall(".//br")
                        if len(brs) > 0:
                            paragraphText = AppendSpanEnd(paragraphText, spanweight, spanstyle, bstyle)
                            for br in brs:
                                paragraphText += '<br/>'
                                if br.tail:
                                    paragraphText, maxfs = AppendItemTextInStyle(paragraphText, br.tail, span, pdf,
                                        additional_fonts, bodyfont, bodyfs, bweight, bstyle)
                        else:
                            paragraphText = AppendSpanEnd(paragraphText, spanweight, spanstyle, bstyle)
                        
                        if span.tail is not None:
                            paragraphText = AppendText(paragraphText, html.escape(span.tail))
                    
                    else:
                        logging.warning(f"Ignoring unhandled tag {item.tag} in list item (tag content: {etree.tostring(item, encoding='unicode')[:100]}...)")
                
                # Finalize the list item paragraph
                try:
                    paragraphText += '</para>'
                    usefs = maxfs if maxfs > 0 else bodyfs
                    list_styleN.leading = usefs * finalLeadingFactor
                    pdf_flowableList.append(Paragraph(paragraphText, list_styleN))
                except Exception:
                    logging.exception('Exception')

    # The <table> tag contains margin info, not actual content - mark it as processed
    table = body.find('table')
    if table is not None:
        unprocessed_children.discard(table)
    
    # Validate: warn about any body children that we didn't process
    if unprocessed_children:
        logging.warning("=" * 80)
        logging.warning("TEXT CONTENT BEING SILENTLY IGNORED!")
        logging.warning(f"Found {len(unprocessed_children)} unprocessed elements as direct children of <body>:")
        for child in unprocessed_children:
            child_text = ''.join(child.itertext())[:100]  # Get text content, first 100 chars
            logging.warning(f"  Ignoring <{child.tag}> with {len(list(child))} children")
            logging.warning(f"    Text content preview: {child_text}")
            logging.warning(f"    XML: {etree.tostring(child, encoding='unicode')[:200]}...")
        logging.warning("=" * 80)

    if indexEntryText:
        albumIndex.AddIndexEntry(pgno, indexEntryText)

    # Add a frame object that can contain multiple paragraphs. Margins (padding) are specified in
    # the editor in mm, arriving in the mcf in 1/10 mm, but appearing in the html with the unit "px".
    # This is a bit strange, but ignoring the "px" and using mcf2rl seems to work ok.
    frameWidth = mcf2rl * areaWidth
    frameHeight = mcf2rl * areaHeight
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
        processDecorationBorders(decorationTag, areaHeight, areaWidth, pdf)

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
        mcf2rl * -0.5 * areaWidth, mcf2rl * -0.5 * areaHeight,
        width=mcf2rl * areaWidth, height=mcf2rl * areaHeight, mask='auto')
    if decoration is not None:
        processDecorationBorders(decoration, areaHeight, areaWidth, pdf)
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

        transx = mcf2rl * cx
        transy = mcf2rl * cy

        # process images
        for imageTag in area.findall('imagebackground') + area.findall('image'):
            processAreaImageTag(imageTag, area, areaHeight, areaRot, areaWidth, imagedir, productstyle, mcfBaseFolder, pagetype, pdf, pw, transx, transy)

        # process text
        for textTag in area.findall('text'):
            processAreaTextTag(textTag, additional_fonts, area, areaHeight, areaRot, areaWidth, pdf, transx, transy, pageNumber)

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
    pdf.setPageSize((mcf2rl * pw, mcf2rl * ph))

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
    global pageNumberingInfo  # pylint: disable=global-statement
    global albumIndex  # pylint: disable=global-statement

    clipartDict = {}    # a dictionary for clipart element IDs to file name
    clipartPathList = tuple()
    passepartoutDict = None    # a dictionary for passepartout  desginElementIDs to file name
    passepartoutFolders = tuple[str]() # global variable with the folders for passepartout frames
    pageNumberingInfo = None

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

    try:
        albumIndex = Index(configuration['INDEX'])
    except KeyError:
        albumIndex = Index(None)

    # Load fonts
    availableFonts = findAndRegisterFonts(defaultConfigSection, appDataDir, albumBaseFolder, cewe_folder)

    # Read any configured non-standard line scales for specified fonts, creating a map of font name to line scale
    LineScales.setupFontLineScales(defaultConfigSection)

    # extract basic album properties
    articleConfigElement = fotobook.find('articleConfig')
    if articleConfigElement is None:
        logging.error(f'{albumname} is an old version. Open it in the album editor and save before retrying the pdf conversion. Exiting.')
        sys.exit(1)

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

    pageNumberElement = fotobook.find('pagenumbering')
    if pageNumberElement is not None:
        pnpos = int(pageNumberElement.get('position'))
        if pnpos != 0: # 0 implies no numbering
            # make a page number description object to use later
            pageNumberingInfo = PageNumberingInfo(pageNumberElement, pdf, availableFonts)

    # generate all the requested pages
    processPages(fotobook, mcfBaseFolder, imageFolder, productstyle, pdf, pageCount, pageNumbers,
        cewe_folder, availableFonts, backgroundLocations, bg_notFoundDirList)

    # save final output pdf
    try:
        pdf.save()
    except Exception as ex:
        logging.error(f'Could not save the output file: {str(ex)}')

    pdf = []

    if albumIndex.indexing:
        # At this point we have an index of items (selected on the basis of their font characteristics)
        #   albumIndex.ShowIndex()
        indexPdfFileName = albumIndex.SaveIndexPdf(outputFileName, albumTitle, pagesize)
        indexPngFileName = albumIndex.SaveIndexPng(indexPdfFileName)
        albumIndex.MergeAlbumAndIndexPng(outputFileName, indexPngFileName)
        # most usual is to delete the index pdf, but leave the index png which could be added
        # to the original with the cewe editor, and then you get it in the printed edition as well
        if albumIndex.deleteIndexPdf and os.path.exists(indexPdfFileName):
            os.remove(indexPdfFileName)
        if albumIndex.deleteIndexPng and os.path.exists(indexPngFileName):
            os.remove(indexPngFileName)

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


def addPageNumber(pni, pdf, pageNumber, productStyle, oddpage):
    if pni is None or pni.position == 0:
        return

    paragraphText = pni.getParagraphText(pageNumber)
    paragraph = Paragraph(paragraphText, pni.paragraphStyle)
    paraWidth = paragraph.minWidth()
    _, paraHeight = paragraph.wrap(1000, 1000)
    frameWidthFiddleFactor = 3 + pni.fontsize * 1.5
    # Copilot thinks a fiddle factor is necessary due to imprecisions in the reportlab suite!
    # The fiddle factor calculation comes from trial and error! Surely there's a better solution?
    frameWidth = paraWidth + frameWidthFiddleFactor
    frameHeight = paraHeight + 3

    if 'singlePageNumberPosition' in defaultConfigSection:
        pnp = PageNumberPosition.ToEnum(defaultConfigSection['singlePageNumberPosition'].strip())
    else:
        pnp = PageNumberPosition.ORIGINAL

    transx, transy = getPageNumberXy(pnp, pni, pdf, frameWidth, frameHeight, productStyle, oddpage)
    pdf.translate(transx, transy)
    pdf_flowList = [paragraph]
    newFrame = ColorFrame(0, 0, frameWidth, frameHeight, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    # newFrame.background = reportlab.lib.colors.aliceblue # uncomment for debugging
    newFrame.background = pni.bgcolor
    newFrame.addFromList(pdf_flowList, pdf)
    pdf.translate(-transx, -transy)


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
                    addPageNumber(pageNumberingInfo, pdf, pageNumber, productstyle, oddpage)

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

                if AlbumInfo.isAlbumProduct(productstyle) and pagetype in [PageType.EmptyPage, PageType.Normal]:
                    addPageNumber(pageNumberingInfo, pdf, pageNumber, productstyle, oddpage)

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
