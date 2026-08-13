#SPDX-License-Identifier: GPL-3.0-only

#author(s): BarchSteel
#Copyright (c) 2020 by BarchSteel

# This test needs to be in its own directory, so it can have it's own cwew2pdf.ini with
# with an invalid entry to test the error handling.

# test what happens when a font file does not exist.
# if the font is missing, the page where it was used should still exist.

# Bootstrap the project root so this test can also run directly.
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)
import os, os.path
from pikepdf import Pdf


from cewe2pdf import convertMcf

def tryToBuildBook(keepDoublePages):
    inFile = str(Path(Path.cwd(), 'tests', 'testFontDoesNotExist', 'testFontDoesNotExist.mcf'))
    outFile = str(Path(Path.cwd(), 'tests', 'testFontDoesNotExist', 'testFontDoesNotExist.mcf.pdf'))
    if os.path.exists(outFile) == True:
        os.remove(outFile)
    assert os.path.exists(outFile) == False
    convertMcf(inFile, keepDoublePages)
    assert Path(outFile).exists() == True

    #check the pdf contents
    readPdf = Pdf.open(outFile)
    numPages =  len(readPdf.pages)
    assert numPages == 6, f"Expected 6 pages (4 normal plus 2 covers), found {numPages}"

    #os.remove(outFile)

def test_testFontDoesNotExist():
    tryToBuildBook(False)

if __name__ == '__main__':
    #only executed when this file is run directly.
    test_testFontDoesNotExist()
