"""Regression test for vertically-centred text after automatic font shrinking.

The MCF fixture deliberately needs a text box which is initially just too narrow
for ReportLab, but fits as a single line after cewe2pdf shrinks its font to 99%.
That combination exercises the vertical-centering calculations at a non-unit
scale factor.
"""

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
ALBUM_FILE = TEST_DIRECTORY / 'testTextShrinkVAlign.mcf'
EXPECTED_PAGE_COUNT = 28


def buildAndCompareTextShrinkVAlign(main=False):
    """Render the fixture and compare it with its approved PDF result."""
    if not ALBUM_FILE.is_file():
        message = f'Awaiting fixture MCF: {ALBUM_FILE}'
        if main:
            raise FileNotFoundError(message)
        pytest.skip(message)

    styleId = 'S'
    yyyymmdd = datetime.today().strftime('%Y%m%d')
    outputName = ('testTextShrinkVAlign.mcf.pdf' if main else
                  f'testTextShrinkVAlign.mcf.{yyyymmdd}{styleId}.pdf')
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


def test_textShrinkVAlign():
    """Pytest entry point for scaled, vertically-centred text."""
    buildAndCompareTextShrinkVAlign()


if __name__ == '__main__':
    buildAndCompareTextShrinkVAlign(main=True)
