"""Render a CEWE MCF containing a literal web address."""

from datetime import datetime
import os
from pathlib import Path
import sys

import pymupdf
from pikepdf import Pdf


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from testutils import configureTestImportPaths

configureTestImportPaths(__file__)

from compare_pdf import ComparePDF, ShowDiffsStyle
from cewe2pdf import convertMcf
from testutils import getLatestResultFile


URLS = {
    'https://example.com/cewe2pdf/a/long/link/which/wraps/across/lines',
    'https://example.com/blue-link',
    'https://example.com/cewe2pdf/a/normal/link.htm',
}


def tryToBuildBook(inputFile, outputFile, latestResultFile, expectedPages):
    if os.path.exists(outputFile):
        os.remove(outputFile)
    assert not os.path.exists(outputFile)
    convertMcf(inputFile, keepDoublePages=False, outputFileName=outputFile)
    assert Path(outputFile).exists()

    with Pdf.open(outputFile) as renderedPdf:
        assert len(renderedPdf.pages) == expectedPages

    with pymupdf.open(outputFile) as renderedPdf:
        links = [link for page in renderedPdf for link in page.get_links()]
    assert links
    assert all(link['kind'] == pymupdf.LINK_URI for link in links)
    assert {link['uri'] for link in links} == URLS

    if latestResultFile is not None:
        print(f'Compare {outputFile} with {latestResultFile}')
        comparison = ComparePDF([outputFile, latestResultFile], ShowDiffsStyle.Nothing)
        assert comparison.compare(), 'Pixel comparison failed'
        comparison.cleanup()
    else:
        print('No approved result PDF to compare with')


def test_textLinks(main=False):
    albumFolderBasename = 'testTextLinks'
    albumBasename = 'testTextLinks'
    inputFile = Path.cwd() / 'tests' / albumFolderBasename / f'{albumBasename}.mcf'
    if main:
        outputFileBasename = f'{albumBasename}.mcf.pdf'
    else:
        yyyymmdd = datetime.today().strftime('%Y%m%d')
        outputFileBasename = f'{albumBasename}.mcf.{yyyymmdd}S.pdf'
    outputFile = Path.cwd() / 'tests' / albumFolderBasename / outputFileBasename
    latestResultFile = getLatestResultFile(albumFolderBasename, '*S.pdf')

    tryToBuildBook(str(inputFile), str(outputFile), latestResultFile, expectedPages=28)


if __name__ == '__main__':
    test_textLinks(main=True)
