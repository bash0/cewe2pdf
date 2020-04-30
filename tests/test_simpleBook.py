# test to convert a simple mcf to pdf
#if you run this file directly, it won't have access to parent folder, so add it to python path
import sys
sys.path.append('..')
sys.path.append('.')
from pathlib import Path
import os, os.path
from pdfrw import PdfReader


from cewe2pdf import convertMcf

def tryToBuildBook(keepDoublePages):
    inFile = str(Path(Path.cwd(), 'tests', 'unittest_fotobook.mcf'))
    outFile = str(Path(Path.cwd(), 'tests', 'unittest_fotobook.mcf.pdf'))
    if os.path.exists(outFile) == True:
        os.remove(outFile)
    assert os.path.exists(outFile) == False
    convertMcf(inFile, keepDoublePages)
    assert Path(outFile).exists() == True

    #check the pdf contents
    readerObj = PdfReader(outFile)
    numPages =  len(readerObj.pages)
    if keepDoublePages:
        assert numPages == 15
    else:
        assert numPages == 28

    #os.remove(outFile)

def test_simpleBookSinglePage():
    tryToBuildBook(False)

def test_simpleBookDoublePage():
    tryToBuildBook(True)

if __name__ == '__main__':
    #only executed when this file is run directly.
    test_simpleBookSinglePage()
    #test_simpleBookDoublePage();