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
import glob
import fnmatch

import logging
import logging.config

import os.path
import os
import re
import tempfile
import html

import gc

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

# import pil and work around a breaking change in pil 10.0.0, see
#   https://stackoverflow.com/questions/76616042/attributeerror-module-pil-image-has-no-attribute-antialias
import PIL

from packaging.version import parse as parse_version
from lxml import etree
import yaml

from clpFile import ClpFile  # for clipart .CLP and .SVG files
from mcfx import unpackMcfx
from messageCounterHandler import MsgCounterHandler
from passepartout import Passepartout
from pathutils import localfont_dir
from otf import getTtfsFromOtfs

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

if os.path.exists('loggerconfig.yaml'):
    with open('loggerconfig.yaml', 'r') as loggeryaml: # this works on all relevant platforms so pylint: disable=unspecified-encoding
        config = yaml.safe_load(loggeryaml.read())
        logging.config.dictConfig(config)
else:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

configlogger = logging.getLogger("cewe2pdf.config")

# create log output handlers which count messages at each level
rootMessageCountHandler = MsgCounterHandler()
rootMessageCountHandler.setLevel(logging.DEBUG) # ensuring that it counts everything
logging.getLogger().addHandler(rootMessageCountHandler)

configMessageCountHandler = MsgCounterHandler()
configMessageCountHandler.setLevel(logging.DEBUG) # ensuring that it counts everything
configlogger.addHandler(configMessageCountHandler)

# make it possible for PIL.Image to open .heic files if the album editor stores them directly
# ref https://github.com/bash0/cewe2pdf/issues/130
try:
    from pillow_heif import register_heif_opener # the absence of heif handling is handled so pylint: disable=import-error
    register_heif_opener()
except ModuleNotFoundError as heifex:
    logging.warning(f"{heifex.msg}: direct use of .heic images is not available")

# ### settings ####
image_res = 150  # dpi  The resolution of normal images will be reduced to this value, if it is higher.
bg_res = 150  # dpi The resolution of background images will be reduced to this value, if it is higher.
image_quality = 86  # 0=worst, 100=best. This is the JPEG quality option.
# ##########

# .mcf units are 0.1 mm
# Tabs seem to be in 8mm pitch
tab_pitch = 80

# definitions
formats = {"ALB82": reportlab.lib.pagesizes.A4,
           "ALB69": (5400/100/2*reportlab.lib.units.cm, 3560/100*reportlab.lib.units.cm)}  # add other page sizes here
f = 72. / 254.  # convert from mcf (unit=0.1mm) to reportlab (unit=inch/72)

tempFileList = []  # we need to remove all this temporary files at the end

# reportlab defaults
# pdf_styles = getSampleStyleSheet()
# pdf_styleN = pdf_styles['Normal']
pdf_flowableList = []

clipartDict = dict[int, str]()    # a dictionary for clipart element IDs to file name
clipartPathList = tuple[str]()
passepartoutDict = None    # will be dict[int, str] for passepartout designElementIDs to file name
passepartoutFolders = tuple[str]() # global variable with the folders for passepartout frames
fontSubstitutions = list[str]() # used to avoid repeated messages
fontLineScales = {} # mapping fontnames to linescale where the standard value is not ok


def getConfigurationInt(configSection, itemName, defaultValue, minimumValue):
    returnValue = minimumValue
    try:
        # eg getConfigurationInt(defaultConfigSection, 'pdfImageResolution', '150', 100)
        returnValue = int(configSection.get(itemName, defaultValue))
    except ValueError:
        logging.error(f'Invalid configuration value supplied for {itemName}')
        returnValue = int(defaultValue)
    if returnValue < minimumValue:
        logging.error(f'Configuration value supplied for {itemName} is less than {minimumValue}, using {minimumValue}')
        returnValue = minimumValue
    return returnValue


def autorot(im):
    # some cameras return JPEG in MPO container format. Just use the first image.
    if im.format not in ('JPEG', 'MPO'):
        return im
    ExifRotationTag = 274
    exifdict = im.getexif()
    if exifdict is not None and ExifRotationTag in list(exifdict.keys()):
        orientation = exifdict[ExifRotationTag]
        # The PIL.Image values must be dynamic in some way so disable pylint no-member
        if orientation == 2:
            im = im.transpose(PIL.Image.FLIP_LEFT_RIGHT) # pylint: disable=no-member
        elif orientation == 3:
            im = im.transpose(PIL.Image.ROTATE_180) # pylint: disable=no-member
        elif orientation == 4:
            im = im.transpose(PIL.Image.FLIP_TOP_BOTTOM) # pylint: disable=no-member
        elif orientation == 5:
            im = im.transpose(PIL.Image.FLIP_TOP_BOTTOM) # pylint: disable=no-member
            im = im.transpose(PIL.Image.ROTATE_90) # pylint: disable=no-member
        elif orientation == 6:
            im = im.transpose(PIL.Image.ROTATE_270) # pylint: disable=no-member
        elif orientation == 7:
            im = im.transpose(PIL.Image.FLIP_LEFT_RIGHT) # pylint: disable=no-member
            im = im.transpose(PIL.Image.ROTATE_90) # pylint: disable=no-member
        elif orientation == 8:
            im = im.transpose(PIL.Image.ROTATE_90) # pylint: disable=no-member
    return im


