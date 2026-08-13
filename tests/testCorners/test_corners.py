# This test needs to be in its own directory, so it can have it's own cwew2pdf.ini.
# Also we can store the asset files here.

# Test the corner masking

# Bootstrap the project root so this test can also run directly.
import os, os.path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)
from datetime import datetime
from xml.etree import ElementTree
from PIL import Image
from pikepdf import Pdf, PdfImage

from compare_pdf import ComparePDF, ShowDiffsStyle # type: ignore
from cewe2pdf import convertMcf # type: ignore
from corners import (CornerInfo, CornerShape, CornersInfo, applyCornerMask,
                     getCornerInfo, hasImplementedCorners) # type: ignore

from testutils import getLatestResultFile

def tryToBuildBook(inFile, outFile, latestResultFile, keepDoublePages):
    if os.path.exists(outFile) == True:
        os.remove(outFile)
    assert os.path.exists(outFile) == False
    convertMcf(inFile, keepDoublePages, outputFileName=outFile)
    assert Path(outFile).exists() == True

    #check the pdf contents
    # we could also test more sophisticated things, like colors or compare images.
    readPdf = Pdf.open(outFile)
    numPages =  len(readPdf.pages)
    assert numPages == 28, f"Expected 28 pages, found {numPages}"

    # page = readPdf.pages[0]
    # imagesizes = [(412,385),(412,288),(412,423),(219,225),(10,10)]
    # imagekeys = list(page.images.keys())
    # imagecount = len(imagekeys)
    # the test album front cover has 5 images. My interpretation (aided by pdfexplorer) is
    # 1 clipart for the background, a 10x10 image
    # 2 cliparts each used twice (same size, different rotation) so they count just 2
    # 1 clipart used once (the blue square with the white circle centre, large)
    # 1 clipart used three times (the same blue square as above, but smaller and used in 3 different rotations)
    # assert imagecount == 5, f"Expected 5 images on front cover, found {imagecount}"
    # for imk in imagekeys:
    #     coverimage = page.images[imk]
    #     coverpdfimage = PdfImage(coverimage)
    #     size = (coverpdfimage.width,coverpdfimage.height)
    #     assert size in imagesizes, f"Image sized {size} not expected"

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

def defineCommonVariables():
    albumFolderBasename = 'testCorners'
    albumBasename = "testCorners"
    inFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", f'{albumBasename}.mcf'))
    yyyymmdd = datetime.today().strftime("%Y%m%d")
    return albumFolderBasename,albumBasename,inFile,yyyymmdd


def test_recognises_unsupported_corner_shapes():
    corners = ElementTree.fromstring(
        '<corners><corner where="top-left" shape="concave" length="100"/>'
        '<corner where="bottom-right" shape="notched" length="200"/></corners>')

    assert getCornerInfo(corners, 'top-left') == (CornerShape.Concave, 100)
    assert getCornerInfo(corners, 'bottom-right') == (CornerShape.Notched, 200)


def test_renders_notched_and_concave_corner_masks():
    notchedInfo = CornersInfo(
        topLeft=CornerInfo(CornerShape.Notched, 25))
    notchedImage = applyCornerMask(Image.new('RGB', (100, 100)), notchedInfo, 100)
    assert hasImplementedCorners(notchedInfo)
    assert notchedImage.getchannel('A').getpixel((24, 24)) == 0
    assert notchedImage.getchannel('A').getpixel((26, 26)) == 255

    concaveInfo = CornersInfo(
        topLeft=CornerInfo(CornerShape.Concave, 25))
    concaveImage = applyCornerMask(Image.new('RGB', (100, 100)), concaveInfo, 100)
    assert hasImplementedCorners(concaveInfo)
    assert concaveImage.getchannel('A').getpixel((5, 5)) == 0
    assert concaveImage.getchannel('A').getpixel((22, 22)) == 255

def test_testCorners(main=False):
    albumFolderBasename, albumBasename, inFile, yyyymmdd = defineCommonVariables()
    styleid = "S"
    if (main):
        # use an undated output file name when running as main rather than via pytest
        outFileBasename = f'{albumBasename}.mcf.pdf'
    else:
        outFileBasename = f'{albumBasename}.mcf.{yyyymmdd}{styleid}.pdf'
    outFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", outFileBasename))
    latestResultFile = getLatestResultFile(albumFolderBasename, f"*{styleid}.pdf")
    tryToBuildBook(inFile, outFile, latestResultFile, False)

if __name__ == '__main__':
    #only executed when this file is run directly.
    test_recognises_unsupported_corner_shapes()
    test_renders_notched_and_concave_corner_masks()
    test_testCorners(main=True)
