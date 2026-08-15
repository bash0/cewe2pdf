# This test needs to be in its own directory, so it can have it's own cwew2pdf.ini.
# Also we can store the asset files here.

# Test the default substitution for missing fonts

# Bootstrap the project root so this test can also run directly.
import os, os.path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)
from datetime import datetime
from pikepdf import Pdf

from compare_pdf import ComparePDF, ShowDiffsStyle # type: ignore
from cewe2pdf import convertMcf # type: ignore

from testutils import getLatestResultFile


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
    albumFolderBasename = 'testTextBox'
    albumBasename = "testTextBox"
    inFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", f'{albumBasename}.mcf'))
    yyyymmdd = datetime.today().strftime("%Y%m%d")
    return albumFolderBasename,albumBasename,inFile,yyyymmdd

def test_testfontsubstitution(main=False):
    albumFolderBasename, albumBasename, inFile, yyyymmdd = defineCommonVariables()
    styleid = "S"
    if (main):
        # use an undated output file name when running as main rather than via pytest
        outFileBasename = f'{albumBasename}.mcf.pdf'
    else:
        outFileBasename = f'{albumBasename}.mcf.{yyyymmdd}{styleid}.pdf'
    outFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", outFileBasename))
    latestResultFile = getLatestResultFile(albumFolderBasename, f"*{styleid}.pdf")
    tryToBuildBook(inFile, outFile, latestResultFile, False, 28)


if __name__ == '__main__':
    # When running this test directly we will normally not have IGNORELOCALFONTS set, so the system
    # fonts will be registered and could be accessed. When the tests are run by a full pytest
    # discovery, IGNORELOCALFONTS is set to 1, so that the system fonts are not registered (not
    # on the developer machine nor on the github servers) so the direct run result and the full 
    # pytest run result will not be the same.
    test_testfontsubstitution(main=True)
