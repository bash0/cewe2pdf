"""Pixel-comparison regression test for CEWE background left/centre/right alignment."""

from datetime import datetime
import os
from pathlib import Path
import sys

from pikepdf import Pdf


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from testutils import configureTestImportPaths

configureTestImportPaths(__file__)

from compare_pdf import ComparePDF, ShowDiffsStyle
from cewe2pdf import convertMcf
from testutils import getLatestResultFile


def tryToBuildBook(inputFile, outputFile, latestResultFile, keepDoublePages,
                   expectedPages):
    """Render the fixture and compare it with the user-approved PDF, if any."""
    if os.path.exists(outputFile):
        os.remove(outputFile)

    convertMcf(str(inputFile), keepDoublePages=keepDoublePages,
               outputFileName=str(outputFile))
    assert outputFile.exists()

    with Pdf.open(outputFile) as renderedPdf:
        assert len(renderedPdf.pages) == expectedPages

    if latestResultFile is None:
        print('No approved result PDF to compare with')
        return

    comparison = ComparePDF([outputFile, latestResultFile], ShowDiffsStyle.Nothing)
    try:
        assert comparison.compare(), 'Pixel comparison failed'
    finally:
        comparison.cleanup()


def test_backgroundAlignment(main=False):
    """The fixture contains otherwise identical left, centre, and right backgrounds."""
    folder = 'testBackgroundAlignment'
    album = 'testBackgroundAlignment'
    inputFile = PROJECT_ROOT / 'tests' / folder / f'{album}.mcf'
    dateSuffix = '' if main else f'.{datetime.today():%Y%m%d}'

    outputFile = PROJECT_ROOT / 'tests' / folder / f'{album}.mcf{dateSuffix}S.pdf'
    latestResultFile = getLatestResultFile(folder, '*S.pdf')
    tryToBuildBook(inputFile, outputFile, latestResultFile,
                   keepDoublePages=False, expectedPages=28)

    outputFile = PROJECT_ROOT / 'tests' / folder / f'{album}.mcf{dateSuffix}D.pdf'
    latestResultFile = getLatestResultFile(folder, '*D.pdf')
    tryToBuildBook(inputFile, outputFile, latestResultFile,
                   keepDoublePages=True, expectedPages=15)


if __name__ == '__main__':
    test_backgroundAlignment(main=True)
