"""Test CEWE page selection without invoking any PDF rendering."""

from pathlib import Path
import sys

from lxml import etree
import pytest
from reportlab.lib.units import mm

# This test imports the resolver directly rather than through cewe2pdf.py.
# Derive the project root from this file so that pytest works from any cwd,
# including GitHub Actions' test-collection environment.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from ceweInfo import ProductInfo, PdfProductStyle
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
    pages = list(resolvePages(_testFotobook(), PdfProductStyle.AlbumSingleSide, 28))

    assert len(pages) == 30
    assert [page.page_type for page in pages[:3]] == [
        PageProcessingType.Cover,
        PageProcessingType.FrontInsideCoverBackground,
        PageProcessingType.OpeningContentPage,
    ]
    assert pages[-3].page_type == PageProcessingType.RegularPage
    assert pages[-3].page_number == 26
    assert not pages[-3].finish_page
    assert pages[-2].page_type == PageProcessingType.BackInsideCover
    assert pages[-1].page_type == PageProcessingType.Cover


@pytest.mark.parametrize(('productName', 'expectedSize'), [
    ('ALB14', (205, 270)),
    ('ALB15', (205, 270)),
    ('ALB42', (382, 290)),
    ('ALB82', (205, 270)),
    ('ALB98', (205, 270)),
    ('ALB131', (148, 148)),
])
def test_albumFallbackSizesDescribeTheirInternalPages(productName, expectedSize):
    """Cover bundles include bleed; fallbacks describe the printable product."""
    assert ProductInfo.ceweFormats[productName] == tuple(
        size * mm for size in expectedSize)


def test_resolveSelectedAlbumPages():
    pages = list(resolvePages(_testFotobook(), PdfProductStyle.AlbumSingleSide,
                              28, pageNumbers=[0, 26]))

    assert [(page.page_number, page.page_type) for page in pages] == [
        (0, PageProcessingType.Cover),
        (1, PageProcessingType.FrontInsideCoverBackground),
        (26, PageProcessingType.RegularPage),
    ]


def test_resolveMemoryCards():
    pages = list(resolvePages(_memoryCardsFotobook(), PdfProductStyle.MemoryCard, 25))

    assert len(pages) == 25
    assert [page.page_number for page in pages] == list(range(1, 26))
    assert all(page.page_type == PageProcessingType.RegularPage for page in pages)
    assert [int(page.element.get('pagenr')) for page in pages] == list(range(1, 26))


@pytest.mark.parametrize('fixtureName', ['a4p', 'a4l', 'a5l', 'sq21'])
def test_resolveCalendarPages(fixtureName):
    """Calendar pages are independent, including their pagenr=0 cover."""
    pages = list(resolvePages(_calendarFotobook(fixtureName), PdfProductStyle.Calendar, 13))

    assert [page.page_number for page in pages] == list(range(13))
    assert all(page.page_type == PageProcessingType.CalendarPage for page in pages)
    assert all(not page.odd_page for page in pages)
    assert all(page.finish_page for page in pages)
    assert pages[-1].last_page


def test_detectCalendarStructureWithoutCalendarProductId(caplog):
    """Calendar structure takes priority over an unfamiliar product ID."""
    fotobook = _calendarFotobook('sq21')
    fotobook.set('productname', 'CUSTOM42')

    productStyle = ProductInfo.pdfStyleFromMcf(fotobook)
    pageCount = int(fotobook.find('articleConfig').get('totalpages'))
    pages = list(resolvePages(fotobook, productStyle, pageCount))

    assert productStyle == PdfProductStyle.Calendar
    assert [page.page_number for page in pages] == list(range(13))
    assert all(page.page_type == PageProcessingType.CalendarPage for page in pages)
    assert "Calendar structure detected for product 'CUSTOM42'" in caplog.text


def test_calendarIdentifierWithoutCalendarStructureWarns(caplog):
    """A CAL fallback remains available, but its missing structure is visible."""
    fotobook = etree.fromstring(
        '<fotobook productname="CALfuture"><page pagenr="1" '
        'type="normalpage"><bundlesize width="2100" height="2970"/>'
        '</page></fotobook>')

    assert ProductInfo.pdfStyleFromMcf(fotobook) == PdfProductStyle.Calendar
    assert "Product 'CALfuture' uses a CAL product identifier" in caplog.text


def test_reportsKnownCalendarProductAndItsBundle(caplog):
    """The must-see diagnostic describes the actual MCF bundle, not a guess."""
    fotobook = _calendarFotobook('sq21')

    ProductInfo.reportMcfProduct(fotobook, ProductInfo.pdfStyleFromMcf(fotobook))

    assert ('Product CAL99 (known; Calendar): 210.0 × 210.0 mm '
            '(calendarcoverfront, normalpage).' in caplog.text)


def test_reportsKnownAlbumProductAndItsCoverDifferenceOnOneLine(caplog):
    """The product summary includes a meaningful cover difference once."""
    fotobook = _testFotobook()

    ProductInfo.reportMcfProduct(fotobook, PdfProductStyle.AlbumSingleSide)

    assert caplog.text.count('Product ALB98 (known; AlbumSingleSide)') == 1
    assert '205.0 × 270.0 mm (emptypage, normalpage)' in caplog.text
    assert ('214.5 × 275.0 mm (fullcover, spine; +4.63% width, '
            '+1.85% height)' in caplog.text)


def test_reportsAlbumSpreadSizeWhenDoublePagesAreKept(caplog):
    """The optional spread PDF retains CEWE's full bundle width."""
    fotobook = _testFotobook()

    ProductInfo.reportMcfProduct(fotobook, PdfProductStyle.AlbumDoubleSide)

    assert ('Product ALB98 (known; AlbumDoubleSide): 410.0 × 270.0 mm '
            '(emptypage, normalpage)' in caplog.text)


def test_knownProductWarnsWhenItsNormalBundleIsUnexpected(caplog):
    """A substantial size mismatch is a useful warning, not a render failure."""
    fotobook = _calendarFotobook('sq21')
    normalPage = fotobook.find("./page[@type='normalpage']")
    normalPage.find('./bundlesize').set('width', '10000')

    ProductInfo.reportMcfProduct(fotobook, PdfProductStyle.Calendar)

    assert 'outside the 10% tolerance for its known 210.0 × 210.0 mm format' in caplog.text


def test_warnsWhenAPageTypeUsesInconsistentBundles(caplog):
    """Different bundles for one page type are not the normal album case."""
    fotobook = _calendarFotobook('sq21')
    normalPages = fotobook.findall("./page[@type='normalpage']")
    normalPages[1].find('./bundlesize').set('width', '2110')

    ProductInfo.reportMcfProduct(fotobook, PdfProductStyle.Calendar)

    assert ('uses multiple bundle sizes for normalpage pages: '
            '210.0 × 210.0 mm, 211.0 × 210.0 mm.' in caplog.text)


def test_albumIdentifierWarnsWhenItsCoverStructureIsMissing(caplog):
    """An ALB product without cover records deserves a diagnostic."""
    fotobook = _testFotobook()
    spine = fotobook.find("./page[@type='spine']")
    fotobook.remove(spine)

    assert ProductInfo.pdfStyleFromMcf(fotobook) == PdfProductStyle.AlbumSingleSide
    assert "Album product 'ALB98' lacks expected spine page records" in caplog.text