def findFileByExtInDirs(filebase, extList, paths):
    for p in paths:
        for ext in extList:
            testPath = os.path.join(p, filebase + ext)
            if os.path.exists(testPath):
                return testPath
    prtStr = f"Could not find {filebase} [{' '.join(extList)}] in paths {', '.join(paths)}"
    logging.info(prtStr)
    raise ValueError(prtStr)


# locate files in a directory with a pattern, with optional case sensitivity
# eg: findFilesInDir(fontdir, '*.ttf')
def findFilesInDir(dirpath: str, glob_pat: str, ignore_case: bool = True):
    if not os.path.exists(dirpath):
        return []
    rule = re.compile(fnmatch.translate(glob_pat), re.IGNORECASE) if ignore_case \
        else re.compile(fnmatch.translate(glob_pat))
    return [os.path.join(dirpath, n) for n in os.listdir(dirpath) if rule.match(n)]


def findFileInDirs(filenames, paths):
    if not isinstance(filenames, list):
        filenames = [filenames]
    for filename in filenames:
        for p in paths:
            testPath = os.path.join(p, filename)
            if os.path.exists(testPath):
                return testPath

    logging.debug(f"Could not find {filenames} in {', '.join(paths)} paths")
    raise ValueError(f"Could not find {filenames} in {', '.join(paths)} paths")


def getPageElementForPageNumber(fotobook, pageNumber):
    return fotobook.find(f"./page[@pagenr='{floor(2 * (pageNumber / 2))}']")


# This is only used for the <background .../> tags. The stock backgrounds use this element.
def processBackground(backgroundTags, bg_notFoundDirList, cewe_folder, backgroundLocations,
                      keepDoublePages, pagetype, pdf, ph, pw):
    if pagetype == "emptypage":  # don't draw background for the empty pages. That is page nr. 1 and pageCount-1.
        return
    if backgroundTags is not None and len(backgroundTags) > 0:
        # look for a tag that has an alignment attribute
        for curTag in backgroundTags:
            if curTag.get('alignment') is not None:
                backgroundTag = curTag
                break

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
                areaWidth = pw
                if keepDoublePages:
                    areaWidth = pw/2.
                areaHeight = ph

                if keepDoublePages and backgroundTag.get('alignment') == "3":
                    ax = areaWidth
                else:
                    ax = 0
                logging.debug(f"Reading background file: {bgPath}")
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
            except Exception:
                if bgPath not in bg_notFoundDirList:
                    logging.error("Could not find background or error when adding to pdf")
                    logging.exception('Exception')
                bg_notFoundDirList.add(bgPath)
    return


def processAreaImageTag(imageTag, area, areaHeight, areaRot, areaWidth, imagedir,
                        keepDoublePages, mcfBaseFolder, pagetype, pdf, pw, transx, transy):
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
            global passepartoutFolders # pylint: disable=global-statement,global-variable-not-assigned
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
        maskClp = loadClipart(maskClipartFileName)
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
        insertClipartFile(frameClipartFileName, [], 0, areaWidth, areaHeight, frameAlpha, pdf, 0, 0, False, False)

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


def lineScaleForFont(font):
    if font in fontLineScales:
        return fontLineScales[font]
    return 1.1


def CreateParagraphStyle(backgroundColor, textcolor, font, fontsize):
    parastyle = ParagraphStyle(None, None,
        alignment=reportlab.lib.enums.TA_LEFT,  # will often be overridden
        fontSize=fontsize,
        fontName=font,
        leading=fontsize*lineScaleForFont(font),  # line spacing (text + leading)
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
        logging.debug(f"Using font family = '{replacement}' (wanted {family})")
        return
    # At other logging levels we simply log the first font substitution
    if not fontSubsNotedAlready:
        logging.warning(f"Using font family = '{replacement}' (wanted {family})")

def CollectFontInfo(item, pdf, additional_fonts, dfltfont, dfltfs, bweight):
    spanfont = dfltfont
    spanfs = dfltfs
    spanweight = bweight
    spanstyle = dict([kv.split(':') for kv in
                    item.get('style').lstrip(' ').rstrip(';').split('; ')])
    if 'font-family' in spanstyle:
        spanfamily = spanstyle['font-family'].strip("'")
        availableFonts = pdf.getAvailableFonts()
        if spanfamily in availableFonts:
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


def AppendSpanStart(paragraphText, font, fsize, fweight, fstyle, outerstyle):
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


def AppendItemTextInStyle(paragraphText, text, item, pdf, additional_fonts, bodyfont, bodyfs, bweight, bstyle):
    pfont, pfs, pweight, pstyle = CollectFontInfo(item, pdf, additional_fonts, bodyfont, bodyfs, bweight)
    paragraphText = AppendSpanStart(paragraphText, pfont, pfs, pweight, pstyle, bstyle)
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
                additional_fonts, bodyfont, bodyfs, bweight, bstyle)
            paragraphText += '</para>'
            usefs = maxfs if maxfs > 0 else bodyfs
            pdf_styleN.leading = usefs * lineScaleForFont(bodyfont)  # line spacing (text + leading)
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
                pdf_styleN.leading = usefs * lineScaleForFont(bodyfont)  # line spacing (text + leading)

            # now run round the htmlspans
            for item in htmlspans:
                if item.tag == 'br':
                    br = item
                    # terminate the current pdf para and add it to the flow. The nbsp seems unnecessary
                    # but if it is not there then an empty paragraph goes missing :-(
                    paragraphText += '&nbsp;</para>'
                    usefs = maxfs if maxfs > 0 else bodyfs
                    pdf_styleN.leading = usefs * lineScaleForFont(bodyfont)  # line spacing (text + leading)
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
                            pdf_styleN.leading = usefs * lineScaleForFont(bodyfont)  # line spacing (text + leading)
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
                pdf_styleN.leading = usefs * lineScaleForFont(bodyfont)  # line spacing (text + leading)
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
    frameWidth = max(frameWidth, finalTotalWidth)

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
                logging.error(f"Missing .clp: {fileName}")
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
            logging.error(f" {baseFileName}, {ex}")
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
        logging.error(f"Problem getting file name for clipart ID: {clipartID}")
        return

    colorreplacements = []
    flipX = False
    flipY = False
    for clipconfig in clipartElement.findall('ClipartConfiguration'):
        for clipcolors in clipconfig.findall('colors'):
            for clipcolor in clipcolors.findall('color'):
                source = '#'+clipcolor.get('source').upper()[1:7]
                target = '#'+clipcolor.get('target').upper()[1:7]
                replacement = (source, target)
                colorreplacements.append(replacement)
        mirror = clipconfig.get('mirror')
        if mirror is not None:
            # cewe developers have a different understanding of x and y :)
            if mirror in ('y', 'both'):
                flipX = True
            if mirror in ('x', 'both'):
                flipY = True

    insertClipartFile(fileName, colorreplacements, transx, areaWidth, areaHeight, alpha, pdf, transy, areaRot, flipX, flipY)


