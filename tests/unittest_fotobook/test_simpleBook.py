#SPDX-License-Identifier: GPL-3.0-only

#author(s): BarchSteel
#Copyright (c) 2019, 2020 by BarchSteel

# test to convert a simple mcf to pdf
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

assertOnPixelComparisonFailure = True # set false to avoid the assertion on pixel-by-pixel comparison failure

def tryToBuildBook(inFile, outFile, latestResultFile, keepDoublePages, expectedPages):
    if os.path.exists(outFile) == True:
        os.remove(outFile)
    assert os.path.exists(outFile) == False
    convertMcf(inFile, keepDoublePages, outputFileName=outFile) # you might try pageNumbers=[0,2,5,6,7,26]
    assert Path(outFile).exists() == True

    # check the pdf contents
    readPdf = Pdf.open(outFile)
    numPages =  len(readPdf.pages)
    assert numPages == expectedPages, f"Expected {expectedPages} pages, found {numPages}"

    if latestResultFile is not None:
        # compare our result with the latest one. Pixel comparison isn't brilliant for this particular
        # test which has become a test bed for specific issues, and as such may rely on exactly the
        # correct fonts and other surroundings for the platform where the issue arose. BUT, even when
        # fonts are substituted or are missing completely (Segoe UI Symbol, for example) the pixel
        # comparison does allow us to be sure that the newly checked in (but potentially visually
        # incorrect) version is still equal to the previous version. If we have only changed the code
        # and not updated the unittest fotobook, we can verify that the code change has not broken
        # anything. When we update the unittest fotobook with a new "test demonstration" then of course
        # we must provide a new result file. As such, the sequence of versions here gives us a decent
        # idea of what we specifically tested for over time.
        print(f"Compare {outFile} with {latestResultFile}")
        files = [outFile, latestResultFile]
        compare = ComparePDF(files, ShowDiffsStyle.Nothing)
        result = compare.compare()
        if assertOnPixelComparisonFailure:
            assert result, "Pixel comparison failed"
    else:
        print(f"No result file to compare with")

    #os.remove(outFile)


def runtest(main, albumFolderBasename, albumBasename, mcfSuffix, styleid, keepDoublePages, expectedPages):
    inFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", f'{albumBasename}.{mcfSuffix}'))
    yyyymmdd = datetime.today().strftime("%Y%m%d")
    if (main):
        # use an undated output file name when running as main rather than via pytest
        outFileBasename = f'{albumBasename}.{mcfSuffix}.{styleid}.pdf'
    else:
        outFileBasename = f'{albumBasename}.{mcfSuffix}.{yyyymmdd}{styleid}.pdf'
    outFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", outFileBasename))
    latestResultFile = getLatestResultFile(albumFolderBasename, f"*{mcfSuffix}.[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]{styleid}.pdf")
    tryToBuildBook(inFile, outFile, latestResultFile, keepDoublePages, expectedPages)


def test_simpleBookSinglePage(main=False):
    runtest(main, 'unittest_fotobook', "unittest_fotobook", "mcf", "S", False, 28)

# You can uncomment these tests to also run different output variants, but basically
#   this test is used to test the content of the pages and not the layout.
#
# def test_simpleBookDoublePage(main=False):
#     runtest(main, 'unittest_fotobook', "unittest_fotobook", "mcf", "D", True, 15)
#
# def test_simpleBookSinglePageMcfx(main=False):
#     runtest(main, 'unittest_fotobook', "unittest_fotobook", "mcfx", "S", False, 28)


if __name__ == '__main__':
    # only executed when this file is run directly rather than by
    # pytest finding the test_ methods

    # Avoid the assertion on pixel failure for non pytest execution because
    # normally this entrypoint will be used when doing manual testing in a local
    # environment with correct local fonts, etc. The assert is basically only
    # interesting when pytest is running the full set of automated tests in
    # the github environment (or here, prior to commit, with runAllTests.py)
    assertOnPixelComparisonFailure = False

    test_simpleBookSinglePage(main=True)

    #test_simpleBookDoublePage(main=True)
    #test_simpleBookSinglePageMcfx(main=True)
