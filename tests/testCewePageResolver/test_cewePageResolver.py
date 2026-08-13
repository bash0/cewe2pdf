"""Test CEWE page selection without invoking any PDF rendering."""

from pathlib import Path

from lxml import etree

from ceweInfo import ProductStyle
from cewePageResolver import resolvePages
from pageTypes import PageProcessingType


def _testFotobook():
    testMcf = Path(__file__).parents[1] / 'testEmptyPageOne' / 'test_emptyPageOne.mcf'
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
