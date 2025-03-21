#SPDX-License-Identifier: GPL-3.0-only

#author(s): BarchSteel
#Copyright (c) 2019, 2020 by BarchSteel

# test to convert a simple mcf to pdf
#if you run this file directly, it won't have access to parent folder, so add it to python path
import sys
sys.path.append('..')
sys.path.append('.')
from pathlib import Path
import os, os.path
from pikepdf import Pdf

from cewe2pdf import convertMcf

def tryToBuildBook(infilename, keepDoublePages = False):
    inFile = str(Path(Path.cwd(), 'tests', 'unittest_fotobook', infilename))
    outFile = str(Path(Path.cwd(), 'tests', 'unittest_fotobook', infilename + '.pdf'))
    if os.path.exists(outFile) == True:
        os.remove(outFile)
    assert os.path.exists(outFile) == False
    convertMcf(inFile, keepDoublePages)
    assert Path(outFile).exists() == True

    #check the pdf contents
    readPdf = Pdf.open(outFile)
    numPages =  len(readPdf.pages)
    if keepDoublePages:
        assert numPages == 15
    else:
        assert numPages == 28

    #os.remove(outFile)

def test_simpleBookDoublePage():
    tryToBuildBook('unittest_fotobook.mcf', keepDoublePages = True)

def test_simpleBookSinglePage():
    tryToBuildBook('unittest_fotobook.mcf')

def test_simpleBookSinglePageMcfx():
    tryToBuildBook('unittest_fotobook.mcfx')

if __name__ == '__main__':
    #only executed when this file is run directly.
    test_simpleBookSinglePage()
    #test_simpleBookDoublePage()