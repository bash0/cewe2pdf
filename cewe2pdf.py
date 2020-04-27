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

from reportlab.rl_config import canvas_basefontname as _baseFontName
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import reportlab.lib.pagesizes
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import PIL
from PIL.ExifTags import TAGS
from io import BytesIO
from pathlib import Path
import argparse     #to parse arguments

import configparser # to read config file, see https://docs.python.org/3/library/configparser.html


logging.basicConfig(stream=sys.stderr, level=logging.INFO) # DEBUG, INFO

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
           "ALB69": (5400/100/2*reportlab.lib.units.cm, 3560/100*reportlab.lib.units.cm)} # add other page sizes here
f = 72. / 254. # convert from mcf (unit=0.1mm) to reportlab (unit=inch/72)

tempFileList =[]    #we need to remove all this temporary files at the end

def autorot(im):
    if im.format != 'JPEG' and im.format != 'MPO':      #some cameras return JPEG in MPO container format. Just use the first image.
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

def findFileInDirs(filenames, paths):
    if  not isinstance(filenames, list): filenames = [filenames]
    for f in filenames:
        for p in paths:
            testPath = os.path.join(p, f)
            if os.path.exists(testPath):
                return testPath

    print('Could not find %s in %s paths' % (filenames, ', '.join(paths)))
    raise ValueError('Could not find %s in %s paths' % (filenames, ', '.join(paths)))

def getBaseBackgroundLocations(basefolder):
    # create a tuple of places (folders) where background resources would be found by default
    baseBackgroundLocations = (
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds'),
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'einfarbige'),
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'multicolor'),
        os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'spotcolor'),
    )
    return baseBackgroundLocations

#def textobject_demo(my_canvas, x, y):
#    # Create textobject
#    textobject = my_canvas.beginText()
#    # Set text location (x, y)
#    textobject.setTextOrigin(x, y)
#    # Set font face and size
#    textobject.setFont('Times-Roman', 16)
#    # Change text color
#    textobject.setFillColor(colors.red)
#    # Write red text
#    textobject.textLine(text='Python rocks in red!')
#    # Write text to the canvas
#    my_canvas.drawText(textobject)

#def paragraph_demo(my_canvas, x, y):
#    styles = getSampleStyleSheet()
#    ptext = """
#        The document you are holding is a set of requirements for your next mission, should you
#        choose to accept it. In any event, this document will self-destruct <b>%s</b> seconds after you
#        read it. Yes, <b>%s</b> can tell when you're done...usually.
#        """ % (10, "we")
#    p = Paragraph(ptext, styles["Normal"])
#    p.wrapOn(my_canvas, 200, 100)
#    p.drawOn(my_canvas, x, y)

def AdjustXLine(current_x_line, fs, text):
    x_line = current_x_line
    if text == '':
        x_line += tab_pitch*f
    else:
        x_line += (floor((len(text)*0.55*fs/f)/tab_pitch)+1)*tab_pitch*f
    return x_line

def DrawStyledParagraph(pdf, text, paragraphStyle, areaHeight, areaWidth, x_line, y_line):
    p = Paragraph(text, paragraphStyle)
    p.wrapOn(pdf, f * areaWidth, f * areaHeight)
    p.drawOn(pdf, -0.5 * f * areaWidth + x_line, -0.5 * f * areaHeight + y_line)
    return AdjustXLine(x_line, paragraphStyle.fontSize, text)

def PreanalyzeFontSizes(fs_body, htmlpara):
    fs_max = 0
    for span in htmlpara.findall(".//span"):
        spanstyle = dict([kv.split(':') for kv in
            span.get('style').lstrip(' ').rstrip(';').split('; ')])
        fs = fs_body
        if 'font-size' in spanstyle:
            fs = int(spanstyle['font-size'].strip("pt"))
        if fs_max < fs:
            fs_max = fs
    return fs_max

