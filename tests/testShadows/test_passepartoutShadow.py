"""Passepartout shadows include the photo and the open decorative frame."""

from io import BytesIO
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock, call, patch
from xml.etree import ElementTree

from PIL import Image
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from conversionState import ConversionState
from decorations.passepartout import Passepartout
from imageareas import processAreaImageTag
from ceweInfo import PdfProductStyle
from pageTypes import PageProcessingType
from renderContext import RenderContext


def test_composite_preserves_holes_photo_offset_and_partial_alpha():
    """A single silhouette must retain transparency from both components."""
    frame = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
    frame.putpixel((80, 80), (0, 0, 0, 255))
    frame.putpixel((20, 30), (0, 0, 0, 128))
    buffer = BytesIO()
    frame.save(buffer, 'PNG')
    buffer.seek(0)
    info = SimpleNamespace(srcXmlFile='example.xml', clipartFile='frame.svg',
        fotoarea_x=0.1, fotoarea_y=0.2, fotoarea_width=0.4, fotoarea_height=0.3)
    context = SimpleNamespace(image_resampling_filter=Image.Resampling.LANCZOS)
    photo = Image.new('RGBA', (40, 30), (10, 20, 30, 128))
    with patch('decorations.passepartout.rasteriseClipart',
            return_value=SimpleNamespace(pngMemFile=buffer)):
        result = Passepartout.createShadowImage(photo, info, 100, 100, 255, [], context)
    alpha = result.getchannel('A')
    assert alpha.getpixel((15, 25)) == 128  # Photo alpha is not multiplied twice.
    assert alpha.getpixel((20, 30)) == 192  # Overlapping photo and frame.
    assert alpha.getpixel((80, 80)) == 255  # Frame outside the photo opening.
    assert alpha.getpixel((5, 5)) == 0
    assert alpha.getpixel((60, 30)) == 0  # Gap between photo and frame.


@pytest.mark.parametrize('rotation', [0, 60])
def test_frame_shadow_is_drawn_once_at_frame_centre_before_foreground(rotation):
    """Exercise real resource lookup, fotoarea placement and the image-area path."""
    fixture = PROJECT_ROOT / 'tests/testShadows'
    root = ElementTree.parse(fixture / 'test_shadows.mcf').getroot()
    area = next(area for page in root.findall('page') for area in page.findall('area')
        if area.find('image') is not None
        and area.find('image').get('passepartoutDesignElementId') == '125186'
        and float(area.find('position').get('rotation')) == rotation)
    position = area.find('position')
    width, height = float(position.get('width')), float(position.get('height'))
    infoPath = PROJECT_ROOT / 'tests/hps/5026/addons/125186/masks/v1/decorations/12809-DECO-ZZ.xml'
    context = RenderContext(1, 150, 80, 150, Image.Resampling.LANCZOS, {}, {}, ())
    state = ConversionState(passepartout_files={125186: str(infoPath)})
    canvas = Mock()
    shadows = []

    def captureShadow(_decoration, _height, _width, pdf, _context, _state,
                      silhouette, shadowWidth, shadowHeight, areaRotation):
        assert pdf.drawImage.call_count == 0
        # The photo's offset has not yet been applied to the canvas.
        assert pdf.translate.call_args_list == [call(100, 200)]
        shadows.append((silhouette, shadowWidth, shadowHeight, areaRotation))

    try:
        processAreaImageTag(area.find('image'), area, height, rotation, width,
            'test_shadows_mcf-Dateien', PdfProductStyle.AlbumSingleSide, str(fixture),
            PageProcessingType.RegularPage, canvas, 2050, 100, 200,
            context, state, captureShadow, Mock())
        assert len(shadows) == 1
        silhouette, shadowWidth, shadowHeight, shadowRotation = shadows[0]
        assert (shadowWidth, shadowHeight, shadowRotation) == (width, height, rotation)
        assert silhouette.size == (int(0.5 + width * 150 / 254), int(0.5 + height * 150 / 254))
        assert silhouette.getchannel('A').getextrema() == (0, 255)
        assert canvas.drawImage.call_count == 2  # Photo and frame remain separate.
        reader = canvas.drawImage.call_args_list[0].args[0]
        photo = Image.frombytes('RGB', reader.getSize(), reader.getRGBData())
        # The older frame descriptor requested a crop wider than this sea
        # photograph, leaving an opaque black strip along its right edge.
        assert photo.getpixel((photo.width - 2, photo.height // 2)) != (0, 0, 0)
    finally:
        for name in state.temporary_files:
            Path(name).unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
