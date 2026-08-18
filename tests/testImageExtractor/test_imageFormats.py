"""Render the image-format fixture and compare it with its approved PDF."""

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest
from pikepdf import Pdf

# Bootstrap the project root so this test can also run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from testutils import configureTestImportPaths, getLatestResultFile

configureTestImportPaths(__file__)

from compare_pdf import ComparePDF, ShowDiffsStyle  # type: ignore
from cewe2pdf import convertMcf  # type: ignore


TEST_DIRECTORY = Path(__file__).parent
ALBUM_FILE = TEST_DIRECTORY / 'test_imageExtractor.mcfx'


def buildAndCompareImageFormats(main=False):
    """Create a PDF containing each imported image format and compare it."""
    if not ALBUM_FILE.is_file():
        pytest.skip(f'Fixture has not yet been added: {ALBUM_FILE.name}')

    styleId = 'S'
    yyyymmdd = datetime.today().strftime('%Y%m%d')
    outputName = 'test_imageExtractor.mcfx.pdf' if main else \
        f'test_imageExtractor.mcfx.{yyyymmdd}{styleId}.pdf'
    outputFile = TEST_DIRECTORY / outputName
    latestResultFile = getLatestResultFile(
        TEST_DIRECTORY.name, f'*{styleId}.pdf')

    if outputFile.exists():
        os.remove(outputFile)

    convertMcf(str(ALBUM_FILE), False, outputFileName=str(outputFile))
    assert outputFile.is_file()

    with Pdf.open(outputFile) as readPdf:
        assert len(readPdf.pages) == 28

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


def test_imageFormats():
    """Pytest entry point for the CEWE-created image-format album."""
    buildAndCompareImageFormats()


if __name__ == '__main__':
    buildAndCompareImageFormats(main=True)
