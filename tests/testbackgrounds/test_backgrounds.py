# This test needs to be in its own directory, so it can have it's own cwew2pdf.ini.
# Also we can store the asset files here.

#if you run this file directly, it won't have access to parent folder, so add it to python path
import sys
sys.path.append('..')
sys.path.append('.')
sys.path.append('tests')

import os, os.path
import glob

from pathlib import Path
from pikepdf import Pdf, PdfImage

from compare_pdf import ComparePDF, ShowDiffsStyle # type: ignore
from cewe2pdf import convertMcf # type: ignore

def tryToBuildBook(latestResultFile, keepDoublePages, expectedPages, expectedEqualBackgroundPageLists):
    inFile = str(Path(Path.cwd(), 'tests', 'testbackgrounds', 'allblackbackgrounds.mcf'))
    # TODO, allow convertMcf to accept an output file name
    # from datetime import datetime
    # styleid = "d" if keepDoublePages else "s"
    # today = datetime.today()
    # yyyymmdd = today.strftime("%Y%m%d")
    # outfilebasename = f'allblackbackgrounds{styleid}{yyyymmdd}.mcf.pdf'
    outFile = str(Path(Path.cwd(), 'tests', 'testbackgrounds', 'allblackbackgrounds.mcf.pdf'))
    if os.path.exists(outFile) == True:
        os.remove(outFile)
    assert os.path.exists(outFile) == False
    convertMcf(inFile, keepDoublePages)
    assert Path(outFile).exists() == True

    # check the pdf contents
    readPdf = Pdf.open(outFile)
    numPages =  len(readPdf.pages)
    assert numPages == expectedPages, f"Expected {expectedPages} pages, found {numPages}"

    assumedBackgroundImageKey = None
    for p in range(0, numPages):
        page = readPdf.pages[p]
        imagekeys = list(page.images.keys())
        imagecount = len(imagekeys)
        if p == 0:
            # the test album has just one actual photo image, on the front cover
            assert imagecount == 2, f"Expected 2 images on front cover (background + picture), found {imagecount}"
            coverBackgroundImageKey = imagekeys[1] # should be the same on both cover pages
        elif p == 1 and keepDoublePages:
            assert imagecount == 1, f"Expected 1 image on page 2 (both backgrounds are black), found {imagecount}"
        elif p == numPages - 1 and keepDoublePages:
            assert imagecount == 1, f"Expected 1 image on page {numPages - 1} (both backgrounds are black), found {imagecount}"
        else:
            assert imagecount == 1, f"Expected 1 image (the background) on inner pages, found {imagecount} images on page {p}"
            if p == 4: # remember the key from a random inner page
                innerBackgroundImageKey = imagekeys[0] # should be the same on all inside pages

    # check that the background image keys match for the covers and for all the inner pages
    assert coverBackgroundImageKey is not None, f"Could not locate cover background image"
    for p in expectedEqualBackgroundPageLists[0]: # covers
        page = readPdf.pages[p]
        imagekeys = list(page.images.keys())
        assert coverBackgroundImageKey in imagekeys
    assert innerBackgroundImageKey is not None, f"Could not locate inner background image"
    for p in expectedEqualBackgroundPageLists[1]: # inner pages
        page = readPdf.pages[p]
        imagekeys = list(page.images.keys())
        assert innerBackgroundImageKey in imagekeys, f"Inner background image differs on page {p}"

    # check we've used the right background images
    coverimage = readPdf.pages[0].images[coverBackgroundImageKey]
    coverpdfimage = PdfImage(coverimage)
    assert coverpdfimage.width == 10 and coverpdfimage.height == 10, \
        f"Expected cover bg WxH 10x10, but is {coverpdfimage.width},{coverpdfimage.height}"
    coverpilimage = coverpdfimage.as_pil_image()
    covertestpixel = coverpilimage.getpixel((1,1))
    assert covertestpixel == (236,220,195), f"Expected cover colour (236, 220, 95), got {covertestpixel}"

    innerimage = readPdf.pages[4].images[innerBackgroundImageKey]
    innerpdfimage = PdfImage(innerimage)
    assert innerpdfimage.width == 10 and innerpdfimage.height == 10, \
        f"Expected inner bg WxH 10x10, but is {innerpdfimage.width},{innerpdfimage.height}"
    innerpilimage = innerpdfimage.as_pil_image()
    innertestpixel = innerpilimage.getpixel((1,1))
    assert innertestpixel == (0,0,0), f"Expected inner colour (0, 0, 0), got {innertestpixel}"

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
    resultpdfpattern = str(Path(Path.cwd(), 'tests', 'testbackgrounds', 'previous_result_pdfs', pattern))
    resultpdffiles = glob.glob(resultpdfpattern)
    resultpdffiles.sort(key=os.path.getmtime, reverse=True)
    return resultpdffiles[0] if len(resultpdffiles) > 0 else None


def test_testBackgrounds():
    # allow us to see that we have the expected environment
    python_executable_path = sys.executable
    virtual_env_name = os.path.basename(os.path.dirname(python_executable_path))
    print(f"Virtual Environment: {virtual_env_name}")

    latestResultFile = getLatestResultFile("*S.pdf")
    tryToBuildBook(latestResultFile, False, 28, [[0,27],[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26]])

    latestResultFile = getLatestResultFile("*D.pdf")
    tryToBuildBook(latestResultFile, True, 15, [[0],[1,2,3,4,5,6,7,8,9,10,11,12,13,14]])

if __name__ == '__main__':
    #only executed when this file is run directly.
    test_testBackgrounds()