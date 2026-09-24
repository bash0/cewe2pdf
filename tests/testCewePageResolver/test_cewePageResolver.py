"""Test CEWE page selection without invoking any PDF rendering."""

from pathlib import Path
import sys

from lxml import etree
import pytest

# This test imports the resolver directly rather than through cewe2pdf.py.
# Derive the project root from this file so that pytest works from any cwd,
# including GitHub Actions' test-collection environment.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from ceweInfo import ProductStyle
from cewePageResolver import resolvePages
from pageTypes import PageProcessingType


def _testFotobook():
    testMcf = Path(__file__).parents[1] / 'testEmptyPageOne' / 'test_emptyPageOne.mcf'
    root = etree.parse(str(testMcf)).getroot()
    return root.find('fotobook') or root


def _memoryCardsFotobook():
    testMcf = Path(__file__).parents[1] / 'testMemoryCards' / 'testMemoryCards.mcf'
    root = etree.parse(str(testMcf)).getroot()
    return root.find('fotobook') or root


def _calendarFotobook(fixtureName):
    testMcf = (Path(__file__).parents[1] / 'testCalendar' / fixtureName /
               f'{fixtureName}.mcf')
    root = etree.parse(str(testMcf)).getroot()
    return root.find('fotobook') or root


def test_resolveAlbumPages():
    pages = list(resolvePages(_testFotobook(), ProductStyle.AlbumSingleSide, 28))

    assert len(pages) == 30
    assert [page.page_type for page in pages[:3]] == [
        PageProcessingType.Cover,
        PageProcessingType.FrontInsideCoverBackground,
        PageProcessingType.FrontInsideCover,
    ]
    assert pages[-3].page_type == PageProcessingType.RegularPage
    assert pages[-3].page_number == 26
    assert not pages[-3].finish_page
    assert pages[-2].page_type == PageProcessingType.BackInsideCover
    assert pages[-1].page_type == PageProcessingType.Cover


def test_resolveSelectedAlbumPages():
    pages = list(resolvePages(_testFotobook(), ProductStyle.AlbumSingleSide,
                              28, pageNumbers=[0, 26]))

    assert [(page.page_number, page.page_type) for page in pages] == [
        (0, PageProcessingType.Cover),
        (1, PageProcessingType.FrontInsideCoverBackground),
        (26, PageProcessingType.RegularPage),
    ]


def test_resolveMemoryCards():
    pages = list(resolvePages(_memoryCardsFotobook(), ProductStyle.MemoryCard, 25))

    assert len(pages) == 25
    assert [page.page_number for page in pages] == list(range(1, 26))
    assert all(page.page_type == PageProcessingType.RegularPage for page in pages)
    assert [int(page.element.get('pagenr')) for page in pages] == list(range(1, 26))


@pytest.mark.parametrize('fixtureName', ['a4p', 'a4l', 'a5l', 'sq21'])
def test_resolveCalendarPages(fixtureName):
    """Calendar pages are independent, including their pagenr=0 cover."""
    pages = list(resolvePages(_calendarFotobook(fixtureName), ProductStyle.Calendar, 13))

    assert [page.page_number for page in pages] == list(range(13))
    assert all(page.page_type == PageProcessingType.CalendarPage for page in pages)
    assert all(not page.odd_page for page in pages)
    assert all(page.finish_page for page in pages)
    assert pages[-1].last_page
