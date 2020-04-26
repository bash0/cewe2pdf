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


import os
import os.path
import sys
from lxml import etree
import tempfile
from math import *

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


#### settings ####
image_quality = 86  # 0=worst, 100=best
image_res = 150  # dpi
bg_res = 100  # dpi
###########

# .mcf units are 0.1 mm

# definitions
formats = {"ALB82": reportlab.lib.pagesizes.A4,
           "ALB69": (5400/100/2*reportlab.lib.units.cm, 3560/100*reportlab.lib.units.cm)}  # add other page sizes here
f = 72. / 254.  # convert from mcf (unit=0.1mm) to reportlab (unit=inch/72)

tempFileList = []  # we need to remove all this temporary files at the end

# reportlab defaults
pdf_styles = getSampleStyleSheet()
pdf_styleN = pdf_styles['Normal']
pdf_story = []


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


def findFileInDirs(filename, paths):
    for p in paths:
        testPath = os.path.join(p, filename)
        if os.path.exists(testPath):
            return testPath

    prtStr = 'Could not find %s in %s paths %s' % (filename, ', '.join(paths))
    print(prtStr)
    raise ValueError(prtStr)

def getPageElementForPageNumber(fotobook, pageNumber):
    return fotobook.find("./page[@pagenr='{}']".format(floor(2 * (pageNumber / 2)), 'd'))

