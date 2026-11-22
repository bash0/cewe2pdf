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

from backgrounds import processBackground
from ceweInfo import PdfProductStyle
from conversionState import ConversionState
from pageTypes import PageProcessingType
from renderContext import RenderContext


class BackgroundCanvas:
    """Capture the real JPEGs and placement passed to the PDF canvas."""

    def __init__(self):
        self.draws = []

    def drawImage(self, reader, left, top, width, height):
        image = Image.frombytes('RGB', reader.getSize(), reader.getRGBData())
        self.draws.append((image, (left, top, width, height)))


def renderPair(resourceFolder, rightColour):
    """Draw one ordinary spread with identical or different colour settings."""
    left = ElementTree.Element('background', alignment='1', designElementId='6480',
        hue='210', fading='3', type='1', rotation='0')
    right = ElementTree.Element('background', alignment='3', designElementId='6480',
        hue=str(rightColour[0]), fading=str(rightColour[1]), type='1', rotation='0')
    context = RenderContext(1, 150, 80, 150, Image.Resampling.LANCZOS, {}, {}, ())
    canvas = BackgroundCanvas()
    state = ConversionState()
    for number, tag, facing in [(2, left, right), (3, right, left)]:
        processBackground([tag], state, (str(resourceFolder),),
            PdfProductStyle.AlbumDoubleSide, PageProcessingType.RegularPage,
            canvas, 10, 20, number, number % 2 == 1, False, context, [facing])
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


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
