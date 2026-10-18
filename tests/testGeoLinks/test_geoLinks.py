"""Render EXIF-geotagged photographs with invisible map links."""

from collections import Counter
from datetime import datetime
import os
from pathlib import Path
import sys

import pymupdf
from pikepdf import Pdf
from pytest import approx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from testutils import configureTestImportPaths

configureTestImportPaths(__file__)

from compare_pdf import ComparePDF, ShowDiffsStyle
from cewe2pdf import convertMcf
from imageUtils import getMapUrlFromExif
from testutils import getLatestResultFile


GEO_URL = 'https://www.google.com/maps?q=57.585401,9.939988'
SECOND_GEO_URL = 'https://www.google.com/maps?q=57.371036,9.710512'


def tryToBuildBook(inputFile, outputFile, latestResultFile, expectedPages):
    if os.path.exists(outputFile):
        os.remove(outputFile)
    convertMcf(str(inputFile), keepDoublePages=False, outputFileName=str(outputFile))
    assert Path(outputFile).exists()

    with Pdf.open(outputFile) as renderedPdf:
        assert len(renderedPdf.pages) == expectedPages

    with pymupdf.open(outputFile) as renderedPdf:
        links = [link for page in renderedPdf for link in page.get_links()]
    assert len(links) == 4
    assert all(link['kind'] == pymupdf.LINK_URI for link in links)
    assert Counter(link['uri'] for link in links) == {
        GEO_URL: 3,
        SECOND_GEO_URL: 1,
    }

    # Three ordinary placements use a 10 mm square; the fourth is rotated,
    # so its enclosing PDF rectangle is slightly larger.
    hotspotDimensions = [(link['from'].width, link['from'].height) for link in links]
    assert hotspotDimensions.count((approx(72 / 2.54, abs=0.001),
                                    approx(72 / 2.54, abs=0.001))) == 3
    assert max(width for width, _ in hotspotDimensions) > 72 / 2.54

    # The MCF also contains r9ozcqmh_1_20260506_144655.jpg, which has no GPS
    # metadata.  The exact four-link count above confirms it creates no link.

    if latestResultFile is not None:
        comparison = ComparePDF([outputFile, latestResultFile], ShowDiffsStyle.Nothing)
        assert comparison.compare(), 'Pixel comparison failed'
        comparison.cleanup()
    else:
        print('No approved result PDF to compare with')


def test_imageWithoutGpsDoesNotCreateMapUrl():
    from PIL import Image

    assert getMapUrlFromExif(Image.new('RGB', (1, 1))) is None


def test_mapUrlTemplateCanSelectAnotherMapService():
    from PIL import Image

    imageFile = PROJECT_ROOT / 'tests' / 'testGeoLinks' / 'testGeoLinks_mcf-Dateien' / (
        'y2cp6ylk_1_20260428_100739.jpg')
    with Image.open(imageFile) as image:
        url = getMapUrlFromExif(
            image, 'https://example.invalid/?lat={latitude:.4f}&lon={longitude:.4f}')

    assert url == 'https://example.invalid/?lat=57.5854&lon=9.9400'


def test_geoLinks(main=False):
    folder = 'testGeoLinks'
    album = 'testGeoLinks'
    inputFile = PROJECT_ROOT / 'tests' / folder / f'{album}.mcf'
    suffix = '' if main else f'.{datetime.today():%Y%m%d}S'
    outputFile = PROJECT_ROOT / 'tests' / folder / f'{album}.mcf{suffix}.pdf'
    latestResultFile = getLatestResultFile(folder, '*S.pdf')

    tryToBuildBook(inputFile, outputFile, latestResultFile, expectedPages=28)


if __name__ == '__main__':
    test_geoLinks(main=True)
