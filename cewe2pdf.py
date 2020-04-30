#!/usr/bin/env python
# -*- coding: utf-8 -*-


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


import os, os.path
import logging
import sys
from lxml import etree
import tempfile
from math import sqrt, floor
import html

from reportlab.pdfgen import canvas
import reportlab.lib.pagesizes
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import ParagraphStyle

import PIL
from PIL.ExifTags import TAGS
from io import BytesIO
from pathlib import Path
import argparse  # to parse arguments

import configparser # to read config file, see https://docs.python.org/3/library/configparser.html


logging.basicConfig(stream=sys.stderr, level=logging.INFO)

#### settings ####
image_quality = 86 # 0=worst, 100=best
image_res = 150 # dpi
bg_res = 100 # dpi
###########

#.mcf units are 0.1 mm
# Tabs seem to be in 8mm pitch
tab_pitch = 80
line_scale = 1.2

# definitions
formats = {"ALB82": reportlab.lib.pagesizes.A4,
           "ALB69": (5400/100/2*reportlab.lib.units.cm, 3560/100*reportlab.lib.units.cm)}  # add other page sizes here
f = 72. / 254.  # convert from mcf (unit=0.1mm) to reportlab (unit=inch/72)

tempFileList = []  # we need to remove all this temporary files at the end

# reportlab defaults
pdf_styles = getSampleStyleSheet()
pdf_styleN = pdf_styles['Normal']
pdf_flowableList = []

def autorot(im):
    # some cameras return JPEG in MPO container format. Just use the first image.
    if im.format != 'JPEG' and im.format != 'MPO':
        return im
    exifdict = im._getexif()
    if exifdict != None and 274 in list(exifdict.keys()):
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

    prtStr = 'Could not find %s [%s] in paths %s' % (
        filebase, ' '.join(extList), ', '.join(paths))
    print(prtStr)
    raise ValueError(prtStr)


def findFileInDirs(filenames, paths):
    if  not isinstance(filenames, list): filenames = [filenames]
    for f in filenames:
        for p in paths:
            testPath = os.path.join(p, f)
            if os.path.exists(testPath):
                return testPath

    print('Could not find %s in %s paths' % (filenames, ', '.join(paths)))
    raise ValueError('Could not find %s in %s paths' % (filenames, ', '.join(paths)))


def getPageElementForPageNumber(fotobook, pageNumber):
    return fotobook.find("./page[@pagenr='{}']".format(floor(2 * (pageNumber / 2)), 'd'))

