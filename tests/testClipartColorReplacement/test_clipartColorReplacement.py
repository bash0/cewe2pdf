# This test needs to be in its own directory, so it can have it's own cwew2pdf.ini.
# Also we can store the asset files here.

# Test the clipart rendering with passepartout frame recoloring

#if you run this file directly, it won't have access to parent folder, so add it to python path
import sys
sys.path.append('..')
sys.path.append('.')
sys.path.append('tests/compare-pdf/compare_pdf') # used if compare_pdf has not been pip installed

import os, os.path
import glob

from pathlib import Path
from pikepdf import Pdf

from compare_pdf import ComparePDF, ShowDiffsStyle # type: ignore
from cewe2pdf import convertMcf # type: ignore

def tryToBuildBook(latestResultFile, keepDoublePages, expectedPages):
    inFile = str(Path(Path.cwd(), 'tests', 'testClipartColorReplacement', 'test_clipart_colorreplacement.mcf'))
    outFile = str(Path(Path.cwd(), 'tests', 'testClipartColorReplacement', 'test_clipart_colorreplacement.mcf.pdf'))
    if os.path.exists(outFile) == True:
        os.remove(outFile)
    assert os.path.exists(outFile) == False
    convertMcf(inFile, keepDoublePages)
    assert Path(outFile).exists() == True

    #check the pdf contents
    # we could also test more sophisticated things, like colors or compare images.
    readPdf = Pdf.open(outFile)
    numPages =  len(readPdf.pages)
    assert numPages == expectedPages, f"Expected {expectedPages} pages, found {numPages}"

    if latestResultFile is not None:
        # compare our result with the latest one
        print(f"Compare {outFile} with {latestResultFile}")
        files = [outFile, latestResultFile]
        compare = ComparePDF(files, ShowDiffsStyle.Nothing)
        result = compare.compare()
        assert result, "Pixel comparison failed"
    else:
        print(f"No result file to compare with")

    #os.remove(outFile)


def getLatestResultFile(pattern : str)-> str:
    resultpdfpattern = str(Path(Path.cwd(), 'tests', 'testClipartColorReplacement', 'previous_result_pdfs', pattern))
    resultpdffiles = glob.glob(resultpdfpattern)
    resultpdffiles.sort(key=os.path.getmtime, reverse=True)
    return resultpdffiles[0] if len(resultpdffiles) > 0 else None


def test_testClipartColorReplacement():
    latestResultFile = getLatestResultFile("*.pdf")
    tryToBuildBook(latestResultFile, False, 28)


if __name__ == '__main__':
    #only executed when this file is run directly.
    test_testClipartColorReplacement()
