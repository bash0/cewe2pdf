#!/usr/bin/env python
# -*- coding: utf-8 -*-

# In this file it is permitted to catch exceptions on a broad basis since there
# are many things that can go wrong with file handling and xml parsing:
#    pylint: disable=bare-except,broad-except
# We're not quite at the level of documenting all the classes and functions yet :-)
#    pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

'''
Create pdf files from CEWE .mcf photo books (cewe-fotobuch)
version 0.11 (Dec 2019)

This script reads CEWE .mcf files using the lxml library
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
import glob

import logging
import logging.config
import yaml

import os.path
import os
import tempfile
import html
import traceback

import argparse  # to parse arguments
import configparser  # to read config file, see https://docs.python.org/3/library/configparser.html

from io import BytesIO
from math import sqrt, floor

from pathlib import Path

from fontTools import ttLib

from reportlab.pdfgen import canvas
import reportlab.lib.pagesizes
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Frame, Table
from reportlab.lib.styles import ParagraphStyle
# from reportlab.lib.styles import getSampleStyleSheet

from lxml import etree

import PIL
from clpFile import ClpFile  # for clipart .CLP and .SVG files
from passepartout import Passepartout

if hasattr(sys, 'frozen'):
    # This is needed for compiled, i.e. frozen programs on Windows to find their dlls.
    # this _may_ pose a security risk, as normally on Linux the current path is on the path
    dllpath = os.path.dirname(os.path.realpath(sys.argv[0]))
    if dllpath not in os.environ:
        os.environ["PATH"] += os.pathsep + dllpath

if os.path.exists('loggerconfig.yaml'):
    with open('loggerconfig.yaml', 'r') as f:
        config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
else:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

configlogger = logging.getLogger("cewe2pdf.config")

# ### settings ####
image_quality = 86  # 0=worst, 100=best. This is the JPEG quality option.
image_res = 150  # dpi  The resolution of normal images will be reduced to this value, if it is higher.
bg_res = 100  # dpi The resolution of background images will be reduced to this value, if it is higher.
# ##########

# .mcf units are 0.1 mm
# Tabs seem to be in 8mm pitch
tab_pitch = 80
line_scale = 1.1

# definitions
formats = {"ALB82": reportlab.lib.pagesizes.A4,
           "ALB69": (5400/100/2*reportlab.lib.units.cm, 3560/100*reportlab.lib.units.cm)}  # add other page sizes here
f = 72. / 254.  # convert from mcf (unit=0.1mm) to reportlab (unit=inch/72)

tempFileList = []  # we need to remove all this temporary files at the end

# reportlab defaults
# pdf_styles = getSampleStyleSheet()
# pdf_styleN = pdf_styles['Normal']
pdf_flowableList = []

clipartDict = dict()    # a dictionary for clipart element IDs to file name
clipartPathList = tuple()
passepartoutDict = None    # a dictionary for passepartout  desginElementIDs to file name
passepartoutFolders = tuple() # global variable with the folders for passepartout frames
fontSubstitutions = list() # used to avoid repeated messages

def autorot(im):
    # some cameras return JPEG in MPO container format. Just use the first image.
    if im.format != 'JPEG' and im.format != 'MPO':
        return im
    exifdict = im._getexif()
    if exifdict is not None and 274 in list(exifdict.keys()):
        orientation = exifdict[274]

        if orientation == 2:
            im = im.transpose(PIL.Image.FLIP_LEFT_RIGHT)
        elif orientation == 3:
            im = im.transpose(PIL.Image.ROTATE_180)
        elif orientation == 4:
            im = im.transpose(PIL.Image.FLIP_TOP_BOTTOM)
        elif orientation == 5:
            im = im.transpose(PIL.Image.FLIP_TOP_BOTTOM)
            im = im.transpose(PIL.Image.ROTATE_90)
        elif orientation == 6:
            im = im.transpose(PIL.Image.ROTATE_270)
        elif orientation == 7:
            im = im.transpose(PIL.Image.FLIP_LEFT_RIGHT)
            im = im.transpose(PIL.Image.ROTATE_90)
        elif orientation == 8:
            im = im.transpose(PIL.Image.ROTATE_90)
    return im


def findFileByExtInDirs(filebase, extList, paths):
    for p in paths:
        for ext in extList:
            testPath = os.path.join(p, filebase + ext)
            if os.path.exists(testPath):
                return testPath

    prtStr = 'Could not find %s [%s] in paths %s' % (filebase, ' '.join(extList), ', '.join(paths))
    logging.info(prtStr)
    raise ValueError(prtStr)


def findFileInDirs(filenames, paths):
    if not isinstance(filenames, list):
        filenames = [filenames]
    for filename in filenames:
        for p in paths:
            testPath = os.path.join(p, filename)
            if os.path.exists(testPath):
                return testPath

    logging.debug('Could not find %s in %s paths' % (filenames, ', '.join(paths)))
    raise ValueError('Could not find %s in %s paths' % (filenames, ', '.join(paths)))


def getPageElementForPageNumber(fotobook, pageNumber):
    return fotobook.find("./page[@pagenr='{}']".format(floor(2 * (pageNumber / 2))))


# This is only used for the <background .../> tags. The stock backgrounds use this element.
def processBackground(backgroundTags, bg_notFoundDirList, cewe_folder, backgroundLocations, keepDoublePages, oddpage, pagetype, pdf, ph, pw):
    if pagetype == "emptypage":  # don't draw background for the empty pages. That is page nr. 1 and pageCount-1.
        return
    if backgroundTags is not None and len(backgroundTags) > 0:
        # look for a tag that has an alignment attribute
        for curTag in backgroundTags:
            if curTag.get('alignment') is not None:
                backgroundTag = curTag
                break

        if (backgroundTag is not None and cewe_folder is not None
                and backgroundTag.get('designElementId') is not None):
            bg = backgroundTag.get('designElementId')
            # example: fading="0" hue="270" rotation="0" type="1"
            backgroundFading = 0 # backgroundFading not used yet pylint: disable=unused-variable
            if "fading" in backgroundTag.attrib:
                if float(backgroundTag.get('fading')) != 0:
                    logging.warning('value of background attribute not supported: fading = %s' % backgroundTag.get(
                        'fading'))
            backgroundHue = 0 # backgroundHue not used yet pylint: disable=unused-variable
            if "hue" in backgroundTag.attrib:
                if float(backgroundTag.get('hue')) != 0:
                    logging.warning(
                        'value of background attribute not supported: hue =  %s' % backgroundTag.get('hue'))
            backgroundRotation = 0 # backgroundRotation not used yet pylint: disable=unused-variable
            if "rotation" in backgroundTag.attrib:
                if float(backgroundTag.get('rotation')) != 0:
                    logging.warning('value of background attribute not supported: rotation =  %s' % backgroundTag.get(
                        'rotation'))
            backgroundType = 1 # backgroundType not used yet pylint: disable=unused-variable
            if "type" in backgroundTag.attrib:
                if int(backgroundTag.get('type')) != 1:
                    logging.warning(
                        'value of background attribute not supported: type =  %s' % backgroundTag.get('type'))
            try:
                bgPath = ""
                bgPath = findFileInDirs([bg + '.bmp', bg + '.webp', bg + '.jpg'], backgroundLocations)
                areaWidth = pw*2
                if keepDoublePages:
                    areaWidth = pw
                areaHeight = ph
                if pagetype != 'singleside' and oddpage and not keepDoublePages:
                    ax = -areaWidth / 2.
                else:
                    ax = 0
                logging.debug("Reading background file: {}".format(bgPath))
                # webp doesn't work with PIL.Image.open in Anaconda 5.3.0 on Win10
                imObj = PIL.Image.open(bgPath)
                # create a in-memory byte array of the image file
                im = bytes()
                memFileHandle = BytesIO(im)
                imObj = imObj.convert("RGB")
                imObj.save(memFileHandle, 'jpeg')
                memFileHandle.seek(0)
                # im = imread(bgpath) #does not work with 1-bit images
                pdf.drawImage(ImageReader(
                    memFileHandle), f * ax, 0, width=f * areaWidth, height=f * areaHeight)
                # pdf.drawImage(ImageReader(bgpath), f * ax, 0, width=f * aw, height=f * ah)
            except Exception as ex:
                if bgPath not in bg_notFoundDirList:
                    logging.error("Could not find background or error when adding to pdf")
                    logging.exception('Exception')
                bg_notFoundDirList.add(bgPath)
    return


def processAreaImageTag(imageTag, area, areaHeight, areaRot, areaWidth, imagedir, keepDoublePages, mcfBaseFolder, pagetype, pdf, pw, transx, transy):
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
        if keepDoublePages:
            img_transx = transx + f * pw/2
        else:
            img_transx = transx + f * pw
    else:
        img_transx = transx

    # correct for exif rotation
    im = autorot(im)
    # get the cutout position and scale
    imleft = float(imageTag.find('cutout').get(
        'left').replace(',', '.'))
    imtop = float(imageTag.find('cutout').get(
        'top').replace(',', '.'))
    # imageWidth_px, imageHeight_px = im.size
    imScale = float(imageTag.find('cutout').get('scale'))

    # we need to take care of changes introduced by passepartout elements, before further image processing
    passepartoutid = imageTag.get('passepartoutDesignElementId')
    frameClipartFileName = None
    maskClipartFileName = None
    frameDeltaX_mcfunit = 0
    frameDeltaY_mcfunit = 0
    imgCropWidth_mcfunit = areaWidth
    imgCropHeight_mcfunit = areaHeight
    if passepartoutid is not None:
        logging.warning('Frames (passepartout) are not fully implemented {}'.format(passepartoutid))
        # re-generate the index of designElementId to .xml files, if it does not exist
        passepartoutid = int(passepartoutid)    # we need to work with a number below
        global passepartoutDict # pylint: disable=global-statement
        if passepartoutDict is None:
            configlogger.info("Regenerating passepartout index from .XML files.")
            global passepartoutFolders  # pylint: disable=global-statement
            passepartoutDict = Passepartout.buildElementIdIndex(passepartoutFolders)
        # read information from .xml file
        try:
            pptXmlFileName = passepartoutDict[passepartoutid]
        except: # noqa: E722
            pptXmlFileName = None
        if pptXmlFileName is None:
            logging.error("Can't find passepartout for {}".format(passepartoutid))
        else:
            pptXmlFileName = passepartoutDict[passepartoutid]
            pptXmlInfo = Passepartout.extractInfoFromXml(pptXmlFileName, passepartoutid)
            frameClipartFileName = Passepartout.getClipartFullName(pptXmlInfo)
            maskClipartFileName = Passepartout.getMaskFullName(pptXmlInfo)
            logging.debug("Using mask file: {}".format(maskClipartFileName))
            # draw the passepartout clipart file.
            # ToDo: apply the masking
            frameAlpha = 255
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
            (new_w, new_h), PIL.Image.ANTIALIAS)
    im.load()

    # apply the frame mask from the passepartout to the image
    if maskClipartFileName is not None:
        maskClp = loadClipart(maskClipartFileName)
        im = maskClp.applyAsAlphaMaskToFoto(im)

    # re-compress image
    jpeg = tempfile.NamedTemporaryFile()
    # we need to close the temporary file, because otherwise the call to im.save will fail on Windows.
    jpeg.close()
    if im.mode == 'RGBA' or im.mode == 'P':
        im.save(jpeg.name, "PNG")
    else:
        im.save(jpeg.name, "JPEG",
                quality=image_quality)

    # place image
    logging.debug("image: {}".format(imageTag.get('filename')))
    pdf.translate(img_transx, transy)   # we need to go to the center for correct rotation
    pdf.rotate(-areaRot)   # rotation around center of area
    # calculate the non-symmetric shift of the center, given the left pos and the width.
    frameShiftX_mcf = -(frameDeltaX_mcfunit-((areaWidth - imgCropWidth_mcfunit) - frameDeltaX_mcfunit))/2
    frameShiftY_mcf = (frameDeltaY_mcfunit-((areaHeight - imgCropHeight_mcfunit) - frameDeltaY_mcfunit))/2
    pdf.translate(frameShiftX_mcf * f, -frameShiftY_mcf * f) # for adjustments from passepartout
    pdf.drawImage(ImageReader(jpeg.name),
        f * -0.5 * imgCropWidth_mcfunit,
        f * -0.5 * imgCropHeight_mcfunit,
        width=f * imgCropWidth_mcfunit,
        height=f * imgCropHeight_mcfunit,
        mask='auto')
    pdf.translate(-frameShiftX_mcf * f, frameShiftY_mcf * f) # for adjustments from passepartout

    # we need to draw our passepartout after the real image, so it overlays it.
    if frameClipartFileName is not None:
        # we set the transx, transy, and areaRot for the clipart to zero, because our current pdf object
        # already has these transformations applied. So don't do it twice.
        insertClipartFile(frameClipartFileName, [], 0, areaWidth, areaHeight, frameAlpha, pdf, 0, 0)

    for decorationTag in area.findall('decoration'):
        processAreaDecorationTag(decorationTag, areaHeight, areaWidth, pdf)

    pdf.rotate(areaRot)
    pdf.translate(-img_transx, -transy)

    # we now have temporary file, that we need to delete after pdf creation
    tempFileList.append(jpeg.name)
    # we can not delete now, because file is opened by pdf library


def AppendText(paratext, newtext):
    if newtext is None:
        return paratext
    return paratext + newtext.replace('\t', '&nbsp;&nbsp;&nbsp;')


def AppendBreak(paragraphText, parachild):
    br = parachild
    paragraphText = AppendText(paragraphText, "<br></br>&nbsp;")
    paragraphText = AppendText(paragraphText, br.tail)
    return paragraphText


def CreateParagraphStyle(backgroundColor, textcolor, font, fontsize):
    parastyle = ParagraphStyle(None, None,
        alignment=reportlab.lib.enums.TA_LEFT,  # will often be overridden
        fontSize=fontsize,
        fontName=font,
        leading=fontsize*line_scale,  # line spacing (text + leading)
        borderPadding=0,
        borderWidth=0,
        leftIndent=0,
        rightIndent=0,
        embeddedHyphenation=1,  # allow line break on existing hyphens
        textColor=textcolor,
        backColor=backgroundColor)
    return parastyle


def IsBold(weight):
    return weight > 400


def IsItalic(itemstyle, outerstyle):
    if 'font-style' in itemstyle:
        return itemstyle['font-style'].strip(" ") == "italic"
    if 'font-style' in outerstyle:
        return outerstyle['font-style'].strip(" ") == "italic"
    return False


def IsUnderline(itemstyle, outerstyle):
    if 'text-decoration' in itemstyle:
        return itemstyle['text-decoration'].strip(" ") == "underline"
    if 'text-decoration' in outerstyle:
        return outerstyle['text-decoration'].strip(" ") == "underline"
    return False


def Dequote(s):
    """
    If a string has single or double quotes around it, remove them.
    Make sure the pair of quotes match.
    If a matching pair of quotes is not found, return the string unchanged.
    """
    if (s[0] == s[-1]) and s.startswith(("'", '"')):
        return s[1:-1]
    return s

def noteFontSubstitution(family, replacement):
    fontSubstitutionPair = family + "/" + replacement
    fontSubsNotedAlready = fontSubstitutionPair in fontSubstitutions 
    if not fontSubsNotedAlready:
        fontSubstitutions.append(fontSubstitutionPair)
    if logging.root.isEnabledFor(logging.DEBUG):
        # At DEBUG level we log all font substitutions, making it easier to find them in the mcf
        logging.debug("Using font family = '%s' (wanted %s)" % (replacement, family))
        return
    # At other logging levels we simply log the first font substitution
    if not fontSubsNotedAlready:
        logging.warning("Using font family = '%s' (wanted %s)" % (replacement, family))

def CollectFontInfo(item, pdf, additional_fonts, dfltfont, dfltfs, bweight):
    spanfont = dfltfont
    spanfs = dfltfs
    spanweight = bweight
    spanstyle = dict([kv.split(':') for kv in
                    item.get('style').lstrip(' ').rstrip(';').split('; ')])
    if 'font-family' in spanstyle:
        spanfamily = spanstyle['font-family'].strip("'")
        if spanfamily in pdf.getAvailableFonts():
            spanfont = spanfamily
        elif spanfamily in additional_fonts:
            spanfont = spanfamily
        if spanfamily != spanfont:
            noteFontSubstitution(spanfamily, spanfont)

    if 'font-weight' in spanstyle:
        try:
            spanweight = int(Dequote(spanstyle['font-weight']))
        except: # noqa: E722
            spanweight = 400

    if 'font-size' in spanstyle:
        spanfs = floor(float(spanstyle['font-size'].strip("pt")))
    return spanfont, spanfs, spanweight, spanstyle


def AppendSpanStart(paragraphText, bgColorAttrib, font, fsize, fweight, fstyle, outerstyle):
    """
    Remember this is not really HTML, though it looks that way.
    See 6.2 Paragraph XML Markup Tags in the reportlabs user guide.
    """
    paragraphText = AppendText(paragraphText, '<font name="' + font + '"' + ' size=' + str(fsize))

    if 'color' in fstyle:
        paragraphText = AppendText(paragraphText, ' color=' + fstyle['color'])

    # This old strategy doesn't interpret background alpha values correctly, background is 
    # now done in processAreaTextTag (credit seaeagle1, changeset 687fe50)
    #    if bgColorAttrib is not None:
    #        paragraphText = AppendText(paragraphText, ' backcolor=' + bgColorAttrib)

    paragraphText = AppendText(paragraphText, '>')

    if IsBold(fweight):  # ref https://www.w3schools.com/csSref/pr_font_weight.asp
        paragraphText = AppendText(paragraphText, "<b>")
    if IsItalic(fstyle, outerstyle):
        paragraphText = AppendText(paragraphText, '<i>')
    if IsUnderline(fstyle, outerstyle):
        paragraphText = AppendText(paragraphText, '<u>')
    return paragraphText


def AppendSpanEnd(paragraphText, weight, style, outerstyle):
    if IsUnderline(style, outerstyle):
        paragraphText = AppendText(paragraphText, '</u>')
    if IsItalic(style, outerstyle):
        paragraphText = AppendText(paragraphText, '</i>')
    if IsBold(weight):
        paragraphText = AppendText(paragraphText, "</b>")
    paragraphText = AppendText(paragraphText, '</font>')
    return paragraphText


def AppendItemTextInStyle(paragraphText, text, item, pdf, additional_fonts, bodyfont, bodyfs, bweight, bstyle, bgColorAttrib):
    pfont, pfs, pweight, pstyle = CollectFontInfo(item, pdf, additional_fonts, bodyfont, bodyfs, bweight)
    paragraphText = AppendSpanStart(paragraphText, bgColorAttrib, pfont, pfs, pweight, pstyle, bstyle)
    if text is None:
        paragraphText = AppendText(paragraphText, "")
    else:
        paragraphText = AppendText(paragraphText, html.escape(text))
    paragraphText = AppendSpanEnd(paragraphText, pweight, pstyle, bstyle)
    return paragraphText, pfs

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


def processAreaTextTag(textTag, additional_fonts, area, areaHeight, areaRot, areaWidth, pdf, transx, transy):
    # note: it would be better to use proper html processing here
    htmlxml = etree.XML(textTag.text)
    body = htmlxml.find('.//body')
    bstyle = dict([kv.split(':') for kv in body.get('style').lstrip(' ').rstrip(';').split('; ')])
    try:
        bodyfs = floor(float(bstyle['font-size'].strip("pt")))
    except: # noqa: E722
        bodyfs = 12
    family = bstyle['font-family'].strip("'")
    if family in pdf.getAvailableFonts():
        bodyfont = family
    elif family in additional_fonts:
        bodyfont = family
    else:
        bodyfont = 'Helvetica'
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
                logging.warning("Ignoring invalid table margin settings {}".format(tableStyleAttrib))

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

    # set default para style in case there are no spans to set it
    pdf_styleN = CreateParagraphStyle(backgroundColor, reportlab.lib.colors.black, bodyfont, bodyfs)
    # pdf_styleN.backColor = reportlab.lib.colors.HexColor("0xFFFF00") # for debuging useful

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
        htmlspans = p.findall(".*")
        if len(htmlspans) < 1: # i.e. there are no spans, just a paragraph
            paragraphText = '<para autoLeading="max">'
            paragraphText, maxfs = AppendItemTextInStyle(paragraphText, p.text, p, pdf,
                additional_fonts, bodyfont, bodyfs, bweight, bstyle, backgroundColorAttrib)
            paragraphText += '</para>'
            usefs = maxfs if maxfs > 0 else bodyfs
            pdf_styleN.leading = usefs * line_scale  # line spacing (text + leading)
            pdf_flowableList.append(Paragraph(paragraphText, pdf_styleN))

        else:
            paragraphText = '<para autoLeading="max">'

            # there might be untagged text preceding a span. We have to add that to paragraphText
            # first - but we must not terminate the paragraph and add it to the flowable because
            # the first span just continues that leading text
            if not p.text is None:
                paragraphText, maxfs = AppendItemTextInStyle(paragraphText, p.text, p, pdf,
                    additional_fonts, bodyfont, bodyfs, bweight, bstyle, backgroundColorAttrib)
                usefs = maxfs if maxfs > 0 else bodyfs
                pdf_styleN.leading = usefs * line_scale  # line spacing (text + leading)

            # now run round the htmlspans
            for item in htmlspans:
                if item.tag == 'br':
                    br = item
                    # terminate the current pdf para and add it to the flow. The nbsp seems unnecessary
                    # but if it is not there then an empty paragraph goes missing :-(
                    paragraphText += '&nbsp;</para>'
                    usefs = maxfs if maxfs > 0 else bodyfs
                    pdf_styleN.leading = usefs * line_scale  # line spacing (text + leading)
                    pdf_flowableList.append(Paragraph(paragraphText, pdf_styleN))
                    # start a new pdf para in the style of the para and add the tail text of this br item
                    paragraphText = '<para autoLeading="max">'
                    paragraphText, maxfs = AppendItemTextInStyle(paragraphText, br.tail, p, pdf,
                        additional_fonts, bodyfont, bodyfs, bweight, bstyle, backgroundColorAttrib)

                elif item.tag == 'span':
                    span = item
                    spanfont, spanfs, spanweight, spanstyle = CollectFontInfo(span, pdf, additional_fonts, bodyfont, bodyfs, bweight)

                    if spanfs > maxfs:
                        maxfs = spanfs

                    paragraphText = AppendSpanStart(paragraphText, backgroundColorAttrib, spanfont, spanfs, spanweight, spanstyle, bstyle)

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
                            pdf_styleN.leading = usefs * line_scale  # line spacing (text + leading)
                            pdf_flowableList.append(Paragraph(paragraphText, pdf_styleN))
                            # start a new pdf para in the style of the current span
                            paragraphText = '<para autoLeading="max">'
                            # now add the tail text of each br in the span style
                            paragraphText, maxfs = AppendItemTextInStyle(paragraphText, br.tail, span, pdf,
                                additional_fonts, bodyfont, bodyfs, bweight, bstyle, backgroundColorAttrib)
                    else:
                        paragraphText = AppendSpanEnd(paragraphText, spanweight, spanstyle, bstyle)

                    if span.tail is not None:
                        paragraphText = AppendText(paragraphText, html.escape(span.tail))

                else:
                    logging.warning("Ignoring unhandled tag {}".format(item.tag))

            # try to create a paragraph with the current text and style. Catch errors.
            try:
                paragraphText += '</para>'
                usefs = maxfs if maxfs > 0 else bodyfs
                pdf_styleN.leading = usefs * line_scale  # line spacing (text + leading)
                pdf_flowableList.append(Paragraph(paragraphText, pdf_styleN))
            except Exception as ex:
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
    for j in range(len(pdf_flowableList)):
        neededTextWidth, neededTextHeight = pdf_flowableList[j].wrap(availableTextWidth, availableTextHeight)
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
        logging.warning(' Most recent paragraph text: {}'.format(paragraphText))
        frameHeight = finalTotalHeight
    if finalTotalWidth > frameWidth:
        frameWidth = finalTotalWidth

    newFrame = Frame(frameBottomLeft_x, frameBottomLeft_y,
        frameWidth, frameHeight,
        leftPadding=leftPad, bottomPadding=bottomPad,
        rightPadding=rightPad, topPadding=topPad,
        showBoundary=0  # for debugging useful to set 1
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


def loadClipart(fileName) -> ClpFile:
    """Tries to load a clipart file. Either from .CLP or .SVG file
    returns a clpFile object"""
    newClpFile = ClpFile("")

    if os.path.isabs(fileName):
        filePath = Path(fileName)
        if not filePath.exists():
            filePath = filePath.parent.joinpath(filePath.stem+".clp")
            if not filePath.exists():
                logging.error("Missing .clp: {}".format(fileName))
                return ClpFile("")   # return an empty ClpFile
    else:
        pathObj = Path(fileName)
        # the name can actually be "correct", but its stem may not be in the clipartPathList. This will 
        # happen at least for passepartout clip masks when we're using a local test hps structure rather 
        # than an installed cewe_folder. For that reason we add the file's own folder to the clipartPathList
        # before searching for a clp or svg file matching the stem
        baseFileName = pathObj.stem
        fileFolder = pathObj.parent
        try:
            filePath = findFileInDirs([baseFileName+'.clp', baseFileName+'.svg'], (fileFolder,) + clipartPathList)
            filePath = Path(filePath)
        except Exception as ex:
            logging.error(" {}, {}".format(baseFileName, ex))
            return ClpFile("")   # return an empty ClpFile

    if filePath.suffix == '.clp':
        newClpFile.readClp(filePath)
    else:
        newClpFile.loadFromSVG(filePath)

    return newClpFile


def processAreaClipartTag(clipartElement, areaHeight, areaRot, areaWidth, pdf, transx, transy, alpha):
    clipartID = int(clipartElement.get('designElementId'))
    # print("Warning: clip-art elements are not supported. (designElementId = {})".format(clipartID))

    # designElementId 0 seems to be a special empty placeholder
    if clipartID == 0:
        return

    # Load the clipart
    fileName = None
    if clipartID in clipartDict:
        fileName = clipartDict[clipartID]
    # verify preconditions to avoid exception loading the clip art file, which would break the page count
    if not fileName:
        logging.error("Problem getting file name for clipart ID: {}".format(clipartID))
        return

    colorreplacements = []
    for clipconfig in clipartElement.findall('ClipartConfiguration'):
        for clipcolors in clipconfig.findall('colors'):
            for clipcolor in clipcolors.findall('color'):
                source = '#'+clipcolor.get('source').upper()[1:7]
                target = '#'+clipcolor.get('target').upper()[1:7]
                replacement = (source, target)
                colorreplacements.append(replacement)

    insertClipartFile(fileName, colorreplacements, transx, areaWidth, areaHeight, alpha, pdf, transy, areaRot)


def insertClipartFile(fileName:str, colorreplacements, transx, areaWidth, areaHeight, alpha, pdf, transy, areaRot):
    img_transx = transx

    res = image_res # use the foreground resolution setting for clipart

    # 254 -> convert from mcf unit (0.1mm) to inch (1 inch = 25.4 mm)
    new_w = int(0.5 + areaWidth * res / 254.)
    new_h = int(0.5 + areaHeight * res / 254.)

    clipart = loadClipart(fileName)
    if len(clipart.svgData) <= 0:
        logging.error("Clipart file could not be loaded: {}".format(fileName))
        # avoiding exception in the processing below here
        return

    if len(colorreplacements) > 0:
        clipart.replaceColors(colorreplacements)

    clipart.convertToPngInBuffer(new_w, new_h, alpha)  # so we can access the pngMemFile later

    # place image
    logging.debug("Clipart file: {}".format(fileName))
    pdf.translate(img_transx, transy)
    pdf.rotate(-areaRot)
    pdf.drawImage(ImageReader(clipart.pngMemFile),
        f * -0.5 * areaWidth, f * -0.5 * areaHeight,
        width=f * areaWidth, height=f * areaHeight, mask='auto')
    pdf.rotate(areaRot)
    pdf.translate(-img_transx, -transy)


def processElements(additional_fonts, fotobook, imagedir, keepDoublePages, mcfBaseFolder, oddpage, page, pageNumber, pagetype, pdf, ph, pw):
    if keepDoublePages and oddpage == 1 and pagetype == 'normal':
        # if we are in double-page mode, all the images are already drawn by the even pages.
        return

    # switch pack to the page element for the even page to get the elements
    if pagetype == 'normal' and oddpage == 1:
        page = getPageElementForPageNumber(fotobook, 2*floor(pageNumber/2))

    for area in page.findall('area'):
        areaPos = area.find('position')
        areaLeft = float(areaPos.get('left').replace(',', '.'))
        # old python 2 code: aleft = float(area.get('left').replace(',', '.'))
        if pagetype != 'singleside' or len(area.findall('imagebackground')) == 0:
            if oddpage and not keepDoublePages:
                # shift double-page content from other page
                areaLeft -= pw
        areaTop = float(areaPos.get('top').replace(',', '.'))
        areaWidth = float(areaPos.get('width').replace(',', '.'))
        areaHeight = float(areaPos.get('height').replace(',', '.'))
        areaRot = float(areaPos.get('rotation'))

        # check if the image is on current page at all
        if pagetype == 'normal' and not keepDoublePages:
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
            processAreaImageTag(imageTag, area, areaHeight, areaRot, areaWidth, imagedir, keepDoublePages, mcfBaseFolder, pagetype, pdf, pw, transx, transy)

        # process text
        for textTag in area.findall('text'):
            processAreaTextTag(textTag, additional_fonts, area, areaHeight, areaRot, areaWidth, pdf, transx, transy)

        # Clip-Art
        # In the clipartarea there are two similar elements, the <designElementIDs> and the <clipart>.
        # We are using the <clipart> element here
        if area.get('areatype') == 'clipartarea': # only look for alpha and clipart within clipartarea tags
            alpha = 255
            decoration = area.find('decoration') # decoration tag
            if decoration is not None:
                alphatext = decoration.get('alpha') # alpha attribute
                if alphatext is not None:
                    alpha = int((float(alphatext)) * 255)
            for clipartElement in area.findall('clipart'):
                processAreaClipartTag(clipartElement, areaHeight, areaRot, areaWidth, pdf, transx, transy, alpha)
    return


def parseInputPage(fotobook, cewe_folder, mcfBaseFolder, backgroundLocations, imagedir, pdf,
        page, pageNumber, pageCount, pagetype, keepDoublePages, oddpage,
        bg_notFoundDirList, additional_fonts):
    logging.info('parsing page {}  of {}'.format(page.get('pagenr'), pageCount))

    bundlesize = page.find("./bundlesize")
    if bundlesize is not None:
        pw = float(bundlesize.get('width'))
        ph = float(bundlesize.get('height'))

        # reduce the page width to a single page width,
        # if we want to have single pages.
        if not keepDoublePages:
            pw = pw / 2
    else:
        # Assume A4 page size
        pw = 2100
        ph = 2970
    pdf.setPageSize((f * pw, f * ph))

    # process background
    # look for all "<background...> tags.
    # the preceeding designElementIDs tag only match the same
    #  number for the background attribute if it is a original
    #  stock image, without filters.
    backgroundTags = page.findall('background')
    processBackground(backgroundTags, bg_notFoundDirList, cewe_folder, backgroundLocations, keepDoublePages, oddpage, pagetype, pdf, ph, pw)

    # all elements (images, text,..) for even and odd pages are defined on the even page element!
    processElements(additional_fonts, fotobook, imagedir, keepDoublePages, mcfBaseFolder, oddpage, page, pageNumber, pagetype, pdf, ph, pw)

def getBaseClipartLocations(baseFolder):
    # create a tuple of places (folders) where background resources would be found by default
    baseClipartLocations = (
        os.path.join(baseFolder, 'Resources', 'photofun', 'decorations'),   # trailing comma is important to make a 1-element tuple
        # os.path.join(baseFolder, 'Resources', 'photofun', 'decorations', 'form_frames'),
        # os.path.join(baseFolder, 'Resources', 'photofun', 'decorations', 'frame_frames')
    )
    return baseClipartLocations

def readClipArtConfigXML(baseFolder, keyaccountFolder):
    """Parse the configuration XML file and generate a dictionary of designElementId to fileName
    currently only cliparts_default.xml is supported !"""
    global clipartPathList  # pylint: disable=global-statement
    clipartPathList = getBaseClipartLocations(baseFolder) # append instead of overwrite global variable
    xmlConfigFileName = 'cliparts_default.xml'
    try:
        xmlFileName = findFileInDirs(xmlConfigFileName, clipartPathList)
        loadClipartConfigXML(xmlFileName)
    except: # noqa: E722
        configlogger.error('Could not load clipart definition file: {}'.format(xmlConfigFileName))
        configlogger.error('Cliparts will not be available.')
        return

    if keyaccountFolder is None:
        # In "production" this is definitely an error, although for unit tests (in particular when
        # run on the checkin build where CEWE is not installed and there is definitely no downloaded 
        # stuff from the installation) it isn't really an error because there is a local folder
        # tests/Resources/photofun/decorations with the clipart files needed for the tests.
        configlogger.error("No downloaded clipart folder found")
        return

    addonclipartxmls = os.path.join(keyaccountFolder, "addons", "*", "cliparts", "v1", "decorations", "*.xml");
    for file in glob.glob(addonclipartxmls):
        loadClipartConfigXML(file)

def loadClipartConfigXML(xmlFileName):
    clipArtXml = open(xmlFileName, 'rb')
    xmlInfo = etree.parse(xmlFileName)
    clipArtXml.close()

    for decoration in xmlInfo.findall('decoration'):
        clipartElement = decoration.find('clipart')
        fileName = os.path.join(os.path.dirname(xmlFileName), clipartElement.get('file'))
        designElementId = int(clipartElement.get('designElementId'))    # assume these IDs are always integers.
        clipartDict[designElementId] = fileName
    return

def getBaseBackgroundLocations(basefolder, keyaccountFolder):
    # create a tuple of places (folders) where background resources would be found by default
    baseBackgroundLocations = (
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds'),
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'einfarbige'),
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'multicolor'),
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'spotcolor'),
    )
    if keyaccountFolder is not None:
        baseBackgroundLocations = baseBackgroundLocations + \
            tuple(glob.glob(os.path.join(keyaccountFolder, "addons", "*", "backgrounds", "v1", "backgrounds"))) + \
            tuple(glob.glob(os.path.join(keyaccountFolder, "addons", "*", "backgrounds", "v1")))

    return baseBackgroundLocations


def SetEnvironmentVariables(cewe_folder, keyAccountNumber):
    # put values into the environment so that it can be substituted in later
    # config elements in the ini file, eg as ${CEWE_FOLDER} 
    os.environ['CEWE_FOLDER'] = cewe_folder
    os.environ['KEYACCOUNT'] = keyAccountNumber


def getOutputFileName(mcfname):
    return mcfname + '.pdf'


def checkCeweFolder(cewe_folder):
    if os.path.exists(cewe_folder):
        logging.info("cewe_folder is {}".format(cewe_folder))
    else:
        logging.error("cewe_folder {} not found. This must be a test run which doesn't need it!".format(cewe_folder))

def convertMcf(mcfname, keepDoublePages: bool, pageNumbers=None):
    global clipartPathList  # pylint: disable=global-statement
    global fontSubstitutions  # pylint: disable=global-statement
    global passepartoutDict  # pylint: disable=global-statement
    global passepartoutFolders  # pylint: disable=global-statement

    clipartDict = dict()    # a dictionary for clipart element IDs to file name
    clipartPathList = tuple()
    passepartoutDict = None    # a dictionary for passepartout  desginElementIDs to file name
    passepartoutFolders = tuple() # global variable with the folders for passepartout frames
    fontSubstitutions = list() # used to avoid repeated messages

    # Get the folder in which the .mcf file is
    mcfPathObj = Path(mcfname).resolve()    # convert it to an absolute path
    mcfBaseFolder = str(mcfPathObj.parent)

    # parse the input mcf xml file
    # read file as binary, so UTF-8 encoding is preserved for xml-parser
    mcffile = open(mcfname, 'rb')
    mcf = etree.parse(mcffile)
    mcffile.close()
    fotobook = mcf.getroot()
    if fotobook.tag != 'fotobook':
        logging.error(mcfname + ' is not a valid mcf file. Exiting.')
        sys.exit(1)

	# check output file is acceptable before we do any processing
    outputFileName = getOutputFileName(mcfname)
    if os.path.exists(outputFileName):
        if os.path.isfile(outputFileName):
            if not os.access(outputFileName, os.W_OK):
                logging.error("Existing output file '%s' is not writable" % (outputFileName))
                sys.exit(1)
        else:
            logging.error("Existing output '%s' is not a file" % (outputFileName))
            sys.exit(1)

    # a null default configuration section means that some capabilities will be missing!
    defaultConfigSection = None
    # find cewe folder using the original cewe_folder.txt file
    try:
        configFolderFileName = findFileInDirs('cewe_folder.txt', (mcfBaseFolder, os.path.curdir))
        cewe_file = open(configFolderFileName, 'r')
        cewe_folder = cewe_file.read().strip()
        cewe_file.close()
        checkCeweFolder(cewe_folder)
        keyAccountNumber = getKeyaccountNumber(cewe_folder)
        keyaccountFolder = getKeyaccountDataFolder(cewe_folder, keyAccountNumber)

        backgroundLocations = getBaseBackgroundLocations(cewe_folder, keyaccountFolder)
    except: # noqa: E722
        logging.info('Trying cewe2pdf.ini from current directory and from .mcf directory.')
        configuration = configparser.ConfigParser()
        # Try to read the .ini first from the current directory, and second from the directory where the .mcf file is.
        # Order of the files is important, because config entires are
        #  overwritten when they appear in the later config files.
        # We want the config file in the .mcf directory to be the most important file.
        filesread = configuration.read(['cewe2pdf.ini', os.path.join(mcfBaseFolder, 'cewe2pdf.ini')])
        if len(filesread) < 1:
            logging.warning('Cannot find cewe installation folder cewe_folder from cewe2pdf.ini')
            cewe_folder = None
        else:
            # Give the user feedback which config-file is used, in case there is a problem.
            logging.info('Using configuration in: ' + ', '.join(map('{}'.format, filesread)))
            defaultConfigSection = configuration['DEFAULT']
            # find cewe folder from ini file
            if 'cewe_folder' not in defaultConfigSection:
                logging.error('Error: You must create cewe_folder.txt or modify cewe2pdf.ini')
                sys.exit(1)

            cewe_folder = defaultConfigSection['cewe_folder'].strip()
            checkCeweFolder(cewe_folder)

            keyAccountNumber = getKeyaccountNumber(cewe_folder, defaultConfigSection)

            # set the cewe folder and key account number into the environment for later use in the config files
            SetEnvironmentVariables(cewe_folder, keyAccountNumber)
            
            keyaccountFolder = getKeyaccountDataFolder(cewe_folder, keyAccountNumber, defaultConfigSection)

            baseBackgroundLocations = getBaseBackgroundLocations(cewe_folder, keyaccountFolder)

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

    if keyaccountFolder is not None:
        passepartoutFolders = passepartoutFolders + \
            tuple([os.path.join(keyaccountFolder, "addons")]) + \
            tuple([os.path.join(cewe_folder, "Resources", "photofun", "decorations")])

    bg_notFoundDirList = set([])   # keep a list with background folders that not found, to prevent multiple errors for the same cause.

    # Load additional fonts
    ttfFiles = []
    fontDirs = []
    additional_fonts = {}
    additional_fontFamilies = {}
    if cewe_folder is not None:
        fontDirs.append(os.path.join(cewe_folder, 'Resources', 'photofun', 'fonts'))

    try:
        configFontFileName = findFileInDirs('additional_fonts.txt', (mcfBaseFolder, os.path.curdir))
        logging.info('Using fonts from: ' + configFontFileName)
        with open(configFontFileName, 'r') as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue # ignore empty lines
                if line.startswith("#"):
                    continue # ignore comments
                if line.find(" = ") != -1:
                    # Old "font name = /path/to/file" format
                    p = line.split(" = ", 1)
                    path = os.path.expandvars(p[1])
                else:
                    path = os.path.expandvars(line)

                if not os.path.exists(path):
                    configlogger.error('Custom additional font file does not exist: ' + path)
                    continue
                if os.path.isdir(path):
                    fontDirs.append(path)
                else:
                    ttfFiles.append(path)
            fp.close()
    except ValueError: # noqa: E722
        configlogger.error('cannot find additional fonts (define them in additional_fonts.txt)')
        configlogger.error('Content example:')
        configlogger.error('/tmp/vera.ttf')

    if len(fontDirs) > 0:
        for fontDir in fontDirs:
            ttfFiles.extend(sorted(glob.glob(os.path.join(fontDir, '*.ttf'))))

    if len(ttfFiles) > 0:
        ttfFiles = list(dict.fromkeys(ttfFiles))# remove duplicates
        for ttfFile in ttfFiles:
            font = ttLib.TTFont(ttfFile)
            fontFamily = font['name'].getName(1, 3, 1, 1033)#Arial
            fontSubFamily = font['name'].getName(2, 3, 1, 1033)#Regular, Bold, Bold Italic
            if fontFamily is None:
                configlogger.warning('Could not get family (name) of font: ' + ttfFile)
                continue
            if fontSubFamily is None:
                configlogger.warning('Could not get subfamily of font: ' + ttfFile)
                continue

            fontFamily = fontFamily.toUnicode()
            fontSubFamily = fontSubFamily.toUnicode()

            if fontSubFamily == "Medium" or fontSubFamily == "Regular":
                fontName = fontFamily
            else:
                fontName = fontFamily + " " + fontSubFamily
            additional_fonts[fontName] = ttfFile

            if fontFamily not in additional_fontFamilies:
                additional_fontFamilies[fontFamily] = {
                    "normal": None,
                    "bold": None,
                    "italic": None,
                    "boldItalic": None
                }
            if fontSubFamily == "Medium" or fontSubFamily == "Regular":
                additional_fontFamilies[fontFamily]["normal"] = fontName
            elif fontSubFamily == "Bold":
                additional_fontFamilies[fontFamily]["bold"] = fontName
            elif fontSubFamily == "Italic" or fontSubFamily == "Medium Italic":
                additional_fontFamilies[fontFamily]["italic"] = fontName
            elif fontSubFamily == "Bold Italic":
                additional_fontFamilies[fontFamily]["boldItalic"] = fontName
            else:
                additional_fonts[fontFamily] = ttfFile
                configlogger.warning("Unhandled font subfamily: " + fontName + " " + fontSubFamily)

    # Add additional fonts. We need to loop over the keys, not the list iterator, so we can delete keys from the list in the loop
    logging.info("Registering %s fonts" % len(additional_fonts))
    for curFontName in list(additional_fonts):
        try:
            pdfmetrics.registerFont(TTFont(curFontName, additional_fonts[curFontName]))
            configlogger.info("Registered '%s' from '%s'" % (curFontName, additional_fonts[curFontName]))
        except:# noqa: E722
            configlogger.error("Failed to register font '%s' (from %s)" % (curFontName, additional_fonts[curFontName]))
            del additional_fonts[curFontName]    # remove this item from the font list, so it won't be used later and cause problems.

    # the reportlab manual says:
    #  Before using the TT Fonts in Platypus we should add a mapping from the family name to the individual font
    #  names that describe the behaviour under the <b> and <i> attributes.
    #  from reportlab.pdfbase.pdfmetrics import registerFontFamily
    #  registerFontFamily('Vera',normal='Vera',bold='VeraBd',italic='VeraIt',boldItalic='VeraBI')
    if len(additional_fontFamilies) > 0:
        for familyName, fontfamily in additional_fontFamilies.items():
            for key, value in dict(fontfamily).items():
                if value is None:
                    del fontfamily[key]
            pdfmetrics.registerFontFamily(familyName, **fontfamily)
            configlogger.info("Registered font family '%s'" % (familyName))

    if defaultConfigSection is not None:
        ff = defaultConfigSection.get('FontFamilies', '').splitlines()  # newline separated list of folders
        fontFamilies = filter(lambda bg: (len(bg) != 0), ff)
        for fontfamily in fontFamilies:
            members = fontfamily.split(",")
            if len(members) == 5:
                pdfmetrics.registerFontFamily(
                    members[0],
                    normal=members[1],
                    bold=members[2],
                    italic=members[3],
                    boldItalic=members[4]
                    )
                configlogger.info("Registered explicit font family '%s'" % (members[0]))
            else:
                configlogger.error('Invalid FontFamily line ignored (!= 5 comma-separated strings): ' + fontfamily)

    logging.info("Ended font registration")

    # extract properties
    articleConfigElement = fotobook.find('articleConfig')
    if articleConfigElement is None:
        logging.error(mcfname + ' is an old version. Open it in the album editor and save before retrying the pdf conversion. Exiting.')
        sys.exit(1)
    pageCount = int(articleConfigElement.get('normalpages')) + 2    # maximum number of pages
    imagedir = fotobook.get('imagedir')

    # generate a list of available clip-arts
    readClipArtConfigXML(cewe_folder, keyaccountFolder)

    # create pdf
    pagesize = reportlab.lib.pagesizes.A4
    if fotobook.get('productname') in formats:
        pagesize = formats[fotobook.get('productname')]
    pdf = canvas.Canvas(outputFileName, pagesize=pagesize)

    for n in range(pageCount):
        try:
            if (n == 0) or (n == pageCount - 1):
                pageNumber = 0
                page = [i for i in
                        fotobook.findall("./page[@pagenr='0'][@type='FULLCOVER']")
                        + fotobook.findall("./page[@pagenr='0'][@type='fullcover']")
                        if (i.find("./area") is not None)
                        ][0]
                oddpage = (n == 0)
                pagetype = 'cover'
                # for double-page-layout: the last page is already the left side of the book cover. So skip rendering the last page
                if ((keepDoublePages is True) and (n == (pageCount - 1))):
                    page = None
            elif n == 1:
                pageNumber = 1
                oddpage = True
                # Look for an empty page 0 that still contains an area element
                page = [i for i in
                        fotobook.findall("./page[@pagenr='0'][@type='EMPTY']")
                        + fotobook.findall("./page[@pagenr='0'][@type='emptypage']")
                        if i.find("./area") is not None]
                if len(page) >= 1:
                    page = page[0]
                    # If there is on page 1 only text, the area-tag is still on page 0.
                    #  So this will either include the text (which is put in page 0),
                    #  or the packground which is put in page 1.
                else:
                    page = None # if we find no empty page with an area tag, we need to set this to None to prevent an exception later.

                # Look for the the first page and set it up for processing
                realFirstPageList = fotobook.findall("./page[@pagenr='1'][@type='normalpage']")
                if len(realFirstPageList) > 0 and (pageNumbers is None or 0 in pageNumbers):
                    # we need to do run parseInputPage twico for one output page in the PDF.
                    # The background needs to be drawn first, or it would obscure any other other elements.
                    pagetype = 'singleside'
                    parseInputPage(fotobook, cewe_folder, mcfBaseFolder, backgroundLocations, imagedir, pdf,
                        realFirstPageList[0], pageNumber, pageCount, pagetype, keepDoublePages, oddpage,
                        bg_notFoundDirList, additional_fonts)
                pagetype = 'emptypage'
            else:
                pageNumber = n
                oddpage = (pageNumber % 2) == 1
                page = getPageElementForPageNumber(fotobook, n)
                pagetype = 'normal'

            if pageNumbers is not None and pageNumber not in pageNumbers:
                continue

            if page is not None:
                parseInputPage(fotobook, cewe_folder, mcfBaseFolder, backgroundLocations, imagedir, pdf,
                    page, pageNumber, pageCount, pagetype, keepDoublePages, oddpage,
                    bg_notFoundDirList, additional_fonts)

            # finish the page and start a new one.
            # If "keepDoublePages" was active, we only start a new page, after the odd pages.
            if ((keepDoublePages is False)
                or ((not (keepDoublePages is True and oddpage is True and pagetype == 'normal'))
                    and (not (keepDoublePages is True and n == (pageCount - 1) and pagetype == 'cover'))
                   )
               ):
                pdf.showPage()

        except Exception as ex:
            # if one page fails: continue with next one
            logging.exception("Exception")
            logging.error('error on page {}: {}'.format(n, ex.args[0]))

    # save final output pdf
    pdf.save()

    pdf = []

    # force the release of objects which might be holding on to picture file references
    # so that they will not prevent the removal of the files as we clean up and exit
    import gc
    objectscollected = gc.collect()
    logging.info('GC collected objects : {}'.format(objectscollected))

    # clean up temp files
    for tmpFileName in tempFileList:
        if os.path.exists(tmpFileName):
            os.remove(tmpFileName)
    return True


def getHpsDataFolder():
    # linux + macosx
    dotMcfFolder = os.path.expanduser("~/.mcf/hps/")
    if os.path.exists(dotMcfFolder):
        return dotMcfFolder

    # windows
    # from some time around september 2022 (07.02.05) the key account folder seems to have been moved
    # (or perhaps added to on a per user basis?) from ${PROGRAMDATA}/hps/ to ${LOCALAPPDATA}/CEWE/hps/
    winHpsFolder = os.path.expandvars("${LOCALAPPDATA}/CEWE/hps/")
    if os.path.exists(winHpsFolder):
        return winHpsFolder
    # check for the older location
    winHpsFolder = os.path.expandvars("${PROGRAMDATA}/hps/")
    if os.path.exists(winHpsFolder):
        logging.info('hps data folder found at old location {}'.format(winHpsFolder))
        return winHpsFolder

    return None


def getKeyaccountDataFolder(cewe_folder, keyAccountNumber, defaultConfigSection = None):
    # for testing (in particular on checkin on github where no cewe product is installed)
    # we may want to have a specially constructed local key account data folder
    if defaultConfigSection is not None:
        inihps = defaultConfigSection.get('hpsFolder')
        if inihps is not None:
            inikadf = os.path.join(inihps, keyAccountNumber)
            if os.path.exists(inikadf):
                logging.info('ini file overrides hps folder, key account folder set to {}'.format(inikadf))
                return inikadf.strip()
            else:
                logging.error('ini file overrides hps folder, but key account folder {} does not exist. Using defaults'.format(inikadf))
    
    hpsFolder = getHpsDataFolder()
    if hpsFolder is None:
        logging.warning('No installed hps data folder found')
        return None

    kadf = os.path.join(hpsFolder, keyAccountNumber)
    if os.path.exists(kadf):
        logging.info('Installed key account data folder at {}'.format(kadf))
        return kadf
    else:
        logging.error('Installed key account data folder {} not found'.format(kadf))
        return None


def getKeyAccountFileName(cewe_folder):
    keyAccountFileName = os.path.join(cewe_folder, "Resources", "config", "keyaccount.xml")
    return keyAccountFileName


def getKeyaccountNumber(cewe_folder, defaultConfigSection = None):
    keyAccountFileName = getKeyAccountFileName(cewe_folder)
    try:
        katree = etree.parse(keyAccountFileName)
        karoot = katree.getroot()
        ka = karoot.find('keyAccount').text # that's the official installed value
        # see if he has a .ini file override for the keyaccount
        if defaultConfigSection is not None:
            inika = defaultConfigSection.get('keyaccount')
            if inika is not None:
                logging.info('ini file overrides keyaccount from {} to {}'.format(ka, inika))
                ka = inika
    except Exception as ex:
        ka = "0"
        logging.error('Could not extract keyAccount tag in file: {}, using {}'.format(keyAccountFileName, ka))
    return ka.strip()


if __name__ == '__main__':
    # only executed when this file is run directly.
    # we need trick to have both: default and fixed formats.
    class CustomArgFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass

    parser = argparse.ArgumentParser(description='Convert a photo-book from .mcf file format to .pdf',
                                     epilog="Example:\n   python cewe2pdf.py c:\\path\\to\\my\\files\\my_nice_fotobook.mcf",
                                     formatter_class=CustomArgFormatter)
    parser.add_argument('--keepDoublePages', dest='keepDoublePages', action='store_const',
                        const=True, default=False,
                        help='Each page in the .pdf will be a double-sided page, instead of a normal single page.')
    parser.add_argument('--pages', dest='pages', action='store',
                        default=None,
                        help='Page numbers to render, e.g. 1,2,4-9')
    parser.add_argument('inputFile', type=str, nargs='?',
                        help='the mcf input file. If not given, the first .mcf in the current directory is used.')

    args = parser.parse_args()

    # if no file name was given, search for the first .mcf file in the current directory
    if args.inputFile is None:
        fnames = [i for i in os.listdir('.') if i.endswith('.mcf')]
        if len(fnames) > 0:
            args.inputFile = fnames[0]

    # if inputFile name is still empty, we have to throw an error
    if args.inputFile is None:
        parser.parse_args(['-h'])
        sys.exit(1)

    pageNumbers = None
    if args.pages is not None:
        pageNumbers = []
        for expr in args.pages.split(','):
            expr = expr.strip()
            if expr.isnumeric():
                pageNumbers.append(int(expr)) # simple number "23"
            elif expr.find('-') > -1:
                # page range: 23-42
                fromTo = expr.split('-', 2)
                if not fromTo[0].isnumeric() or not fromTo[1].isnumeric():
                    logging.error('Invalid page range: ' + expr)
                    sys.exit(1)
                pageFrom = int(fromTo[0])
                pageTo = int(fromTo[1])
                if pageTo < pageFrom:
                    logging.error('Invalid page range: ' + expr)
                    sys.exit(1)
                pageNumbers = pageNumbers + list(range(pageFrom, pageTo + 1))
            else:
                logging.error('Invalid page number: ' + expr)
                sys.exit(1)

    # if we have a file name, let's convert it
    resultFlag = convertMcf(args.inputFile, args.keepDoublePages, pageNumbers)
