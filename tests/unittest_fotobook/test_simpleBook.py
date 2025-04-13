#SPDX-License-Identifier: GPL-3.0-only

#author(s): BarchSteel
#Copyright (c) 2019, 2020 by BarchSteel

# test to convert a simple mcf to pdf
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


def runtest(albumFolderBasename, albumBasename, mcfSuffix, styleId, keepDoublePages, expectedPages):
    inFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", f'{albumBasename}.{mcfSuffix}'))
    yyyymmdd = datetime.today().strftime("%Y%m%d")
    outFileBasename = f'{albumBasename}.{mcfSuffix}.{yyyymmdd}{styleId}.pdf'
    outFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", outFileBasename))
    latestResultFile = getLatestResultFile(albumFolderBasename, f"*{mcfSuffix}.*{styleId}.pdf")
    tryToBuildBook(inFile, outFile, latestResultFile, keepDoublePages, expectedPages)


def test_simpleBookSinglePage():
    runtest('unittest_fotobook', "unittest_fotobook", "mcf", "S", False, 28)

# You can uncomment these tests to also run different output variants, but basically
#   this test is used to test the content of the pages and not the layout.
#
# def test_simpleBookDoublePage():
#     runtest('unittest_fotobook', "unittest_fotobook", "mcf", "D", True, 15)
#
# def test_simpleBookSinglePageMcfx():
#     runtest('unittest_fotobook', "unittest_fotobook", "mcfx", "S", False, 28)


if __name__ == '__main__':
    # only executed when this file is run directly rather than by
    # pytest finding the test_ methods

    # Avoid the assertion on pixel failure for non pytest execution because
    # normally this entrypoint will be used when doing manual testing in a local
    # environment with correct local fonts, etc. The assert is basically only
    # interesting when pytest is running the full set of automated tests in
    # the github environment (or here, prior to commit, with runAllTests.py)
    assertOnPixelComparisonFailure = False

    test_simpleBookSinglePage()

    #test_simpleBookDoublePage()
    #test_simpleBookSinglePageMcfx()