# This is only used for the <background .../> tags. The stock backgrounds use this element.
def processBackground(backgroundTags, bg_notFoundDirList, cewe_folder, backgroundLocations, keepDoublePages, oddpage, pagetype, pdf, ph, pw):
    if (pagetype=="emptypage"): #don't draw background for the empty pages. That is page nr. 1 and pageCount-1.
        return
    if backgroundTags != None and len(backgroundTags) > 0:
        # look for a tag that has an alignment attribute
        for curTag in backgroundTags:
            if curTag.get('alignment') != None:
                backgroundTag = curTag
                break
    
        if (backgroundTag != None and cewe_folder != None and
                backgroundTag.get('designElementId') != None):
            bg = backgroundTag.get('designElementId')
            # example: fading="0" hue="270" rotation="0" type="1"
            backgroundFading = 0
            if "fading" in backgroundTag.attrib:
                if float(backgroundTag.get('fading')) != 0:
                    print('value of background attribute not supported: fading = %s' % backgroundTag.get(
                        'fading'))
            backgroundHue = 0
            if "hue" in backgroundTag.attrib:
                if float(backgroundTag.get('hue')) != 0:
                    print(
                        'value of background attribute not supported: hue =  %s' % backgroundTag.get('hue'))
            backgroundRotation = 0
            if "rotation" in backgroundTag.attrib:
                if float(backgroundTag.get('rotation')) != 0:
                    print('value of background attribute not supported: rotation =  %s' % backgroundTag.get(
                        'rotation'))
            backgroundType = 1
            if "type" in backgroundTag.attrib:
                if int(backgroundTag.get('type')) != 1:
                    print(
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
                print("Reading background file: {}".format(bgPath))
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
                #pdf.drawImage(ImageReader(bgpath), f * ax, 0, width=f * aw, height=f * ah)
            except Exception as ex:
                if bgPath not in bg_notFoundDirList:
                    print('cannot find background or error when adding to pdf', bgPath, '\n', ex.args[0])
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    print('', (exc_type, fname, exc_tb.tb_lineno))
                bg_notFoundDirList.add(bgPath)
    return

def processAreaImageTag(imageTag, area, areaHeight, areaRot, areaWidth, imagedir, keepDoublePages, mcfBaseFolder, pagetype, pdf, pw, transx, transy):
        # open raw image file
        if imageTag.get('filename') == None:
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
        imageWidth_px, imageHeight_px = im.size
        imsc = float(imageTag.find('cutout').get('scale'))
    
        # without cropping: to get from a image pixel width to the areaWidth in .mcf-units, the image pixel width is multiplied by the scale factor.
        # to get from .mcf units are divided by the scale factor to get to image pixel units.
    
        # crop image
        im = im.crop((int(0.5 - imleft/imsc),
                        int(0.5 - imtop/imsc),
                        int(0.5 - imleft/imsc +
                            areaWidth / imsc),
                        int(0.5 - imtop/imsc + areaHeight / imsc)))
    
        # scale image
        # re-scale the image if it is much bigger than final resolution in PDF
        # set desired DPI based on where the image is used. The background gets a lower DPI.
        if imageTag.tag == 'imagebackground' and pagetype != 'cover':
            res = bg_res
        else:
            res = image_res
        # 254 -> convert from mcf unit (0.1mm) to inch (1 inch = 25.4 mm)
        new_w = int(0.5 + areaWidth * res / 254.)
        new_h = int(0.5 + areaHeight * res / 254.)
        factor = sqrt(new_w * new_h /
                        float(im.size[0] * im.size[1]))
        if factor <= 0.8:
            im = im.resize(
                (new_w, new_h), PIL.Image.ANTIALIAS)
        im.load()
    
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
        print('image', imageTag.get('filename'))
        pdf.translate(img_transx, transy)
        pdf.rotate(-areaRot)
        pdf.drawImage(ImageReader(jpeg.name),
                        f * -0.5 * areaWidth, f * -0.5 * areaHeight,
                        width=f * areaWidth, height=f * areaHeight, mask='auto')
        pdf.rotate(areaRot)
        pdf.translate(-img_transx, -transy)
    
        # we now have temporary file, that we need to delete after pdf creation
        tempFileList.append(jpeg.name)
        # we can not delete now, because file is opened by pdf library

def AppendText(paratext, newtext):
    if newtext is None:
        return paratext
    return paratext + newtext

def AppendBreak(paragraphText, parachild):
    br = parachild
    paragraphText = AppendText(paragraphText, "<br></br>")
    paragraphText = AppendText(paragraphText, br.tail)
    return paragraphText

def CreateParagraphStyle(backgroundColor, textcolor, font, fontsize):
    parastyle = ParagraphStyle(None, None,
        alignment=reportlab.lib.enums.TA_LEFT, # will often be overridden
        fontSize=fontsize,
        fontName=font,
        leading=fontsize*line_scale,  # line spacing (text + leading)
        borderPadding=0,
        borderWidth=0,
        leftIndent=0,
        rightIndent=0,
        embeddedHyphenation=1, # allow line break on existing hyphens
        textColor=textcolor,
        backColor=backgroundColor)
    return parastyle

def processAreaTextTag(textTag, additionnal_fonts, area, areaHeight, areaRot, areaWidth, pdf, transx, transy):
    # note: it would be better to use proper html processing here
    htmlxml = etree.XML(textTag.text)
    body = htmlxml.find('.//body')
    bstyle = dict([kv.split(':') for kv in
                    body.get('style').lstrip(' ').rstrip(';').split('; ')])
    family = bstyle['font-family'].strip("'")
    font = 'Helvetica'
    try:
        bodyfs = floor(float(bstyle['font-size'].strip("pt")))
    except:
        bodyfs = 20
    if family in pdf.getAvailableFonts():
        font = family
    elif family in additionnal_fonts:
        font = family
    color = '#000000' 
    maxfs = bodyfs

    pdf.translate(transx, transy)
    pdf.rotate(-areaRot)
    
    #Get the background color. It is stored in an extra element.
    backgroundColor = None
    backgroundColorAttrib = area.get('backgroundcolor')
    if (backgroundColorAttrib is not None):
        backgroundColor = reportlab.lib.colors.HexColor(backgroundColorAttrib)
    
    # set default para style in case there are no spans to set it
    pdf_styleN = CreateParagraphStyle(backgroundColor, reportlab.lib.colors.black, font, bodyfs)

    ################
    # potential killer here .. the leading for the paragraph is set on the basis of the bodyfs and will
    # not be changed as the size of the text changes! So the lines of the paragraph can collide
    # or be too widely spaced for the font size as that size changes through the paragraph.
    ################

    # pdf_styleN.backColor = reportlab.lib.colors.HexColor("0xFFFF00") # for debuging useful
    
    htmlparas = body.findall(".//p")
    for p in htmlparas:
        if p.get('align') == 'center':
            pdf_styleN.alignment = reportlab.lib.enums.TA_CENTER
        elif p.get('align') == 'right':
            pdf_styleN.alignment = reportlab.lib.enums.TA_RIGHT
        else:
            pdf_styleN.alignment = reportlab.lib.enums.TA_LEFT
        paragraphText = '<para autoLeading="max">'
        htmlspans = p.findall(".*")
        if (len(htmlspans) < 1): 
            # append the paragraph text, accepting whatever format is valid now
            if (p.text == None):
                paragraphText = AppendText(paragraphText, "<br></br>")
            else:
                paragraphText = AppendText(paragraphText, html.escape(p.text))
        else:
            for item in htmlspans:
                if item.tag == 'br':
                    paragraphText = AppendBreak(paragraphText, item)
                elif item.tag == 'span':
                    span = item
                    spanfont = font
                    style = dict([kv.split(':') for kv in
                                    span.get('style').lstrip(' ').rstrip(';').split('; ')])
                    if 'font-family' in style:
                        spanfamily = style['font-family'].strip(
                            "'")
                        if spanfamily in pdf.getAvailableFonts():
                            spanfont = spanfamily
                        elif spanfamily in additionnal_fonts:
                            spanfont = spanfamily
                        if spanfamily != spanfont:
                            print("Using font family = '%s' (wanted %s)" % (
                                spanfont, spanfamily))
                    if 'font-size' in style:
                        spanfs = floor(float(style['font-size'].strip("pt")))
                    else:
                        spanfs = bodyfs
                    if spanfs > maxfs:
                        maxfs = spanfs

                    paragraphText = AppendText(paragraphText, '<span name="' + spanfont + '"'
                        ' size=' + str(spanfs)
                        )

                    if 'color' in style:
                        paragraphText = AppendText(paragraphText, ' color=' + style['color'] )

                    if 'font-style' in style:
                        pass  # paragraphText = AppendText(paragraphText, ' style=' + style['font-style'] )

                    if (backgroundColorAttrib is not None):
                        paragraphText = AppendText(paragraphText, ' backcolor=' + backgroundColorAttrib)
                    
                    paragraphText = AppendText(paragraphText, '>')
                                    
                    # append the text of the span
                    paragraphText = AppendText(paragraphText, html.escape(span.text))
            
                    # there might be line breaks within the span. Could be that this should be recursive.
                    for spanchild in span:
                        if spanchild.tag == 'br':
                            paragraphText = AppendBreak(paragraphText, spanchild)

                    paragraphText = AppendText(paragraphText, '</span>')

                    if (span.tail != None):
                        paragraphText = AppendText(paragraphText, html.escape(span.tail))
                else:
                    print('Ignoring unhandled tag ' + item.tag )

        paragraphText += '</para>'

        pdf_styleN.leading = maxfs * line_scale  # line spacing (text + leading)

        pdf_flowableList.append(Paragraph(paragraphText, pdf_styleN))

    #Add a frame object that can contain multiple paragraphs
    frameBottomLeft_x = -0.5 * f * areaWidth
    frameBottomLeft_y = -0.5 * f * areaHeight
    frameWidth = f * areaWidth
    frameHeight = f * areaHeight

    #Go through all flowables and test if the fit in the frame. If not increase the frame height.
    #To solve the problem, that if each paragraph will fit indivdually, and also all together,
    # we need to keep track of the total summed height+
    totalMaxHeight = 0
    for j in range(len(pdf_flowableList)):
        neededWidth, neededHeight = pdf_flowableList[j].wrap(frameWidth, frameHeight)
        totalMaxHeight += neededHeight
    if (totalMaxHeight > frameHeight):
        print('Warning: A set of paragraphs would not fit inside its frame. Frame height will be increased to prevent loss of text.')
    frameHeight = max( frameHeight, totalMaxHeight)   # increase the height

    newFrame = Frame(frameBottomLeft_x, frameBottomLeft_y,
                        frameWidth, frameHeight,
                        leftPadding=0, bottomPadding=0,
                        rightPadding=0, topPadding=0,
                        showBoundary=0  # for debugging useful
                        )

    #This call should produce an exception, if any of the flowables do not fit inside the frame.
    #But there seems to be a bug, and no exception is triggered.
    #We took care of this by making the frame so large, that it always can fit the flowables.
    #maybe should switch to res=newFrame.split(flowable, pdf) and check the result manually.
    newFrame.addFromList(pdf_flowableList, pdf)

    pdf.rotate(areaRot)
    pdf.translate(-transx, -transy)
    return

def processAreaClipartTag(clipartElement):
    clipartID = int( clipartElement.get('designElementId'))
    print("Warning: clip-art elements are not supported. (designElementId = {})".format(clipartID))

def processElements(additionnal_fonts, fotobook, imagedir, keepDoublePages, mcfBaseFolder, oddpage, page, pageNumber, pagetype, pdf, ph, pw):
    if keepDoublePages and oddpage == 1 and pagetype == 'normal':
        # if we are in double-page mode, all the images are already drawn by the even pages.
        return
    else:
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
                processAreaTextTag(textTag, additionnal_fonts, area, areaHeight, areaRot, areaWidth, pdf, transx, transy)
                        
            #Clip-Art
            #In the clipartarea there are two similar elements, the <designElementIDs> and the <clipart>.
            # We are using the <clipart> element here
            for clipartElement in area.findall('clipart'):                            
                processAreaClipartTag(clipartElement)

    return

def parseInputPage(fotobook, cewe_folder, mcfBaseFolder, backgroundLocations, imagedir, pdf, page, pageNumber, pageCount, pagetype, keepDoublePages, oddpage, bg_notFoundDirList, additionnal_fonts):
    print('parsing page', page.get('pagenr'), ' of ', pageCount)

    bundlesize = page.find("./bundlesize")
    if (bundlesize is not None):
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
    processElements(additionnal_fonts, fotobook, imagedir, keepDoublePages, mcfBaseFolder, oddpage, page, pageNumber, pagetype, pdf, ph, pw)

def getBaseBackgroundLocations(basefolder):
    # create a tuple of places (folders) where background resources would be found by default
    baseBackgroundLocations = (
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds'),
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'einfarbige'),
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'multicolor'),
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'spotcolor'),
    )
    return baseBackgroundLocations

