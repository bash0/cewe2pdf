"""Shared background geometry must be independent of per-page colour choices."""

from pathlib import Path
import sys
from xml.etree import ElementTree

from PIL import Image, ImageChops
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from testutils import configureTestImportPaths

configureTestImportPaths(__file__)

from ceweInfo import PdfProductStyle
from conversionState import ConversionState
from pageTypes import PageProcessingType
from pages import parseInputPage
from renderContext import RenderContext


class BackgroundCanvas:
    """Capture the real JPEGs and placement passed to the PDF canvas."""

    def __init__(self):
        self.draws = []

    def drawImage(self, reader, left, top, width, height):
        image = Image.frombytes('RGB', reader.getSize(), reader.getRGBData())
        self.draws.append((image, (left, top, width, height)))

    def setPageSize(self, _size):
        """Page setup does not change the captured image pixels."""


def renderPair(resourceFolder, rightColour, productStyle=PdfProductStyle.AlbumDoubleSide,
               rightDesign='6480', alignments=('1', '3')):
    """Draw one ordinary spread with identical or different colour settings."""
    left = ElementTree.Element('background', alignment=alignments[0], designElementId='6480',
        hue='210', fading='3', type='1', rotation='0')
    right = ElementTree.Element('background', alignment=alignments[1], designElementId=rightDesign,
        hue=str(rightColour[0]), fading=str(rightColour[1]), type='1', rotation='0')
    context = RenderContext(1, 150, 80, 150, Image.Resampling.LANCZOS, {}, {}, ())
    canvas = BackgroundCanvas()
    state = ConversionState()
    book = ElementTree.Element('fotobook')
    for number, tag in [(2, left), (3, right)]:
        page = ElementTree.SubElement(book, 'page', pagenr=str(number), type='normalpage')
        ElementTree.SubElement(page, 'bundlesize', width='20', height='10')
        page.append(tag)
    for page in book.findall('page'):
        number = int(page.get('pagenr'))
        parseInputPage(book, str(resourceFolder), (str(resourceFolder),), '', canvas,
            page, number, 4, PageProcessingType.RegularPage, productStyle,
            number % 2 == 1, state, {}, False, context, lambda *_args: None)
    return canvas.draws


@pytest.mark.parametrize('sourceSize, fittedSize, rightColour', [
    ((42, 12), (24, 12), (0, 3)),
    ((12, 12), (12, 6), (210, 5)),
])
def test_sharedFittingIsIndependentOfColour(tmp_path, sourceSize, fittedSize, rightColour):
    """Cover horizontal/vertical crops and changes of hue/fading without a matrix."""
    source = Image.new('RGB', sourceSize)
    # A neutral two-dimensional ramp survives recolouring. It makes movement
    # of the crop visible without coupling the geometry check to colour maths.
    source.putdata([(2 * left + 8 * top,) * 3
        for top in range(source.height) for left in range(source.width)])
    source.save(tmp_path / '6480.bmp')
    shared = renderPair(tmp_path, (210, 3))
    separate = renderPair(tmp_path, rightColour)
    assert len(shared) == 1
    assert len(separate) == 2
    assert shared[0][0].size == fittedSize
    assert shared[0][1] == (0, 0, 20, 10)
    assert [draw[1] for draw in separate] == [(0, 0, 10, 10), (10, 0, 10, 10)]
    assert [draw[0].size for draw in separate] == [(fittedSize[0] // 2, fittedSize[1])] * 2
    joined = Image.new('RGB', fittedSize)
    joined.paste(separate[0][0], (0, 0))
    joined.paste(separate[1][0], (fittedSize[0] // 2, 0))
    # Encoding separate JPEGs changes block boundaries, but not the source crop.
    difference = ImageChops.difference(shared[0][0], joined)
    assert max(channel[1] for channel in difference.getextrema()) <= 4
    for colour in [(210, 3), rightColour]:
        singles = renderPair(tmp_path, colour, PdfProductStyle.AlbumSingleSide)
        assert [draw[1] for draw in singles] == [(0, 0, 10, 10)] * 2
        joined = Image.new('RGB', fittedSize)
        joined.paste(singles[0][0], (0, 0))
        joined.paste(singles[1][0], (fittedSize[0] // 2, 0))
        difference = ImageChops.difference(shared[0][0], joined)
        assert max(channel[1] for channel in difference.getextrema()) <= 4


@pytest.mark.parametrize('alignment, productStyle, rightDesign, cropLeft', [
    ('1', PdfProductStyle.AlbumSingleSide, '201', 0),
    ('2', PdfProductStyle.AlbumDoubleSide, '6480', 3),
    ('3', PdfProductStyle.AlbumSingleSide, '201', 6),
])
def test_spread_first_respects_individual_alignment(tmp_path, alignment, productStyle, rightDesign, cropLeft):
    """Cover different designs and independently centred copies without a matrix."""
    source = Image.new('RGB', (12, 12))
    source.putdata([(2 * x + 8 * y,) * 3 for y in range(12) for x in range(12)])
    source.save(tmp_path / '6480.bmp')
    Image.new('RGB', (12, 12), 'white').save(tmp_path / '201.bmp')
    draws = renderPair(tmp_path, (210, 3), productStyle, rightDesign,
        (alignment, alignment if rightDesign == '6480' else '3'))
    assert len(draws) == 2
    assert draws[0][0].size == (6, 6)
    expected = source.crop((cropLeft, 3, cropLeft + 6, 9))
    difference = ImageChops.difference(draws[0][0], expected)
    assert max(channel[1] for channel in difference.getextrema()) <= 4
    if alignment == '2':
        assert draws[0][0].tobytes() == draws[1][0].tobytes()


def test_one_pixel_plain_background_remains_opaque(tmp_path):
    """A constant texture must not become an empty crop at tiny source sizes."""
    Image.new('RGB', (1, 1), (90, 90, 90)).save(tmp_path / '6480.bmp')
    for productStyle in (PdfProductStyle.AlbumSingleSide, PdfProductStyle.AlbumDoubleSide):
        draws = renderPair(tmp_path, (210, 3), productStyle)
        assert draws
        assert all(image.getpixel((0, 0)) == (90, 90, 90) for image, _rectangle in draws)


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