def DrawText(pdf, text, areaHeight, areaWidth, additionnal_fonts):
    # note: it would be better to use proper html processing here
    # Replace linefeeds
    text.text = text.text.replace('<br />', '\n')
    html = etree.XML(text.text)
    body = html.find('.//body')
    bodystyle = dict([kv.split(':') for kv in
        body.get('style').lstrip(' ').rstrip(';').split('; ')])
    family = bodystyle['font-family'].strip("'")
    parafont = 'Helvetica'
    try:
        bodyfs = int(bodystyle['font-size'].strip("pt"))
    except:
        bodyfs = 20
    if family in pdf.getAvailableFonts():
        parafont = family
    elif family in additionnal_fonts:
        parafont = family
    color = '#000000'
    y_para = 0.0
    for htmlpara in body.findall(".//p"):
        # Pre-analyze fontsizes
        fs_max = PreanalyzeFontSizes(bodyfs, htmlpara)
    
        # Do the writing
        x_span = 0.0
        y_span = 0.0
        lines_span = 0
        for span in htmlpara.findall(".//span"): # each span in the html para
            spanfont = parafont
            spanstyle = dict([kv.split(':') for kv in
                span.get('style').lstrip(' ').rstrip(';').split('; ')])
            if 'font-family' in spanstyle:
                spanfamily = spanstyle['font-family'].strip("'")
                if spanfamily in pdf.getAvailableFonts():
                    spanfont = spanfamily
                elif spanfamily in additionnal_fonts:
                    spanfont = spanfamily
                if spanfamily != spanfont:
                    print("Using font family = '%s' (wanted %s)" % (spanfont, spanfamily))
            spanfs = bodyfs
            if 'font-size' in spanstyle:
                spanfs = int(spanstyle['font-size'].strip("pt"))
            pdf.setFont(spanfont, spanfs)
            
            if 'color' in spanstyle:
                color = spanstyle['color']
            pdf.setFillColor(color)

            lines = span.text.split('\n') # split the span on what used to be <br>
            lines_cnt = len(lines)
            lines_span += lines_cnt-1
            x_line = 0.0
            for line_no, line in enumerate(lines): # each line in the html span
                x_line = x_span
                y_line = -line_scale*fs_max*(line_no) + y_para + y_span
                logging.debug("Line %d/%d: |%s|" % (line_no+1, lines_cnt, line))
                texts = line.split('\t')
                paragraphStyle = ParagraphStyle(
                    name = 'Normal',
                    textColor = color,
                    fontName = spanfont, 
                    fontSize = spanfs, 
                    leading = spanfs * line_scale, 
                    alignment = TA_LEFT)
                if htmlpara.get('align') == 'center':
                    paragraphStyle.alignment = TA_CENTER
                    for text in texts:
                        #pdf.drawCentredString(0, 0.5 * f * areaHeight + y_line, line)
                        x_line = DrawStyledParagraph(pdf, text, paragraphStyle, areaHeight, areaWidth, x_line, y_line)
                elif htmlpara.get('align') == 'right':
                    paragraphStyle.alignment = TA_RIGHT
                    for text in reversed(texts):
                        logging.debug("xl: %d\tyl: %d\t(xs: %d\tys: %d\typ: %d)\tFS: %d/%d\t|%s|" % \
                            (x_line, y_line, x_span, y_span, y_para, spanfs, fs_max, text ))
                        #pdf.drawRightString(0.5 * f * areaWidth - x_line, 0.5 * f * areaHeight + y_line, text)
                        x_line = DrawStyledParagraph(pdf, text, paragraphStyle, areaHeight, areaWidth, x_line, y_line)
                else:   # left aligned
                    for text in texts:
                        logging.debug("xl: %d\tyl: %d\t(xs: %d\tys: %d\typ: %d)\tFS: %d/%d\t|%s|" % \
                            (x_line, y_line, x_span, y_span, y_para, spanfs, fs_max, text ))
                        #pdf.drawString(-0.5 * f * areaWidth + x_line, 0.5 * f * areaHeight + y_line, text)
                        x_line = DrawStyledParagraph(pdf, text, paragraphStyle, areaHeight, areaWidth, x_line, y_line)
            x_span = x_line
            if lines_cnt > 1:
                x_span = 0.0
                y_span -= line_scale*fs_max*(lines_cnt-1)
        y_para -= line_scale*fs_max*(lines_span+1)

