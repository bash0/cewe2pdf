# This test needs to be in its own directory, so it can have it's own cwew2pdf.ini.
# Also we can store the asset files here.

# Test rendering when page one is empty

#if you run this file directly, it won't have access to parent folder, so add it to python path
import os, os.path
import sys

from numpy import test
sys.path.append('..')
sys.path.append('.')
sys.path.append('tests/compare-pdf/compare_pdf') # used if compare_pdf has not been pip installed

# Parse the mcf file to create variations using xml.dom.minidom rather than xml.etree.ElementTree
# Copilot suggested this choice because etree is bad at parsing CDATA
from xml.dom.minidom import parse, Document

from datetime import datetime
from pathlib import Path
from pikepdf import Pdf

from compare_pdf import ComparePDF, ShowDiffsStyle # type: ignore
from cewe2pdf import convertMcf # type: ignore
from extraLoggers import mustsee # type: ignore

from testutils import getLatestResultFile, getOutFileBasename, runModifications


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
    readPdf.close()

    if latestResultFile is not None:
        # compare our result with the latest one
        print(f"Compare {outFile} with {latestResultFile}")
        files = [outFile, latestResultFile]
        compare = ComparePDF(files, ShowDiffsStyle.Nothing)
        result = compare.compare()
        compare.cleanup() # to force closure of the files and allow us to delete them
        assert result, "Pixel comparison failed"
    else:
        print(f"No result file to compare with {os.path.basename(outFile)}")
        result = False # we keep the result file so it can become an approved version

    return result


def defineCommonVariables():
    albumFolderBasename = 'testIndex'
    albumBasename = "test_index"
    inFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", f'{albumBasename}.mcf'))
    yyyymmdd = datetime.today().strftime("%Y%m%d")
    return albumFolderBasename,albumBasename,inFile,yyyymmdd

def checkModifiedMcfVersions(main, infile, attribute_modifications, albumFolderBasename, albumBasename):
    # Parse the mcf file and find the elements on which we want to do attribute modication variation
    dom = parse(infile)
    elementName = "pagenumbering"
    elementToVary = dom.getElementsByTagName(elementName)[0]
    if elementToVary is None:
        raise ValueError(f"No <{elementName}> element found in {infile}")
    # Run attribute modification variations on the element found
    runModifications(main, tryToBuildBook, albumFolderBasename, albumBasename, dom, attribute_modifications, elementToVary)

def test_index(main=False):
    albumFolderBasename, albumBasename, inFile, yyyymmdd = defineCommonVariables()

    styleid = "S"
    outFileBasename = getOutFileBasename(main, albumBasename, yyyymmdd, styleid)
    outFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", outFileBasename))
    latestResultFile = getLatestResultFile(albumFolderBasename, f"*{styleid}.pdf")
    tryToBuildBook(inFile, outFile, latestResultFile, False, 29)

if __name__ == '__main__':
    #only executed when this file is run directly.
    test_index(main=True)
