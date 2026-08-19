"""Render CEWE image rotation and image-background operations."""

import os
import sys
from datetime import datetime
from pathlib import Path

from pikepdf import Pdf

# Bootstrap the project root so this test can also run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from testutils import configureTestImportPaths, getLatestResultFile

configureTestImportPaths(__file__)

from compare_pdf import ComparePDF, ShowDiffsStyle  # type: ignore
from cewe2pdf import convertMcf  # type: ignore


TEST_DIRECTORY = Path(__file__).parent
ALBUM_FILE = TEST_DIRECTORY / 'test_imageOperations.mcf'
EXPECTED_PAGE_COUNT = 28


def buildAndCompareImageOperations(main=False):
    """Create the operation test PDF and compare it with its approved result."""
    styleId = 'S'
    yyyymmdd = datetime.today().strftime('%Y%m%d')
    outputName = ('test_imageOperations.mcf.pdf' if main else
                  f'test_imageOperations.mcf.{yyyymmdd}{styleId}.pdf')
    outputFile = TEST_DIRECTORY / outputName
    latestResultFile = getLatestResultFile(TEST_DIRECTORY.name,
                                           f'*{styleId}.pdf')

    if outputFile.exists():
        os.remove(outputFile)

    convertMcf(str(ALBUM_FILE), False, outputFileName=str(outputFile))
    assert outputFile.is_file()

    with Pdf.open(outputFile) as readPdf:
        assert len(readPdf.pages) == EXPECTED_PAGE_COUNT, \
            f'Expected {EXPECTED_PAGE_COUNT} pages, found {len(readPdf.pages)}'

    if latestResultFile is None:
        print('No approved PDF result file to compare with')
        return

    print(f'Compare {outputFile} with {latestResultFile}')
    compare = ComparePDF([str(outputFile), latestResultFile],
                         ShowDiffsStyle.Nothing)
    try:
        assert compare.compare(), 'Pixel comparison failed'
    finally:
        compare.cleanup()


def test_imageOperations():
    """Pytest entry point for CEWE image rotation/background operations."""
    buildAndCompareImageOperations()


if __name__ == '__main__':
    buildAndCompareImageOperations(main=True)