def convertMcf(mcfname, keepDoublePages):
#Get the folder in which the .mcf file is
    mcfPathObj = Path(mcfname).resolve()    # convert it to an absolute path
    mcfBaseFolder = mcfPathObj.parent

    # parse the input mcf xml file
    mcffile = open(mcfname, 'rb')   #read file as binary, so UTF-8 encoding is preserved for xml-parser
    mcf = etree.parse(mcffile)
    mcffile.close()
    fotobook = mcf.getroot()
    if fotobook.tag != 'fotobook':
        print(mcfname + 'is not a valid mcf file. Exiting.')
        sys.exit(1)

    # find cewe folder using the original cewe_folder.txt file
    try:
        configFolderFileName = findFileInDirs('cewe_folder.txt', (mcfBaseFolder,  os.path.curdir))
        cewe_file = open(configFolderFileName, 'r')
        cewe_folder = cewe_file.read().strip()
        cewe_file.close()
        baseBackgroundLocations = getBaseBackgroundLocations(cewe_folder)
        backgroundLocations = baseBackgroundLocations;
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
            xbg = defaultConfigSection.get('extraBackgroundFolders','').strip() # comma separated list of folders
            backgroundLocations = baseBackgroundLocations + tuple(xbg.split(","))

    bg_notfound = set([])

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
            print("Successfully registered '%s' from '%s'" % (n, additionnal_fonts[n]))
        except:
            print("Failed to register font '%s' (from %s)" % (n, additionnal_fonts[n]))


    # extract properties
    articleConfigElement = fotobook.find('articleConfig')
    pagenum = int(articleConfigElement.get('normalpages')) + 2
    imagedir = fotobook.get('imagedir')


    def getPageElementForPageNumber(pageNumber):
        return fotobook.find("./page[@pagenr='{}']".format(floor(2 * (pageNumber / 2)),'d'))

    for n in range(pagenum):
        try:
            if (n == 0) or (n == pagenum - 1):
                pn = 0
                page = [i for i in
                    fotobook.findall("./page[@pagenr='0'][@type='FULLCOVER']") +
                    fotobook.findall("./page[@pagenr='0'][@type='fullcover']")
                    if (i.find("./area") != None)][0]
                oddpage = (n == 0)
                pagetype = 'cover'
            elif n == 1:
                pn = 1
                page = [i for i in
                    fotobook.findall("./page[@pagenr='0'][@type='EMPTY']") +
                    fotobook.findall("./page[@pagenr='0'][@type='emptypage']")
                    if (i.find("./area") != None)][0]
                oddpage = True
                pagetype = 'singleside'
            else:
                pn = n
                oddpage = (pn % 2) == 1
                page = getPageElementForPageNumber(n)
                pagetype = 'normal'

            if (page != None):
                print('parsing page', page.get('pagenr'),' of ', pagenum)

                bundlesize = page.find("./bundlesize")
                if (bundlesize != None):
                    pw = float(bundlesize.get('width'))
                    ph = float(bundlesize.get('height'))

                    #reduce the page width to a single page width, if we want to have single pages.
                    if not keepDoublePages:
                        pw = pw / 2
                else:
                    # Assume A4 page size
                    pw = 2100
                    ph = 2970
                pdf.setPageSize((f * pw, f * ph))

                # process background
                designElementIDs = page.findall('designElementIDs')
                if designElementIDs != None and len(designElementIDs) > 0:
                    designElementID = designElementIDs[0]
                    if (designElementID != None and cewe_folder != None and
                            designElementID.get('background') != None):
                        bg = designElementID.get('background')
                        try:
                            bgpath = findFileInDirs([bg + '.bmp', bg + '.webp', bg + '.jpg'], backgroundLocations)
                            areaWidth = pw*2
                            if keepDoublePages:
                                areaWidth = pw
                            areaHeight = ph
                            if pagetype != 'singleside' and oddpage and not keepDoublePages:
                                ax = -areaWidth / 2.
                            else:
                                ax = 0
                            imObj = PIL.Image.open(bgpath) # webp doesn't work with PIL.Image.open in Anaconda 5.3.0 on Win10
                            #create a in-memory byte array of the image file
                            im = bytes()
                            memFileHandle = BytesIO(im)
                            imObj = imObj.convert("RGB")
                            imObj.save(memFileHandle,'jpeg')
                            memFileHandle.seek(0)

                            #im = imread(bgpath) #does not work with 1-bit images
                            pdf.drawImage(ImageReader(memFileHandle), f * ax, 0, width=f * areaWidth, height=f * areaHeight)
                            #pdf.drawImage(ImageReader(bgpath), f * ax, 0, width=f * aw, height=f * ah)
                        except Exception as ex:
                            if bgpath not in bg_notfound:
                                print('cannot find background or error when adding to pdf', bgpath, '\n', ex.args[0])
                                exc_type, exc_obj, exc_tb = sys.exc_info()
                                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                                print('', (exc_type, fname, exc_tb.tb_lineno))
                            bg_notfound.add(bgpath)

                #all elements (images, text,..) for even and odd pages are defined on the even page element!
                if keepDoublePages and oddpage == 1 and pagetype =='normal':
                    continue    #if we are in double-page mode, all the images are already drawn by the even pages.
                else:
                    #switch pack to the page element for the even page to get the elements
                    if pagetype=='normal' and oddpage == 1:
                        page = getPageElementForPageNumber(2*floor(pn/2))

                    for area in page.findall('area'):
                        areaPos = area.find('position')
                        areaLeft = float(areaPos.get('left').replace(',', '.'))
                        #old python 2 code: aleft = float(area.get('left').replace(',', '.'))
                        if pagetype != 'singleside' or len(area.findall('imagebackground')) == 0:
                            if oddpage and not keepDoublePages:
                                # shift double-page content from other page
                                areaLeft -= pw
                        areaTop = float(areaPos.get('top').replace(',', '.'))
                        areaWidth = float(areaPos.get('width').replace(',', '.'))
                        areaHeight = float(areaPos.get('height').replace(',', '.'))
                        areaRot = float(areaPos.get('rotation'))

                        #check if the image is on current page at all
                        if pagetype=='normal' and not keepDoublePages:
                            if oddpage:
                                if (areaLeft+areaWidth) < 0:  #the right edge of image is beyond the left page border
                                    continue
                            else:
                                if areaLeft > pw:   #the left image edge is beyond the right page border.
                                    continue

                        #center positions
                        cx = areaLeft + 0.5 * areaWidth
                        cy = ph - (areaTop + 0.5 * areaHeight)

                        transx = f * cx
                        transy = f * cy

                        # process images
                        for image in area.findall('imagebackground') + area.findall('image'):
                            # open raw image file
                            if image.get('filename') == None:
                                continue
                            imagepath = os.path.join(mcfBaseFolder, imagedir, image.get('filename'))
                            #the layout software copies the images to another collection folder
                            imagepath=imagepath.replace('safecontainer:/','')
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
                            #get the cutout position and scale
                            imleft = float(image.find('cutout').get('left').replace(',', '.'))
                            imtop = float(image.find('cutout').get('top').replace(',', '.'))
                            imageWidth_px, imageHeight_px = im.size
                            imsc = float(image.find('cutout').get('scale'))

                            #without cropping: to get from a image pixel width to the areaWidth in .mcf-units, the image pixel width is multiplied by the scale factor.
                            #to get from .mcf units are divided by the scale factor to get to image pixel units.

                            # crop image
                            im = im.crop((int(0.5 - imleft/imsc),
                                int(0.5 - imtop/imsc),
                                int(0.5 - imleft/imsc + areaWidth / imsc),
                                int(0.5 - imtop/imsc + areaHeight / imsc)))


                            # scale image
                            # re-scale the image if it is much bigger than final resolution in PDF
                            #set desired DPI based on where the image is used. The background gets a lower DPI.
                            if image.tag == 'imagebackground' and pagetype != 'cover':
                                res = bg_res
                            else:
                                res = image_res
                            new_w = int(0.5 + areaWidth * res / 254.)           #254 -> convert from mcf unit (0.1mm) to inch (1 inch = 25.4 mm)
                            new_h = int(0.5 + areaHeight * res / 254.)
                            factor = sqrt(new_w * new_h / float(im.size[0] * im.size[1]))
                            if factor <= 0.8:
                                im = im.resize((new_w, new_h), PIL.Image.ANTIALIAS)
                            im.load()


                            # re-compress image
                            jpeg = tempfile.NamedTemporaryFile()
                            jpeg.close()    # we need to close the temporary file, because otherwise the call to im.save will fail on Windows.
                            if im.mode == 'RGBA' or im.mode == 'P':
                                im.save(jpeg.name, "PNG")
                            else:
                                im.save(jpeg.name, "JPEG", quality=image_quality)

                            # place image
                            print('image', image.get('filename'))
                            pdf.translate(img_transx, transy)
                            pdf.rotate(-areaRot)
                            pdf.drawImage(ImageReader(jpeg.name),
                                f * -0.5 * areaWidth, f * -0.5 * areaHeight,
                                width = f * areaWidth, height = f * areaHeight, mask='auto')
                            pdf.rotate(areaRot)
                            pdf.translate(-img_transx, -transy)

                            #we now have temporary file, that we need to delete after pdf creation
                            tempFileList.append(jpeg.name)
                            #we can not delete now, because file is opened by pdf library
                            ##try to delete the temporary file again. Needed for Windows
                            #if os.path.exists(jpeg.name):
                            #    os.remove(jpeg.name)

                        # process text
                        for text in area.findall('text'):
                            pdf.translate(transx, transy)
                            pdf.rotate(-areaRot)
                            DrawText(pdf, text, areaHeight, areaWidth, additionnal_fonts)
                            pdf.rotate(areaRot)
                            pdf.translate(-transx, -transy)

            # finish the page
            pdf.showPage()

        except Exception as ex:
            # if one page fails: continue with next one
            print('error on page %i:' % (n, ),'\n', ex.args[0])
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print('', (exc_type, fname, exc_tb.tb_lineno))

    # save final output pdf
    pdf.save()

    pdf = []

    #clean up temp files
    for tmpFileName in tempFileList:
        if os.path.exists(tmpFileName):
           os.remove(tmpFileName)
    return True

if __name__ == '__main__':
    #only executed when this file is run directly.
    #we need trick to have both: default and fixed formats.
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

    #if inputFile name is still empty, we have to throw an error
    if args.inputFile is None:
        parser.parse_args(['-h'])
        sys.exit(1)

    #if we have a file name, let's convert it
    resultFlag = convertMcf(args.inputFile, args.keepDoublePages)