def insertClipartFile(fileName:str, colorreplacements, transx, areaWidth, areaHeight, alpha, pdf, transy, areaRot, flipX, flipY):
    img_transx = transx

    res = image_res # use the foreground resolution setting for clipart

    # 254 -> convert from mcf unit (0.1mm) to inch (1 inch = 25.4 mm)
    new_w = int(0.5 + areaWidth * res / 254.)
    new_h = int(0.5 + areaHeight * res / 254.)

    clipart = loadClipart(fileName)
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
    pdf.rotate(areaRot)
    pdf.translate(-img_transx, -transy)


def processElements(additional_fonts, fotobook, imagedir,
                    keepDoublePages, mcfBaseFolder, oddpage, page, pageNumber, pagetype, pdf, ph, pw, lastpage):
    if keepDoublePages and oddpage == 0 and pagetype == 'normal' and not lastpage:
        # if we are in double-page mode, all the images are drawn by the odd pages.
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
        bg_notFoundDirList, additional_fonts, lastpage):
    logging.info(f"parsing page {page.get('pagenr')}  of {pageCount}")

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
    processBackground(backgroundTags, bg_notFoundDirList, cewe_folder, backgroundLocations, keepDoublePages, pagetype, pdf, ph, pw)

    # all elements (images, text,..) for even and odd pages are defined on the even page element!
    processElements(additional_fonts, fotobook, imagedir, keepDoublePages, mcfBaseFolder, oddpage, page, pageNumber, pagetype, pdf, ph, pw, lastpage)

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
        configlogger.info(f'{xmlFileName} listed {len(clipartDict)} cliparts')
    except: # noqa: E722
        configlogger.info(f'Could not locate and load the clipart definition file: {xmlConfigFileName}')
        configlogger.info('Trying a search for cliparts instead')
        # cliparts_default.xml went missing in 7.3.4 so we have to go looking for all the individual xml
        # files, which still seem to be there and have the same format as cliparts_default.xml, and see
        # if we can build our internal dictionary from them.
        decorations = os.path.join(baseFolder, 'Resources', 'photofun', 'decorations')
        configlogger.info(f'clipart xml path: {decorations}')
        for (root, dirs, files) in os.walk(decorations): # walk returns a 3-tuple so pylint: disable=unused-variable
            for decorationfile in files:
                if decorationfile.endswith(".xml"):
                    loadClipartConfigXML(os.path.join(root, decorationfile))
        numberClipartsLocated = len(clipartDict)
        if numberClipartsLocated > 0:
            configlogger.info(f'{numberClipartsLocated} clipart xmls found')
        else:
            configlogger.error('No clipart xmls found, no delivered cliparts will be available.')

    if keyaccountFolder is None:
        # In "production" this is definitely an error, although for unit tests (in particular when
        # run on the checkin build where CEWE is not installed and there is definitely no downloaded
        # stuff from the installation) it isn't really an error because there is a local folder
        # tests/Resources/photofun/decorations with the clipart files needed for the tests.
        configlogger.error("No downloaded clipart folder found")
        return

    # from (at least) 7.3.4 the addon cliparts might be in more than one structure, so ... first the older layout
    addonclipartxmls = os.path.join(keyaccountFolder, "addons", "*", "cliparts", "v1", "decorations", "*.xml")
    for file in glob.glob(addonclipartxmls):
        loadClipartConfigXML(file)

    # then the newer layout
    currentClipartCount = len(clipartDict)
    localDecorations = os.path.join(keyaccountFolder, 'photofun', 'decorations')
    xmlfiles = glob.glob(os.path.join(localDecorations, "*", "*", "*.xml"))
    configlogger.info(f'local clipart xml path: {localDecorations}')
    for xmlfile in xmlfiles:
        loadClipartConfigXML(xmlfile)
    numberClipartsLocated = len(clipartDict) - currentClipartCount
    if numberClipartsLocated > 0:
        configlogger.info(f'{numberClipartsLocated} local clipart xmls found')

    if len(clipartDict) == 0:
        configlogger.error('No cliparts found')


