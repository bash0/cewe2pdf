#!/usr/bin/env python
# -*- coding: utf8 -*-


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


#### settings ####
image_res = 150 # dpi
bg_res = 100 # dpi
image_quality = 86 # 0=worst, 100=best
##################


# definitions
formats = {"ALB82": reportlab.lib.pagesizes.A4} # add other page sizes here
f = 72. / 254. # convert from mcf (unit=0.1mm) to reportlab (unit=inch/72)


def autorot(im):
    if im.format != 'JPEG':
        return im
    exifdict = im._getexif()
    if exifdict != None and 274 in exifdict.keys():
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

    print 'Could not find %s in %s paths' % (filename, ', '.join(paths))
    raise ValueError('Could not find %s in %s paths' % (filename, ', '.join(paths)))

# determine filename
if len(sys.argv) > 1:
    mcfname = sys.argv[1]
else:
    fnames = [i for i in os.listdir('.') if i.endswith('.mcf')]
    if len(fnames) > 0:
        mcfname = fnames[0]
    else:
        print "no mcf file found or specified"
        sys.exit(1)


# parse the input mcf xml file
mcffile = open(mcfname, 'r')
mcf = etree.parse(mcffile)
mcffile.close()
fotobook = mcf.getroot()
if fotobook.tag != 'fotobook':
    print mcfname + 'is not a valid mcf file. Exiting.'
    sys.exit(1)


# find cewe folder
try:
    cewe_file = open('cewe_folder.txt', 'r')
    cewe_folder = cewe_file.read().strip()
    cewe_file.close()
except:
    print 'cannot find cewe installation folder in cewe_folder.txt'
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
    print 'cannot find additionnal fonts (define them in additionnal_fonts.txt)'
    print 'Content example:'
    print 'Vera = /tmp/vera.ttf'
    print 'Separator is " = " (space equal space)'


# create pdf
pagesize = reportlab.lib.pagesizes.A4
if formats.has_key(fotobook.get('productname')):
    pagesize = formats[fotobook.get('productname')]
pdf = canvas.Canvas(mcfname + '.pdf', pagesize=pagesize)

# Add additionnal fonts
for n in additionnal_fonts:
    try:
        pdfmetrics.registerFont(TTFont(n, additionnal_fonts[n]))
        print "Successfully registered '%s' from '%s'" % (n, additionnal_fonts[n])
    except:
        print "Failed to register font '%s' (from %s)" % (n, additionnal_fonts[n])


