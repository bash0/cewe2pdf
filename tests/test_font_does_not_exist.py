#SPDX-License-Identifier: GPL-3.0-only

#author(s): BarchSteel
#Copyright (c) 2020 by BarchSteel

# test what happens when a font file does not exist.
# if the font is missing, the page where it was used should still exist.

#if you run this file directly, it won't have access to parent folder, so add it to python path
import sys
sys.path.append('..')
sys.path.append('.')
from pathlib import Path
import os, os.path
from pdfrw import PdfReader


from cewe2pdf import convertMcf

def tryToBuildBook(keepDoublePages):
    inFile = str(Path(Path.cwd(), 'tests', 'test_font_does_not_exist.mcf'))
    outFile = str(Path(Path.cwd(), 'tests', 'test_font_does_not_exist.mcf.pdf'))
    if os.path.exists(outFile) == True:
        os.remove(outFile)
    assert os.path.exists(outFile) == False
    convertMcf(inFile, keepDoublePages)
    assert Path(outFile).exists() == True

    #check the pdf contents
    readerObj = PdfReader(outFile)
    numPages =  len(readerObj.pages)
    assert numPages == 6

    #os.remove(outFile)

def test_testFontDoesNotExist():
    tryToBuildBook(False)

if __name__ == '__main__':
    #only executed when this file is run directly.
    test_testFontDoesNotExist()