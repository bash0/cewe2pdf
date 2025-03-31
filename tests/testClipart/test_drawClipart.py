#SPDX-License-Identifier: GPL-3.0-only

#author(s): BarchSteel
#Copyright (c) 2020 by BarchSteel

# This test needs to be in its own directory, so it can have it's own cwew2pdf.ini.
# Also we can store the asset files here.

# Test the clipart rendering

#if you run this file directly, it won't have access to parent folder, so add it to python path
import sys
sys.path.append('..')
sys.path.append('.')
from pathlib import Path
import os, os.path
from pikepdf import Pdf, PdfImage

from cewe2pdf import convertMcf

def tryToBuildBook(keepDoublePages):
    inFile = str(Path(Path.cwd(), 'tests', 'testClipart', 'testClipart.mcf'))
    outFile = str(Path(Path.cwd(), 'tests', 'testClipart', 'testClipart.mcf.pdf'))
    if os.path.exists(outFile) == True:
        os.remove(outFile)
    assert os.path.exists(outFile) == False
    convertMcf(inFile, keepDoublePages)
    assert Path(outFile).exists() == True

    #check the pdf contents
    # we could also test more sophisticated things, like colors or compare images.
    readPdf = Pdf.open(outFile)
    numPages =  len(readPdf.pages)
    assert numPages == 6, f"Expected 6 pages (4 normal plus 2 covers), found {numPages}"

    page = readPdf.pages[0]
    imagesizes = [(412,385),(412,288),(412,423),(219,225),(10,10)]
    imagekeys = list(page.images.keys())
    imagecount = len(imagekeys)
    # the test album front cover has 5 images. My interpretation (aided by pdfexplorer) is
    # 1 clipart for the background, a 10x10 image
    # 2 cliparts each used twice (same size, different rotation) so they count just 2
    # 1 clipart used once (the blue square with the white circle centre, large)
    # 1 clipart used three times (the same blue square as above, but smaller and used in 3 different rotations)
    assert imagecount == 5, f"Expected 5 images on front cover, found {imagecount}"
    for imk in imagekeys:
        coverimage = page.images[imk]
        coverpdfimage = PdfImage(coverimage)
        size = (coverpdfimage.width,coverpdfimage.height)
        assert size in imagesizes, f"Image sized {size} not expected"

    #os.remove(outFile)

def test_testDrawClipart():
    tryToBuildBook(False)

if __name__ == '__main__':
    #only executed when this file is run directly.
    test_testDrawClipart()