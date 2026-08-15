# This test is in its own directory so it can use an empty cewe_folder
# setting and keep any MCF assets beside the MCF file.

import os
import sys
from datetime import datetime
from pathlib import Path

# Bootstrap the project root so this test can also run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)
from pikepdf import Pdf

from compare_pdf import ComparePDF, ShowDiffsStyle  # type: ignore
from cewe2pdf import convertMcf  # type: ignore
from testutils import getLatestResultFile


def tryToBuildBook(inFile, outFile, latestResultFile, keepDoublePages,
                   expectedPages):
    if os.path.exists(outFile):
        os.remove(outFile)

    convertMcf(inFile, keepDoublePages, outputFileName=outFile)
    assert Path(outFile).exists()

    with Pdf.open(outFile) as readPdf:
        assert len(readPdf.pages) == expectedPages, \
            f"Expected {expectedPages} pages, found {len(readPdf.pages)}"

    if latestResultFile is None:
        print('No result file to compare with')
        return

    print(f"Compare {outFile} with {latestResultFile}")
    compare = ComparePDF([outFile, latestResultFile], ShowDiffsStyle.Nothing)
    try:
        assert compare.compare(), 'Pixel comparison failed'
    finally:
        compare.cleanup()


def test_noCewe(main=False):
    albumFolderBasename = 'testNoCewe'
    albumBasename = 'testNoCewe'
    inFile = str(Path(Path.cwd(), 'tests', albumFolderBasename,
                      f'{albumBasename}.mcf'))
    styleid = 'S'
    yyyymmdd = datetime.today().strftime('%Y%m%d')
    outFileBasename = f'{albumBasename}.mcf.pdf' if main else \
        f'{albumBasename}.mcf.{yyyymmdd}{styleid}.pdf'
    outFile = str(Path(Path.cwd(), 'tests', albumFolderBasename,
                       outFileBasename))
    latestResultFile = getLatestResultFile(albumFolderBasename,
                                           f'*{styleid}.pdf')

    # The editor-created fixture should use no CEWE resources.  Adjust this
    # page count if the MCF has a different product layout.
    tryToBuildBook(inFile, outFile, latestResultFile, False, 28)


if __name__ == '__main__':
    test_noCewe(main=True)
