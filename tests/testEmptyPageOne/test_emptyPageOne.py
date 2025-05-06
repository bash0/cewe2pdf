# This test needs to be in its own directory, so it can have it's own cwew2pdf.ini.
# Also we can store the asset files here.

# Test rendering when page one is empty

#if you run this file directly, it won't have access to parent folder, so add it to python path
import os, os.path
import sys
sys.path.append('..')
sys.path.append('.')
sys.path.append('tests/compare-pdf/compare_pdf') # used if compare_pdf has not been pip installed

from datetime import datetime
from pathlib import Path
from pikepdf import Pdf

from compare_pdf import ComparePDF, ShowDiffsStyle # type: ignore
from cewe2pdf import convertMcf # type: ignore

from testutils import getOutFileBasename, getLatestResultFile


def tryToBuildBook(inFile, outFile, latestResultFile, keepDoublePages, expectedPages):
    if os.path.exists(outFile) == True:
        os.remove(outFile)
    assert os.path.exists(outFile) == False
    convertMcf(inFile, keepDoublePages, outputFileName=outFile)
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
    return numPages


def defineCommonVariables():
    albumFolderBasename = 'testEmptyPageOne'
    albumBasename = "test_emptyPageOne"
    inFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", f'{albumBasename}.mcf'))
    yyyymmdd = datetime.today().strftime("%Y%m%d")
    return albumFolderBasename,albumBasename,inFile,yyyymmdd

def test_testEmptyPageOne(main=False):
    albumFolderBasename, albumBasename, inFile, yyyymmdd = defineCommonVariables()
    styleid = "S"
    outFileBasename = getOutFileBasename(main, albumBasename, yyyymmdd, styleid)
    outFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", outFileBasename))
    latestResultFile = getLatestResultFile(albumFolderBasename, f"*{styleid}.pdf")
    tryToBuildBook(inFile, outFile, latestResultFile, False, 28)

    styleid = "D"
    outFileBasename = getOutFileBasename(main, albumBasename, yyyymmdd, styleid)
    outFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", outFileBasename))
    latestResultFile = getLatestResultFile(albumFolderBasename, f"*{styleid}.pdf")
    tryToBuildBook(inFile, outFile, latestResultFile, True, 15)
if __name__ == '__main__':
    #only executed when this file is run directly.
    test_testEmptyPageOne(main=True)
