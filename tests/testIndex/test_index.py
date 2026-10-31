# This test needs to be in its own directory, so it can have it's own cwew2pdf.ini.
# Also we can store the asset files here.

# Test rendering when page one is empty

# Bootstrap the project root so this test can also run directly.
import os, os.path
import sys
from pathlib import Path

from numpy import test
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)
# Parse the mcf file to create variations using xml.dom.minidom rather than xml.etree.ElementTree
# Copilot suggested this choice because etree is bad at parsing CDATA
from xml.dom.minidom import parse, Document

from datetime import datetime
from pikepdf import Pdf
import pymupdf
from lxml import etree
from reportlab.lib.styles import ParagraphStyle

from compare_pdf import ComparePDF, ShowDiffsStyle # type: ignore
from cewe2pdf import convertMcf # type: ignore
from conversionState import ConversionState # type: ignore
from fonts.line_scales import LineScales # type: ignore
from infrastructure.extraLoggers import mustsee # type: ignore
from texts.areas import processTextParas # type: ignore

from testutils import getLatestResultFile, getOutFileBasename, runModifications


class IndexEntryRecorder:
    """Small index double which records the size supplied for matching."""

    def __init__(self):
        self.fontSizes = []

    def CheckForIndexEntry(self, font, fontSize):
        self.fontSizes.append((font, fontSize))
        return font == 'Index heading' and fontSize == 14

    @staticmethod
    def AppendIndexText(existingText, newText):
        return newText if existingText is None else f'{existingText} {newText}'


def test_scaled_span_uses_authored_size_for_index_matching():
    """A fit-to-box shrink must not remove a configured index heading."""
    body = etree.fromstring('''
        <body><p><span style="font-size:14pt; color:#000000;">Shrunk heading</span></p></body>
    ''')
    index = IndexEntryRecorder()
    flowables = []
    style = ParagraphStyle('index-test', fontName='Helvetica', fontSize=14)
    style.textOutline = None
    style.letterSpacing = 0.0

    indexText, _ = processTextParas(
        flowables, None, '', [], body, 'Index heading', 14, {}, 400,
        'Index heading', None, None, style, 0.99, set(body), LineScales(None),
        ConversionState(), index, 500)

    assert index.fontSizes == [('Index heading', 14.0)]
    assert indexText == 'Shrunk heading'


def assertPdfOutline(outFile):
    """The visible index also supplies reader navigation to its real PDF pages."""
    with pymupdf.open(outFile) as renderedPdf:
        assert renderedPdf.get_toc() == [
            [1, 'Contents', 2],
            [2, '2 June 2025. A heading text', 3],
            [2, '3 June 2025. A second heading text', 3],
            [2, '28-29 April 2025 A second heading paragraph', 4],
            [2, '4 June 2025. A longer heading text', 4],
            [2, '5 June 2025. A different font heading', 4],
            [2, '19 June 2025. Later in the journey', 7],
        ]


def assertPdfIndexLinks(outFile):
    """The visible index lines also link to their final PDF destinations."""
    with pymupdf.open(outFile) as renderedPdf:
        links = renderedPdf[1].get_links()
        assert [link['kind'] for link in links] == [pymupdf.LINK_GOTO] * 6
        assert [link['page'] for link in links] == [2, 2, 3, 3, 3, 6]


def assertPdfPageLabels(outFile):
    """Album covers and CEWE content pages get useful reader labels."""
    with pymupdf.open(outFile) as renderedPdf:
        assert renderedPdf.get_page_labels() == [
            {'startpage': 0, 'prefix': 'Cover', 'firstpagenum': 1},
            {'startpage': 1, 'prefix': '', 'style': 'D', 'firstpagenum': 1},
            {'startpage': 27, 'prefix': 'Cover', 'firstpagenum': 1},
        ]


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
    assertPdfOutline(outFile)
    assertPdfIndexLinks(outFile)
    assertPdfPageLabels(outFile)

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

def test_index(main=False):
    albumFolderBasename, albumBasename, inFile, yyyymmdd = defineCommonVariables()

    styleid = "S"
    outFileBasename = getOutFileBasename(main, albumBasename, yyyymmdd, styleid)
    outFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", outFileBasename))
    latestResultFile = getLatestResultFile(albumFolderBasename, f"*{styleid}.pdf")
    tryToBuildBook(inFile, outFile, latestResultFile, False, 28)

if __name__ == '__main__':
    #only executed when this file is run directly.
    test_index(main=True)