def parseInputPage(fotobook, cewe_folder, pdf, page, pn, pageCount, pagetype, keepDoublePages, oddpage, bg_notFoundDirList, additionnal_fonts):
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
                bgpath = findFileByExtInDirs(bg, ('.webp', '.jpg', '.bmp'), (
                    os.path.join(cewe_folder, 'Resources',
                                    'photofun', 'backgrounds'),
                    os.path.join(
                        cewe_folder, 'Resources', 'photofun', 'backgrounds', 'einfarbige'),
                    os.path.join(
                        cewe_folder, 'Resources', 'photofun', 'backgrounds', 'multicolor'),
                ))
                areaWidth = pw*2
                if keepDoublePages:
                    areaWidth = pw
                areaHeight = ph
                if pagetype != 'singleside' and oddpage and not keepDoublePages:
                    ax = -areaWidth / 2.
                else:
                    ax = 0
                # webp doesn't work with PIL.Image.open in Anaconda 5.3.0 on Win10
                imObj = PIL.Image.open(bgpath)
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
                if bgpath not in bg_notFoundDirList:
                    print(
                        'cannot find background or error when adding to pdf', bgpath, '\n', ex.args[0])
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(
                        exc_tb.tb_frame.f_code.co_filename)[1]
                    print('', (exc_type, fname, exc_tb.tb_lineno))
                bg_notFoundDirList.add(bgpath)

    # all elements (images, text,..) for even and odd pages are defined on the even page element!
    if keepDoublePages and oddpage == 1 and pagetype == 'normal':
        # if we are in double-page mode, all the images are already drawn by the even pages.
        return
    else:
        # switch pack to the page element for the even page to get the elements
        if pagetype == 'normal' and oddpage == 1:
            page = getPageElementForPageNumber(fotobook, 2*floor(pn/2))

        for area in page.findall('area'):
            areaPos = area.find('position')
            areaLeft = float(areaPos.get('left').replace(',', '.'))
            # old python 2 code: aleft = float(area.get('left').replace(',', '.'))
            if pagetype != 'singleside' or len(area.findall('imagebackground')) == 0:
                if oddpage and not keepDoublePages:
                    # shift double-page content from other page
                    areaLeft -= pw
            areaTop = float(areaPos.get('top').replace(',', '.'))
            areaWidth = float(areaPos.get(
                'width').replace(',', '.'))
            areaHeight = float(areaPos.get(
                'height').replace(',', '.'))
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
            for image in area.findall('imagebackground') + area.findall('image'):
                # open raw image file
                if image.get('filename') == None:
                    continue
                imagepath = os.path.join(
                    mcfBaseFolder, imagedir, image.get('filename'))
                # the layout software copies the images to another collection folder
                imagepath = imagepath.replace(
                    'safecontainer:/', '')
                im = PIL.Image.open(imagepath)

                if image.get('backgroundPosition') == 'RIGHT_OR_BOTTOM':
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
                imleft = float(image.find('cutout').get(
                    'left').replace(',', '.'))
                imtop = float(image.find('cutout').get(
                    'top').replace(',', '.'))
                imageWidth_px, imageHeight_px = im.size
                imsc = float(image.find('cutout').get('scale'))

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
                if image.tag == 'imagebackground' and pagetype != 'cover':
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
                print('image', image.get('filename'))
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
                # try to delete the temporary file again. Needed for Windows
                # if os.path.exists(jpeg.name):
                #    os.remove(jpeg.name)

            # process text
            for text in area.findall('text'):
                # note: it would be better to use proper html processing here
                html = etree.XML(text.text)
                body = html.find('.//body')
                bstyle = dict([kv.split(':') for kv in
                                body.get('style').lstrip(' ').rstrip(';').split('; ')])
                family = bstyle['font-family'].strip("'")
                font = 'Helvetica'
                try:
                    fs = int(bstyle['font-size'].strip("pt"))
                except:
                    fs = 20
                if family in pdf.getAvailableFonts():
                    font = family
                elif family in additionnal_fonts:
                    font = family
                color = '#000000'

                pdf.translate(transx, transy)
                pdf.rotate(-areaRot)
                y_p = 0
                for p in body.findall(".//p"):
                    for span in p.findall(".//span"):
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
                            fs = int(
                                style['font-size'].strip()[:-2])
                            if 'color' in style:
                                color = style['color']
                        # pdf.setFont(spanfont, fs) # from old code with drawCentredString
                        # pdf.setFillColor(color) # from old code with drawCentredString
                        pdf_styleN = ParagraphStyle(None, None,
                                                    alignment=reportlab.lib.enums.TA_LEFT,
                                                    fontSize=fs,
                                                    fontName=spanfont,
                                                    leading=fs*1.2,  # line spacing
                                                    borderPadding=0,
                                                    borderWidth=0,
                                                    leftIndent=0,
                                                    rightIndent=0,
                                                    textColor=reportlab.lib.colors.HexColor(
                                                        color)
                                                    )
                        if p.get('align') == 'center':
                            #    pdf.drawCentredString(0,
                            #        0.5 * f * areaHeight + y_p -1.3*fs, span.text)
                            pdf_styleN.alignment = reportlab.lib.enums.TA_CENTER
                        elif p.get('align') == 'right':
                            #    pdf.drawRightString(0.5 * f * areaWidth,
                            #        0.5 * f * areaHeight + y_p -1.3*fs, span.text)
                            pdf_styleN.alignment = reportlab.lib.enums.TA_RIGHT
                        else:
                            #    pdf.drawString(-0.5 * f * areaWidth,
                            #        0.5 * f * areaHeight + y_p -1.3*fs, span.text)
                            pdf_styleN.alignment = reportlab.lib.enums.TA_LEFT
                        # add some flowables
                        # pdf_styleN.backColor = reportlab.lib.colors.HexColor("0xFFFF00") # for debuging useful

                        newString = '<para autoLeading="max">' + span.text + '</para>'
                        pdf_story.append(
                            Paragraph(newString, pdf_styleN))

                    y_p -= 1.3*fs
                newFrame = Frame(-0.5 * f * areaWidth, -0.5 * f * areaHeight,
                                    f * areaWidth, f * areaHeight,
                                    leftPadding=0, bottomPadding=0,
                                    rightPadding=0, topPadding=0,
                                    showBoundary=1  # for debugging useful
                                    )
                newFrame.addFromList(pdf_story, pdf)

                pdf.rotate(areaRot)
                pdf.translate(-transx, -transy)
                        
            #Clip-Art
            #In the clipartarea there are two similar elements, the <designElementIDs> and the <clipart>.
            # We are using the <clipart> element here
            for clipartElement in area.findall('clipart'):                            
                clipartID = int( clipartElement.get('designElementId'))
                print("Warning: clip-art elements are not supported. (designElementId = {})".format(clipartID))


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

    # find cewe folder
    try:
        configFolderFileName = findFileInDirs(
            'cewe_folder.txt', (mcfBaseFolder,  os.path.curdir))
        cewe_file = open(configFolderFileName, 'r')
        cewe_folder = cewe_file.read().strip()
        cewe_file.close()
    except:
        print('Cannot find cewe installation folder in cewe_folder.txt. Stock backgrounds will not be unavailable.')
        cewe_folder = None
    bg_notFoundDirList = set([])   #keep a list with background folders that not found, to prevent multiple errors for the same cause.

    # Load additionnal fonts
    additionnal_fonts = {}
    try:
        configFontFileName = findFileInDirs(
            'additional_fonts.txt', (mcfBaseFolder,  os.path.curdir))
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
    pageCount = int(articleConfigElement.get('normalpages')) + 2    #maximum number of pages
    imagedir = fotobook.get('imagedir')

    for n in range(pageCount):
        try:
            if (n == 0) or (n == pageCount - 1):
                pn = 0
                page = [i for i in
                        fotobook.findall("./page[@pagenr='0'][@type='FULLCOVER']") +
                        fotobook.findall(
                            "./page[@pagenr='0'][@type='fullcover']")
                        if (i.find("./area") is not None)][0]
                oddpage = (n == 0)
                pagetype = 'cover'
            elif n == 1:

                pn = 1
                page = [i for i in
                        fotobook.findall("./page[@pagenr='0'][@type='EMPTY']") +
                        fotobook.findall(
                            "./page[@pagenr='0'][@type='emptypage']")
                        if (i.find("./area") is not None)]
                if (len(page) >= 1):
                    page = page[0]
                    # there is a bug here: if on page 1 is only text, the area-tag is on page 0.
                    #  So this will either include the text (which is put in page 0),
                    #  or the packground which is put in page 1.
                    # Probably need to rewrite the whole loop to fix this.
                    if (len(fotobook.findall("./page[@pagenr='1'][@type='normalpage']")) > 0):
                        print(
                            "Warning: can't process structure of first page. There will be missing details on first page.")
                else:
                    page = None
                oddpage = True
                pagetype = 'singleside'
            else:
                pn = n
                oddpage = (pn % 2) == 1
                page = getPageElementForPageNumber(fotobook, n)
                pagetype = 'normal'

            if (page != None):
                parseInputPage(fotobook, cewe_folder, pdf, page, pn, pageCount, pagetype, keepDoublePages, oddpage, bg_notFoundDirList, additionnal_fonts)

            # finish the page
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

    parser = argparse.ArgumentParser(description='Convert a foto-book from .mcf file format to .pdf',
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
