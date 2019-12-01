#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Create pdf files from CEWE .mcf photo books (cewe-fotobuch)
version 0.1 (Nov. 2014)

This script reads CEWE .mcf files using the lxml library
and compiles a pdf file using the reportlab python pdf library.
Execute from same path as .mcf file!

Only basic elements such as images and text are supported.
The feature support is neither complete nor fully correct.
Results may be wrong, incomplete or not produced at all.
This script doesn't work according to the original format
specification but according to estimated meaning.
Feel free to improve!

The script was tested to run with A4 books from CEWE programmversion 5001003

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
import sys
from lxml import etree
import tempfile
from math import *

from reportlab.pdfgen import canvas
import reportlab.lib.pagesizes
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import PIL
from PIL.ExifTags import TAGS
from io import BytesIO
from pathlib import Path


#### settings ####
image_quality = 86 # 0=worst, 100=best
image_res = 150 # dpi
bg_res = 100 # dpi      
##################

#.mcf units are 0.1 mm

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

def findFileInDirs(filename, paths):
    for p in paths:
        testPath = os.path.join(p, filename)
        if os.path.exists(testPath):
            return testPath

    print('Could not find %s in %s paths' % (filename, ', '.join(paths)))
    raise ValueError('Could not find %s in %s paths' % (filename, ', '.join(paths)))

def convertMcf(mcfname):
#Get the folder in which the .mcf file is
    mcfPathObj = Path(mcfname).resolve()    # convert it to an absolute path
    mcfBaseFolder = mcfPathObj.parent
    
    # parse the input mcf xml file
    mcffile = open(mcfname, 'r')
    mcf = etree.parse(mcffile)
    mcffile.close()
    fotobook = mcf.getroot()
    if fotobook.tag != 'fotobook':
        print(mcfname + 'is not a valid mcf file. Exiting.')
        sys.exit(1)
    
    
    # find cewe folder
    try:
        cewe_file = open('cewe_folder.txt', 'r')
        cewe_folder = cewe_file.read().strip()
        cewe_file.close()
    except:
        print('cannot find cewe installation folder in cewe_folder.txt')
        cewe_folder = None
    bg_notfound = set([])
    
    # Load additionnal fonts
    additionnal_fonts = {}
    try:
        with open('additionnal_fonts.txt', 'r') as fp:
            for line in fp:
                p = line.split(" = ", 1)
                additionnal_fonts[p[0]] = p[1].strip()
            fp.close()
    except:
        print('cannot find additionnal fonts (define them in additionnal_fonts.txt)')
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
                        pw = float(bundlesize.get('width')) / 2.0
                        ph = float(bundlesize.get('height'))
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
                            bgpath = findFileInDirs(bg + '.bmp', (
                                os.path.join(cewe_folder, 'Resources', 'photofun', 'backgrounds'),
                                os.path.join(cewe_folder, 'Resources', 'photofun', 'backgrounds', 'einfarbige'),
                                os.path.join(cewe_folder, 'Resources', 'photofun', 'backgrounds', 'multicolor'),
                                ))
                            areaWidth = pw*2
                            areaHeight = ph
                            if pagetype != 'singleside' and oddpage:
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
                #switch pack to the page element for the even page to get the elements
                if pagetype=='normal' and oddpage == 1:
                    page = getPageElementForPageNumber(2*floor(pn/2))
    
                for area in page.findall('area'):
                    areaPos = area.find('position')
                    areaLeft = float(areaPos.get('left').replace(',', '.'))
                    #old python 2 code: aleft = float(area.get('left').replace(',', '.'))
                    if pagetype != 'singleside' or len(area.findall('imagebackground')) == 0:
                        if oddpage:
                            # shift double-page content from other page
                            areaLeft -= pw
                    areaTop = float(areaPos.get('top').replace(',', '.'))
                    areaWidth = float(areaPos.get('width').replace(',', '.'))
                    areaHeight = float(areaPos.get('height').replace(',', '.'))
                    areaRot = float(areaPos.get('rotation'))
    
                    #check if the image is on current page at all
                    if pagetype=='normal':
                        if oddpage:
                            if (areaLeft+areaWidth) < 0:  #the right edge of image is beyond the left page border
                                continue
                        else:
                            if areaLeft > pw:   #the left image edge is beyond the right page border.
                                continue
                    
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
                                    spanfamily = style['font-family'].strip("'")
                                    if spanfamily in pdf.getAvailableFonts():
                                        spanfont = spanfamily
                                    elif spanfamily in additionnal_fonts:
                                        spanfont = spanfamily
                                    if spanfamily != spanfont:
                                        print("Using font family = '%s' (wanted %s)" % (spanfont, spanfamily))
    
                                if 'font-size' in style:
                                    fs = int(style['font-size'].strip()[:-2])
                                    if 'color' in style:
                                        color = style['color']
                                pdf.setFont(spanfont, fs)
                                pdf.setFillColor(color)
                                if p.get('align') == 'center':
                                    pdf.drawCentredString(0,
                                        0.5 * f * areaHeight + y_p -1.3*fs, span.text)
                                elif p.get('align') == 'right':
                                    pdf.drawRightString(0.5 * f * areaWidth,
                                        0.5 * f * areaHeight + y_p -1.3*fs, span.text)
                                else:
                                    pdf.drawString(-0.5 * f * areaWidth,
                                        0.5 * f * areaHeight + y_p -1.3*fs, span.text)
                            y_p -= 1.3*fs
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

    #clean up temp files
    for tmpFileName in tempFileList:
        if os.path.exists(tmpFileName):
            os.remove(tmpFileName)
    return True

if __name__ == '__main__':
    #only executed when this file is run directly.

    # determine filename
    if len(sys.argv) > 1:
        mcfname = sys.argv[1]
    else:
        fnames = [i for i in os.listdir('.') if i.endswith('.mcf')]
        if len(fnames) > 0:
            mcfname = fnames[0]
        else:
            print("no mcf file found or specified")
            sys.exit(1)

    resultFlag = convertMcf(mcfname)