def convertMcf(mcfname, keepDoublePages:bool):
    # Get the folder in which the .mcf file is
    mcfPathObj = Path(mcfname).resolve()    # convert it to an absolute path
    mcfBaseFolder = mcfPathObj.parent

    # parse the input mcf xml file
    # read file as binary, so UTF-8 encoding is preserved for xml-parser
    mcffile = open(mcfname, 'rb')
    mcf = etree.parse(mcffile)
    mcffile.close()
    fotobook = mcf.getroot()
    if fotobook.tag != 'fotobook':
        print(mcfname + 'is not a valid mcf file. Exiting.')
        sys.exit(1)

    # find cewe folder using the original cewe_folder.txt file
    try:
        configFolderFileName = findFileInDirs(
            'cewe_folder.txt', (mcfBaseFolder,  os.path.curdir))
        cewe_file = open(configFolderFileName, 'r')
        cewe_folder = cewe_file.read().strip()
        cewe_file.close()
        baseBackgroundLocations = getBaseBackgroundLocations(cewe_folder)
        backgroundLocations = baseBackgroundLocations
    except:
        print('cannot find cewe installation folder from cewe_folder.txt, trying cewe2pdf.ini')
        configuration = configparser.ConfigParser()
        filesread = configuration.read('cewe2pdf.ini')
        if len(filesread) < 1: 
            print('cannot find cewe installation folder cewe_folder in cewe2pdf.ini')
            cewe_folder = None
        else:
            defaultConfigSection = configuration['DEFAULT']
            # find cewe folder from ini file
            cewe_folder = defaultConfigSection['cewe_folder'].strip()
            baseBackgroundLocations = getBaseBackgroundLocations(cewe_folder)
            # add any extra background folders
            xbg = defaultConfigSection.get('extraBackgroundFolders','').splitlines() # newline separated list of folders
            fxbg = tuple(filter(lambda bg: (len(bg) != 0), xbg))
            backgroundLocations = baseBackgroundLocations + fxbg
    
    bg_notFoundDirList = set([])   #keep a list with background folders that not found, to prevent multiple errors for the same cause.

    # Load additionnal fonts
    additionnal_fonts = {}
    try:
        configFontFileName = findFileInDirs('additional_fonts.txt', (mcfBaseFolder,  os.path.curdir))
        with open(configFontFileName, 'r') as fp:
            for line in fp:
                p = line.split(" = ", 1)
                additionnal_fonts[p[0]] = p[1].strip()
            fp.close()
    except:
        print('cannot find additionnal fonts (define them in additional_fonts.txt)')
        print('Content example:')
        print('Vera = /tmp/vera.ttf')
        print('Separator is " = " (space equal space)')

    # create pdf
    pagesize = reportlab.lib.pagesizes.A4
    if fotobook.get('productname') in formats:
        pagesize = formats[fotobook.get('productname')]
    pdf = canvas.Canvas(mcfname + '.pdf', pagesize=pagesize)

    # Add additionnal fonts
    for n in additionnal_fonts:
        try:
            pdfmetrics.registerFont(TTFont(n, additionnal_fonts[n]))
            print("Successfully registered '%s' from '%s'" %
                  (n, additionnal_fonts[n]))
        except:
            print("Failed to register font '%s' (from %s)" %
                  (n, additionnal_fonts[n]))

    # extract properties
    articleConfigElement = fotobook.find('articleConfig')
    if articleConfigElement == None:
        print(mcfname + ' is an old version. Open it in the album editor and save before retrying the pdf conversion. Exiting.')
        sys.exit(1)
    pageCount = int(articleConfigElement.get('normalpages')) + 2    #maximum number of pages
    imagedir = fotobook.get('imagedir')

    for n in range(pageCount):
        try:
            if (n == 0) or (n == pageCount - 1):
                pageNumber = 0
                page = [i for i in
                        fotobook.findall("./page[@pagenr='0'][@type='FULLCOVER']") +
                        fotobook.findall("./page[@pagenr='0'][@type='fullcover']")
                        if (i.find("./area") is not None)][0]
                oddpage = (n == 0)
                pagetype = 'cover'
                 #for double-page-layout: the last page is already the left side of the book cover. So skip rendering the last page
                if ((keepDoublePages == True) and  (n == (pageCount - 1))):
                    page = None
            elif n == 1:
                pageNumber = 1
                oddpage = True
                #Look for an empty page 0 that still contains an area element
                page = [i for i in
                        fotobook.findall("./page[@pagenr='0'][@type='EMPTY']") +
                        fotobook.findall("./page[@pagenr='0'][@type='emptypage']")
                        if (i.find("./area") is not None)]
                if (len(page) >= 1):                
                    page = page[0]
                    #If there is on page 1 only text, the area-tag is still on page 0.
                    #  So this will either include the text (which is put in page 0),
                    #  or the packground which is put in page 1.

                #Look for the the frist page and set it up for processing
                realFirstPageList = fotobook.findall("./page[@pagenr='1'][@type='normalpage']")
                if (len(realFirstPageList) > 0):
                     # we need to do run parseInputPage twico for one output page in the PDF.
                     #The background needs to be drawn first, or it would obscure any other other elements.
                    pagetype = 'singleside'
                    parseInputPage(fotobook, cewe_folder, mcfBaseFolder, backgroundLocations, imagedir, pdf, realFirstPageList[0], pageNumber, pageCount, pagetype, keepDoublePages, oddpage, bg_notFoundDirList, additionnal_fonts)
                pagetype = 'emptypage'
            else:
                pageNumber = n
                oddpage = (pageNumber % 2) == 1
                page = getPageElementForPageNumber(fotobook, n)
                pagetype = 'normal'

            if (page != None):
                parseInputPage(fotobook, cewe_folder, mcfBaseFolder, backgroundLocations, imagedir, pdf, page, pageNumber, pageCount, pagetype, keepDoublePages, oddpage, bg_notFoundDirList, additionnal_fonts)

            # finish the page and start a new one.
            # If "keepDoublePages" was active, we only start a new page, after the odd pages.
            if ( (keepDoublePages == False)
               or (
                    (not (keepDoublePages==True and oddpage==True and pagetype =='normal'))
                and (not (keepDoublePages==True and n == (pageCount - 1) and pagetype =='cover'))
               )):
                pdf.showPage()

        except Exception as ex:
            # if one page fails: continue with next one
            print('error on page %i:' % (n, ), '\n', ex.args[0])
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print('', (exc_type, fname, exc_tb.tb_lineno))

    # save final output pdf
    pdf.save()

    pdf = []

    # clean up temp files
    for tmpFileName in tempFileList:
        if os.path.exists(tmpFileName):
            os.remove(tmpFileName)
    return True

if __name__ == '__main__':
    # only executed when this file is run directly.
    # we need trick to have both: default and fixed formats.
    class CustomArgFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass

    parser = argparse.ArgumentParser(description='nConvert a foto-book from .mcf file format to .pdf',
                                     epilog="Example:\n   python cewe2pdf.py c:\\path\\to\\my\\files\\my_nice_fotobook.mcf",
                                     formatter_class=CustomArgFormatter)
    parser.add_argument('--keepDoublePages', dest='keepDoublePages', action='store_const',
                        const=True, default=False,
                        help='Each page in the .pdf will be a double-sided page, instead of a normal single page.')
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

    # if we have a file name, let's convert it
    resultFlag = convertMcf(args.inputFile, args.keepDoublePages)