# extract properties
pagenum = int(fotobook.get('normalpages')) + 2
imagedir = fotobook.get('imagedir')


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
            page = fotobook.find("./page[@pagenr='{}']".format(2 * (pn / 2)))
            oddpage = (pn % 2) == 1
            pagetype = 'normal'

        if (page != None):
            print 'parsing page', page.get('pagenr')
            
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
                        bgpath = findFileInDirs(bg + '.jpg', (
                            os.path.join(cewe_folder, 'Resources', 'photofun', 'backgrounds'),
                            os.path.join(cewe_folder, 'Resources', 'photofun', 'backgrounds', 'einfarbige'),
                            os.path.join(cewe_folder, 'Resources', 'photofun', 'backgrounds', 'multicolor'),
                            ))
                        aw = pw*2
                        ah = ph
                        if pagetype != 'singleside' and oddpage:
                            ax = -aw / 2.
                        else:
                            ax = 0
                        #im = PIL.Image.open(bgpath)
                        pdf.drawImage(ImageReader(bgpath),
                            f * ax, 0, width=f * aw, height=f * ah)
                    except:
                        if bgpath not in bg_notfound:
                            print 'cannot find background', bgpath
                        bg_notfound.add(bgpath)
            
            
            for area in page.findall('area'):
                aleft = float(area.get('left').replace(',', '.'))
                if pagetype != 'singleside' or len(area.findall('imagebackground')) == 0:
                    if oddpage:
                        # shift double-page content from other page
                        aleft -= pw
                atop = float(area.get('top').replace(',', '.'))
                aw = float(area.get('width').replace(',', '.'))
                ah = float(area.get('height').replace(',', '.'))
                arot = float(area.get('rotation'))
                
                cx = aleft + 0.5 * aw
                cy = ph - (atop + 0.5 * ah)
                                
                transx = f * cx
                transy = f * cy
                
                
                # process images
                for image in area.findall('imagebackground') + area.findall('image'):
                    # open raw image file
                    if image.get('filename') == None:
                        continue
                    imagepath = os.path.join(os.getcwd(),
                        imagedir, image.get('filename'))
                    im = PIL.Image.open(imagepath)
                    
		    if image.get('backgroundPosition') == 'RIGHT_OR_BOTTOM':
		        # display on the right page
		        img_transx = transx + f * pw
		    else:
		        img_transx = transx
                    
                    # correct for exif rotation
                    im = autorot(im)
                    
                    imleft = float(image.get('left').replace(',', '.'))
                    imtop = float(image.get('top').replace(',', '.'))
                    imw, imh = im.size
                    imsc = float(image.get('scale'))
                    
                    
                    # crop image
                    im = im.crop((int(0.5 - imleft),
                        int(0.5 - imtop),
                        int(0.5 - imleft + aw / imsc),
                        int(0.5 - imtop + ah / imsc)))
                    
                    
                    # scale image
                    if image.tag == 'imagebackground' and pagetype != 'cover':
                        res = bg_res
                    else:
                        res = image_res
                    new_w = int(0.5 + aw * res / 254.)
                    new_h = int(0.5 + ah * res / 254.)
                    factor = sqrt(new_w * new_h / float(im.size[0] * im.size[1]))
                    if factor <= 0.8:
                        im = im.resize((new_w, new_h), PIL.Image.ANTIALIAS)
                    im.load()
                    
                    
                    # compress image
                    jpeg = tempfile.NamedTemporaryFile()
		    if im.mode == 'RGBA':
                    	im.save(jpeg.name, "PNG")
                    else:
                        im.save(jpeg.name, "JPEG", quality=image_quality)
                    
                    
                    # place image                
                    print 'image', image.get('filename')
                    pdf.translate(img_transx, transy)
                    pdf.rotate(-arot)
                    pdf.drawImage(ImageReader(jpeg.name),
                        f * -0.5 * aw, f * -0.5 * ah,
                        width=f * aw, height=f * ah, mask='auto')
                    pdf.rotate(arot)
                    pdf.translate(-img_transx, -transy)
                
                
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
                    pdf.rotate(-arot)
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

                            if 'font-size' in style:
                                fs = int(style['font-size'].strip()[:-2])
                                if 'color' in style:
                                    color = style['color']
                            if spanfamily != spanfont:
                                print "Using font family = '%s' (wanted %s)" % (spanfont, spanfamily)
                            pdf.setFont(spanfont, fs)
                            pdf.setFillColor(color)
                            if p.get('align') == 'center':
                                pdf.drawCentredString(0,
                                    0.5 * f * ah + y_p -1.3*fs, span.text)
                            elif p.get('align') == 'right':
                                pdf.drawRightString(0.5 * f * aw,
                                    0.5 * f * ah + y_p -1.3*fs, span.text)
                            else:
                                pdf.drawString(-0.5 * f * aw,
                                    0.5 * f * ah + y_p -1.3*fs, span.text)
                        y_p -= 1.3*fs
                    pdf.rotate(arot)
                    pdf.translate(-transx, -transy)

        # finish the page
        pdf.showPage()
    
    except Exception as ex:
        # if one page fails: continue with next one
        print 'error on page %i:' % (n, )
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print '', (exc_type, fname, exc_tb.tb_lineno)

# save final output pdf
pdf.save()