def loadClipartConfigXML(xmlFileName):
    try:
        with open(xmlFileName, 'rb') as clipArtXml:
            xmlInfo = etree.parse(clipArtXml)
        for decoration in xmlInfo.findall('decoration'):
            clipartElement = decoration.find('clipart')
            # we might be reading a decoration definition that is not clipart, just ignore those
            if clipartElement is None:
                continue
            fileName = os.path.join(os.path.dirname(xmlFileName), clipartElement.get('file'))
            designElementId = int(clipartElement.get('designElementId'))    # assume these IDs are always integers.
            clipartDict[designElementId] = fileName
    except Exception as clpOpenEx:
        logging.error(f"Cannot open clipart file {xmlFileName}: {repr(clpOpenEx)}")


def getBaseBackgroundLocations(basefolder, keyaccountFolder):
    # create a tuple of places (folders) where background resources would be found by default
    baseBackgroundLocations = (
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds'),
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'einfarbige'),
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'multicolor'),
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'spotcolor'),
    )

    # at some point the base cewe organisation of the backgrounds has been changed
    baseBackgroundLocations = baseBackgroundLocations + \
        tuple(glob.glob(os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', "*", "*/")))

    # and then the key account may have added some more backgrounds ...
    if keyaccountFolder is not None:
        baseBackgroundLocations = baseBackgroundLocations + \
            tuple(glob.glob(os.path.join(keyaccountFolder, "addons", "*", "backgrounds", "v1", "backgrounds/"))) + \
            tuple(glob.glob(os.path.join(keyaccountFolder, "addons", "*", "backgrounds", "v1/"))) + \
            tuple(glob.glob(os.path.join(keyaccountFolder, "photofun", "backgrounds", "*", "*/"))) # from 7.3.4 onwards, I think

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
        logging.info(f"cewe_folder is {cewe_folder}")
    else:
        logging.error(f"cewe_folder {cewe_folder} not found. This must be a test run which doesn't need it!")


def convertMcf(albumname, keepDoublePages: bool, pageNumbers=None, mcfxTmpDir=None, appDataDir=None): # noqa: C901 (too complex)
    global clipartDict  # pylint: disable=global-statement
    global clipartPathList  # pylint: disable=global-statement
    global fontSubstitutions  # pylint: disable=global-statement
    global passepartoutDict  # pylint: disable=global-statement
    global passepartoutFolders  # pylint: disable=global-statement
    global fontLineScales  # pylint: disable=global-statement
    global image_res  # pylint: disable=global-statement
    global bg_res  # pylint: disable=global-statement

    clipartDict = {}    # a dictionary for clipart element IDs to file name
    clipartPathList = tuple()
    fontSubstitutions = [] # used to avoid repeated messages
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

    # data.mcf generated by CEWE software has been found to contain extra
    # content after b'<fotobook>...</fotobook>', either of or both: (i) a
    # remnant terminating xml fragment after a shrunk data.mcf, (ii) a sequence
    # of repeated 0xfb's. Cutting after the first occurrence of b'</fotobook>'
    # therefore fixes both potential problems. In such a situation, looking into
    # the .mcfx file (by sqlite3) shows that data.mcf much larger than
    # data.mcf~, and data.mcf contains almost all of the .mcfx file but not the
    # entire file. Setting the environment variable RETAIN_RAW_DATA_MCF will
    # help debugging by retaining the extracted .mcf file.
    try:
        rawdatafile = os.environ["RETAIN_RAW_DATA_MCF"]
        with open(mcfxmlname, 'rb') as mcfin:
            with open(rawdatafile, 'wb') as mcfout:
                mcfout.write(mcfin.read())
                logging.info(f"Raw content of " + str(mcfxmlname) + " saved to " + rawdatafile)
    except KeyError as error:
        pass

    with open(mcfxmlname, 'rb') as mcfin:
        s = mcfin.read()
        p = s.find(b'</fotobook>')
        if p == -1:
            logging.error(f"malformed data.mcf")
            sys.exit(1)
    with open(mcfxmlname, 'wb') as mcfout:
        logging.info(f"rewriting " + str(mcfxmlname))
        mcfout.write(s[:p+11])
        logging.info(f"removed extra content from data.mcf (reduced from " + str(len(s)) + " to " + str(p+11) + " bytes)")

    # parse the input mcf xml file
    # read file as binary, so UTF-8 encoding is preserved for xml-parser
    try:
        with open(mcfxmlname, 'rb') as mcffile:
            mcf = etree.parse(mcffile)
    except Exception as e:
        invalidmsg = f"Cannot open mcf file {mcfxmlname}"
        if mcfxFormat:
            invalidmsg = invalidmsg + f" (unpacked from {albumname})"
        logging.error(invalidmsg + f": {repr(e)}")
        sys.exit(1)

    fotobook = mcf.getroot()
    if fotobook.tag != 'fotobook':
        invalidmsg = f"Cannot process invalid mcf file (root tag is not 'fotobook'): {mcfxmlname}"
        if mcfxFormat:
            invalidmsg = invalidmsg + f" (unpacked from {albumname})"
        logging.error(invalidmsg)
        sys.exit(1)

    # check output file is acceptable before we do any processing
    outputFileName = getOutputFileName(albumname)
    if os.path.exists(outputFileName):
        if os.path.isfile(outputFileName):
            if not os.access(outputFileName, os.W_OK):
                logging.error(f"Existing output file '{outputFileName}' is not writable")
                sys.exit(1)
        else:
            logging.error(f"Existing output '{outputFileName}' is not a file")
            sys.exit(1)

    # a null default configuration section means that some capabilities will be missing!
    defaultConfigSection = None
    # find cewe folder using the original cewe_folder.txt file
    try:
        configFolderFileName = findFileInDirs('cewe_folder.txt', (albumBaseFolder, os.path.curdir, os.path.dirname(os.path.realpath(__file__))))
        with open(configFolderFileName, 'r') as cewe_file:  # this works on all relevant platforms so pylint: disable=unspecified-encoding
            cewe_folder = cewe_file.read().strip()
            checkCeweFolder(cewe_folder)
            keyAccountNumber = getKeyaccountNumber(cewe_folder)
            keyaccountFolder = getKeyaccountDataFolder(keyAccountNumber)
            backgroundLocations = getBaseBackgroundLocations(cewe_folder, keyaccountFolder)

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
            logging.info(f'Using configuration in: {str(filesread)}')
            defaultConfigSection = configuration['DEFAULT']
            # find cewe folder from ini file
            if 'cewe_folder' not in defaultConfigSection:
                logging.error('You must create cewe_folder.txt or modify cewe2pdf.ini')
                sys.exit(1)

            cewe_folder = defaultConfigSection['cewe_folder'].strip()
            checkCeweFolder(cewe_folder)

            keyAccountNumber = getKeyaccountNumber(cewe_folder, defaultConfigSection)

            # set the cewe folder and key account number into the environment for later use in the config files
            SetEnvironmentVariables(cewe_folder, keyAccountNumber)

            keyaccountFolder = getKeyaccountDataFolder(keyAccountNumber, defaultConfigSection)

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

            # read resolution options
            image_res = getConfigurationInt(defaultConfigSection, 'pdfImageResolution', '150', 100)
            bg_res = getConfigurationInt(defaultConfigSection, 'pdfBackgroundResolution', '150', 100)

    logging.info(f'Using image resolution {image_res}, background resolution {bg_res}')

    if keyaccountFolder is not None:
        passepartoutFolders = passepartoutFolders + \
            tuple([os.path.join(keyaccountFolder, "addons")]) + \
            tuple([os.path.join(keyaccountFolder, "photofun", "decorations")]) + \
            tuple([os.path.join(cewe_folder, "Resources", "photofun", "decorations")])

    bg_notFoundDirList = set([])   # keep a list with background folders that not found, to prevent multiple errors for the same cause.

    # Load additional fonts
    ttfFiles = []
    fontDirs = []
    fontLineScales = {}
    additional_fonts = {}
    additional_fontFamilies = {}

    if cewe_folder:
        fontDirs.append(os.path.join(cewe_folder, 'Resources', 'photofun', 'fonts'))

    # if a user has installed fonts locally on his machine, then we need to look there as well
    localFontFolder = localfont_dir()
    if os.path.exists(localFontFolder):
        fontDirs.append(localFontFolder)

    try:
        configFontFileName = findFileInDirs('additional_fonts.txt', (albumBaseFolder, os.path.curdir, os.path.dirname(os.path.realpath(__file__))))
        logging.info(f'Using fonts from: {configFontFileName}')
        with open(configFontFileName, 'r') as fp: # this works on all relevant platforms so pylint: disable=unspecified-encoding
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
                    configlogger.error(f'Custom additional font file does not exist: {path}')
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
            # this is what we really want to do to find extra ttf files:
            #   ttfextras = glob.glob(os.path.join(fontDir, '*.ttf'))
            # but case sensitivity is a problem which will kick in - at least - when executing
            # a Linux subsystem on a Windows machine and file system. So we use a case insensitive
            # alternative [until Python 3.12 when glob itself offers case insensitivity] Ref the
            # discussion at https://stackoverflow.com/questions/8151300/ignore-case-in-glob-on-linux
            ttfextras = findFilesInDir(fontDir, '*.ttf')
            ttfFiles.extend(sorted(ttfextras))

            # CEWE deliver some fonts as otf, which we cannot use witout first converting to ttf
            #   see https://github.com/bash0/cewe2pdf/issues/133
            otfFiles = findFilesInDir(fontDir, '*.otf')
            if len(otfFiles) > 0:
                ttfsFromOtfs = getTtfsFromOtfs(otfFiles,appDataDir)
                ttfFiles.extend(sorted(ttfsFromOtfs))

    if len(ttfFiles) > 0:
        ttfFiles = list(dict.fromkeys(ttfFiles))# remove duplicates
        for ttfFile in ttfFiles:
            font = ttLib.TTFont(ttfFile)

            # See https://learn.microsoft.com/en-us/typography/opentype/spec/name#name-ids
            # The dp4 fontviewer shows the contents of ttf files https://us.fontviewer.de/
            fontFamily = font['name'].getDebugName(1) # eg Arial
            fontSubFamily = font['name'].getDebugName(2) # eg Regular, Bold, Bold Italic
            fontFullName = font['name'].getDebugName(4) # eg usually a combo of 1 and 2
            if fontFamily is None:
                configlogger.warning(f'Could not get family (name) of font: {ttfFile}')
                continue
            if fontSubFamily is None:
                configlogger.warning(f'Could not get subfamily of font: {ttfFile}')
                continue
            if fontFullName is None:
                configlogger.warning(f'Could not get full font name: {ttfFile}')
                continue

            # Cewe offers the users "fonts" which really name a "font family" (so that you can then use
            # the B or I buttons to get bold or italic.)  The mcf file contains those (family) names.
            # So we're going to register (with pdfmetrics):
            #   (1) a lookup between the cewe font (family) name and up to four fontNames (for R,B,I,BI)
            #   (2) a lookup between these four fontNames and the ttf file implementing the font
            # Observe that these fontNames are used only internally in this code, to create the one-to-four
            #  connection between the cewe font (family) name and the ttf files. The names used to be created
            #  in code, but now we just use the official full font name
            # EXCEPT that there's a special case ... the three FranklinGothic ttf files from CEWE are badly defined
            #  because the fontFullName is identical for all three of them, namely FranklinGothic, rather than
            #  including the subfamily names which are Regular, Medium, Medium Italic
            if (fontFullName == fontFamily) and fontSubFamily not in ('Regular', 'Light', 'Roman'):
                # We have a non-"normal" subfamily where the full font name which is not different from the family name.
                # That may be a slightly dubious font definition, and it seems to cause us trouble. First, warn about it,
                # in case people have actually used these rather "special" fonts:
                configlogger.warning(f"fontFullName == fontFamily '{fontFullName}' for a non-regular subfamily '{fontSubFamily}'. A bit strange!")
                # Some of the special cases really are special and probably OK, but CEWE FranklinGothic
                # is a case in point where I think the definition is just wrong, and we can successfully
                # fix it, in combination with a manual FontFamilies defintion in the .ini file:
                if fontFamily == "FranklinGothic":
                    fontFullName = fontFamily + " " + fontSubFamily
                    configlogger.warning(f"  constructed fontFullName '{fontFullName}' for '{fontFamily}' '{fontSubFamily}'")

            if fontSubFamily == "Regular" and fontFullName == fontFamily + " Regular":
                configlogger.warning(f"Revised regular fontFullName '{fontFullName}' to '{fontFamily}'")
                fontFullName = fontFamily

            additional_fonts[fontFullName] = ttfFile

            # first time we see a family we create an empty entry from that family to the R,B,I,BI font names
            if fontFamily not in additional_fontFamilies:
                additional_fontFamilies[fontFamily] = {
                    "normal": None,
                    "bold": None,
                    "italic": None,
                    "boldItalic": None
                }

            # then try some heuristics to guess which fonts in a potentially large font family can be
            # used to represent the more limited set of four fonts offered by cewe. We should perhaps
            # prefer a particular name (eg in case both Light and Regular exist) but for now the last
            # font in each weight wins
            if fontSubFamily in {"Regular", "Light", "Roman"}:
                additional_fontFamilies[fontFamily]["normal"] = fontFullName
            elif fontSubFamily in {"Bold", "Medium", "Heavy", "Xbold", "Demibold", "Demibold Roman"}:
                additional_fontFamilies[fontFamily]["bold"] = fontFullName
            elif fontSubFamily in {"Italic", "Light Italic", "Oblique"}:
                additional_fontFamilies[fontFamily]["italic"] = fontFullName
            elif fontSubFamily in {"Bold Italic", "Medium Italic", "BoldItalic", "Heavy Italic", "Bold Oblique", "Demibold Italic"}:
                additional_fontFamilies[fontFamily]["boldItalic"] = fontFullName
            else:
                configlogger.warning(f"Unhandled fontSubFamily '{fontSubFamily}', using fontFamily '{fontFamily}' as the regular font name")
                additional_fontFamilies[fontFamily]["normal"] = fontFamily
                additional_fonts[fontFamily] = ttfFile

    logging.info(f"Registering {len(additional_fonts)} fonts")
    # We need to loop over the keys, not the list iterator, so we can delete keys from the list in the loop
    for curFontName in list(additional_fonts):
        try:
            pdfmetrics.registerFont(TTFont(curFontName, additional_fonts[curFontName]))
            configlogger.info(f"Registered '{curFontName}' from '{additional_fonts[curFontName]}'")
        except:# noqa: E722
            configlogger.error(f"Failed to register font '{curFontName}' (from {additional_fonts[curFontName]})")
            del additional_fonts[curFontName]    # remove this item from the font list, so it won't be used later and cause problems.

    # the reportlab manual says:
    #  Before using the TT Fonts in Platypus we should add a mapping from the family name to the individual font
    #  names that describe the behaviour under the <b> and <i> attributes.
    #  from reportlab.pdfbase.pdfmetrics import registerFontFamily
    #  registerFontFamily('Vera',normal='Vera',bold='VeraBd',italic='VeraIt',boldItalic='VeraBI')

    # That's the fonts registered and known to the pdf system. Now for the font families...
    # FIRST we register families explicitly defined in the .ini configuration, because they are
    # potentially providing correct definitions for families which are not correctly identified by
    # the normal heuristic family setup above  - the "fixed" FranklinGothic being a good example:
    # fontFamilies =
    #   FranklinGothic,FranklinGothic,FranklinGothic Medium,Franklin Gothic Book Italic,FranklinGothic Medium Italic
    explicitlyRegisteredFamilyNames = []
    if defaultConfigSection is not None:
        ff = defaultConfigSection.get('FontFamilies', '').splitlines()  # newline separated list of folders
        explicitFontFamilies = filter(lambda bg: (len(bg) != 0), ff)
        for explicitFontFamily in explicitFontFamilies:
            members = explicitFontFamily.split(",")
            if len(members) == 5:
                m_familyname = members[0].strip()
                m_n = members[1].strip()
                m_b = members[2].strip()
                m_i = members[3].strip()
                m_bi = members[4].strip()
                # using font names here which are not already registered as fonts will cause crashes
                # later, so check for that before registering the family
                fontsOk = True
                msg = ""
                for fontToCheck in (m_n, m_b, m_i, m_bi):
                    if fontToCheck not in additional_fonts:
                        if fontsOk:
                            msg = f"Configured font family {m_familyname} ignored because of unregistered fonts: "
                        msg += f"{fontToCheck} "
                        fontsOk = False
                if not fontsOk:
                    configlogger.error(msg)
                else:
                    pdfmetrics.registerFontFamily(m_familyname, normal=m_n, bold=m_b, italic=m_i, boldItalic=m_bi)
                    explicitlyRegisteredFamilyNames.append(m_familyname)
                    configlogger.warning(f"Using configured font family '{m_familyname}': '{m_n}','{m_b}','{m_i}','{m_bi}'")
            else:
                configlogger.error(f'Invalid FontFamilies line ignored (!= 5 comma-separated strings): {explicitFontFamily}')

    # Now we can register the families we have "observed" and built up as we read the font files,
    #  but ignoring any family name which was registered explicitly from configuration
    if len(additional_fontFamilies) > 0:
        for familyName, fontFamily in additional_fontFamilies.items():
            if fontFamily['normal'] is None:
                if fontFamily['italic'] is not None:
                    alternateNormal = 'italic'
                elif fontFamily['bold'] is not None:
                    alternateNormal = 'bold'
                elif fontFamily['boldItalic'] is not None:
                    alternateNormal = 'boldItalic'
                else:
                    alternateNormal = ''
                    configlogger.error(f"Font family '{familyName}' has no normal font and no alternate. The font will not be available")
                if alternateNormal:
                    fontFamily['normal'] = fontFamily[alternateNormal]
                    configlogger.warning(f"Font family '{familyName}' has no normal font, chosen {fontFamily['normal']} from {alternateNormal}")
            for key, value in dict(fontFamily).items(): # looping through normal, bold, italic, bold italic
                if value is None:
                    del fontFamily[key]
            if familyName not in explicitlyRegisteredFamilyNames:
                pdfmetrics.registerFontFamily(familyName, **fontFamily)
                configlogger.info(f"Registered fontfamily '{familyName}': {fontFamily}")
            else:
                configlogger.info(f"Font family '{familyName}' was already registered from configuration file")

    # Read and record non-standard line scale values for specified fonts
    if defaultConfigSection is not None:
        ff = defaultConfigSection.get('fontLineScales', '').splitlines()  # newline separated list of fontname : line_scale
        specifiedLineScales = filter(lambda bg: (len(bg) != 0), ff)
        for specifiedLineScale in specifiedLineScales:
            scaleItems = specifiedLineScale.split(":")
            if len(scaleItems) == 2:
                fontName = scaleItems[0].strip()
                try:
                    scale = float(scaleItems[1].strip())
                    fontLineScales[fontName] = scale
                    configlogger.info(f"Font {fontName} uses non-standard line scale {fontLineScales[fontName]}")
                except ValueError:
                    configlogger.error(f"Invalid line scale value {scaleItems[1]} ignored for {fontName}")
            else:
                configlogger.error(f"Invalid lineScales entry ignored (should be 'FontName: Scale'): {specifiedLineScale}")

    logging.info("Ended font registration")

    # extract properties
    articleConfigElement = fotobook.find('articleConfig')
    if articleConfigElement is None:
        logging.error(f'{albumname} is an old version. Open it in the album editor and save before retrying the pdf conversion. Exiting.')
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
    pdf.setTitle(albumTitle)

    for n in range(pageCount):
        try:
            if (n == 0) or (n == pageCount - 1): # numeric comparisons read best like this so pylint: disable=consider-using-in
                pageNumber = 0
                page = [i for i in
                        fotobook.findall("./page[@pagenr='0'][@type='FULLCOVER']")
                        + fotobook.findall("./page[@pagenr='0'][@type='fullcover']")
                        if (i.find("./area") is not None)
                        ][0]
                oddpage = (n == 0) # bool assign is clearer with parens so pylint: disable=superfluous-parens
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
                    lastpage = False
                    parseInputPage(fotobook, cewe_folder, mcfBaseFolder, backgroundLocations, imagedir, pdf,
                        realFirstPageList[0], pageNumber, pageCount, pagetype, keepDoublePages, oddpage,
                        bg_notFoundDirList, additional_fonts, lastpage)
                pagetype = 'emptypage'
            else:
                pageNumber = n
                oddpage = (pageNumber % 2) == 1
                page = getPageElementForPageNumber(fotobook, n)
                pagetype = 'normal'

            if pageNumbers is not None and pageNumber not in pageNumbers:
                continue

            if page is not None:
                lastpage = (n == pageCount - 2) # bool assign is clearer with parens so pylint: disable=superfluous-parens
                parseInputPage(fotobook, cewe_folder, mcfBaseFolder, backgroundLocations, imagedir, pdf,
                    page, pageNumber, pageCount, pagetype, keepDoublePages, oddpage,
                    bg_notFoundDirList, additional_fonts, lastpage)

            # finish the page and start a new one.
            # If "keepDoublePages" was active, we only start a new page, after the odd pages.
            if ((keepDoublePages is False)
                or ((not (oddpage is False and pagetype == 'normal'))
                    and (not (n == (pageCount - 1) and pagetype == 'cover'))
                   )
               ):
                pdf.showPage()

        except Exception as pageex:
            # if one page fails: continue with next one
            logging.exception("Exception")
            logging.error(f'error on page {n}: {pageex.args[0]}')

    # save final output pdf
    pdf.save()

    pdf = []

    # force the release of objects which might be holding on to picture file references
    # so that they will not prevent the removal of the files as we clean up and exit
    objectscollected = gc.collect()
    logging.info(f'GC collected objects : {objectscollected}')

    # print log count summaries
    print("Total message counts, including messages suppressed by logger configuration")
    print(f"cewe2pdf.config: {configMessageCountHandler.messageCountText()}")
    print(f"root:            {rootMessageCountHandler.messageCountText()}")

    # if he has specified "normal" values for the number of messages of each kind, then warn if we do not see that number
    if defaultConfigSection is not None:
        # the expectedLoggingMessageCounts section is one or more newline separated list of
        #   loggername: levelname[count], ...
        # e.g.
        #   root: WARNING[4], INFO[38]
        # Any loggername that is missing is not checked, any logging level that is missing is expected to have 0 messages
        ff = defaultConfigSection.get('expectedLoggingMessageCounts', '').splitlines()
        loggerdefs = filter(lambda bg: (len(bg) != 0), ff)
        for loggerdef in loggerdefs:
            items = loggerdef.split(":")
            if len(items) == 2:
                loggerName = items[0].strip()
                leveldefs = items[1].strip() # a comma separated list of levelname[count]
                if loggerName == configlogger.name:
                    configMessageCountHandler.checkCounts(loggerName,leveldefs)
                elif loggerName == logging.getLogger().name:
                    rootMessageCountHandler.checkCounts(loggerName,leveldefs)
                else:
                    print(f"Invalid expectedLoggingMessageCounts logger name, entry ignored: {loggerdef}")
            else:
                print(f"Invalid expectedLoggingMessageCounts entry ignored: {loggerdef}")

    # clean up temp files
    for tmpFileName in tempFileList:
        if os.path.exists(tmpFileName):
            os.remove(tmpFileName)
    if unpackedFolder is not None:
        unpackedFolder.cleanup()

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
        logging.info(f'hps data folder found at old location {winHpsFolder}')
        return winHpsFolder

    return None


def getKeyaccountDataFolder(keyAccountNumber, defaultConfigSection=None):
    # for testing (in particular on checkin on github where no cewe product is installed)
    # we may want to have a specially constructed local key account data folder
    if defaultConfigSection is not None:
        inihps = defaultConfigSection.get('hpsFolder')
        if inihps is not None:
            inikadf = os.path.join(inihps, keyAccountNumber)
            if os.path.exists(inikadf):
                logging.info(f'ini file overrides hps folder, key account folder set to {inikadf}')
                return inikadf.strip()
            logging.error(f'ini file overrides hps folder, but key account folder {inikadf} does not exist. Using defaults')

    hpsFolder = getHpsDataFolder()
    if hpsFolder is None:
        logging.warning('No installed hps data folder found')
        return None

    kadf = os.path.join(hpsFolder, keyAccountNumber)
    if os.path.exists(kadf):
        logging.info('Installed key account data folder at {kadf}')
        return kadf
    logging.error(f'Installed key account data folder {kadf} not found')
    return None


def getKeyAccountFileName(cewe_folder):
    keyAccountFileName = os.path.join(cewe_folder, "Resources", "config", "keyaccount.xml")
    return keyAccountFileName


def getKeyaccountNumber(cewe_folder, defaultConfigSection=None):
    keyAccountFileName = getKeyAccountFileName(cewe_folder)
    try:
        katree = etree.parse(keyAccountFileName)
        karoot = katree.getroot()
        ka = karoot.find('keyAccount').text # that's the official installed value
        # see if he has a .ini file override for the keyaccount
        if defaultConfigSection is not None:
            inika = defaultConfigSection.get('keyaccount')
            if inika is not None:
                logging.info(f'ini file overrides keyaccount from {ka} to {inika}')
                ka = inika
    except Exception:
        ka = "0"
        logging.error(f'Could not extract keyAccount tag in file: {keyAccountFileName}, using {ka}')
    return ka.strip()


if __name__ == '__main__':
    # only executed when this file is run directly.
    # we need trick to have both: default and fixed formats.
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
                        help='Page numbers to render, e.g. 1,2,4-9')
    parser.add_argument('--tmp-dir', dest='mcfxTmp', action='store',
                        default=None,
                        help='Directory for .mcfx file extraction')
    parser.add_argument('--appdata-dir', dest='appData',
                        default=None,
                        help='Directory for persistent app data, eg ttf fonts converted from otf fonts')
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

    # convert the file
    resultFlag = convertMcf(args.inputFile, args.keepDoublePages, pages, mcfxTmp, appData)
