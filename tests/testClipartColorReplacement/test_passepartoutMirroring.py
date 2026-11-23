"""Mirroring moves the passepartout geometry without reflecting the photograph."""

from pathlib import Path
import sys
from unittest.mock import Mock, call
from xml.etree import ElementTree

from PIL import Image
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from ceweInfo import PdfProductStyle
from conversionState import ConversionState
from imageareas import processAreaImageTag
from pageTypes import PageProcessingType
from renderContext import RenderContext


@pytest.mark.parametrize('mirror,rotation,opening,framePixel,holePixel', [
    (None, 0, (10, 20), (82, 82), (12, 22)),
    ('x', 0, (10, 50), (82, 17), (12, 77)),
    ('y', 30, (50, 20), (17, 82), (87, 22)),
    ('both', 0, (50, 50), (17, 17), (87, 77)),
])
def test_mirrored_frame_mask_opening_and_shadow(tmp_path, mirror, rotation,
    opening, framePixel, holePixel):
    """An asymmetric mask and frame expose each reflection and misplaced aperture."""
    photo = Image.new('RGB', (40, 30))
    photo.putdata([(x * 5, y * 7, 100) for y in range(30) for x in range(40)])
    photo.save(tmp_path / 'photo.png')
    (tmp_path / 'mask.svg').write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="30">'
        '<path d="M10 0H40V30H0V10H10Z" fill="black"/></svg>', encoding='utf-8')
    (tmp_path / 'frame.svg').write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
        '<rect x="80" y="80" width="10" height="10" fill="blue"/></svg>', encoding='utf-8')
    descriptor = tmp_path / 'frame.xml'
    descriptor.write_text(
        '<decorations><decoration type="fading" designElementId="1" id="example">'
        '<fading designElementType="passepartout" file="mask.svg">'
        '<clipart file="frame.svg"/>'
        '<fotoarea x="0.1" y="0.2" width="0.4" height="0.3"/>'
        '</fading></decoration></decorations>', encoding='utf-8')
    area = ElementTree.fromstring(
        '<area><position width="100" height="100"/>'
        '<decoration><shadow shadowEnabled="1"/></decoration>'
        '<image filename="photo.png" passepartoutDesignElementId="1">'
        '<cutout left="0" top="0" scale="1"/>'
        '<ClipartConfiguration/></image></area>')
    area.find('position').set('rotation', str(rotation))
    imageTag = area.find('image')
    if mirror is not None:
        imageTag.find('ClipartConfiguration').set('mirror', mirror)
    context = RenderContext(1, 254, 80, 254, Image.Resampling.LANCZOS, {}, {}, ())
    state = ConversionState(passepartout_files={1: str(descriptor)})
    canvas = Mock()
    shadows = []

    def captureShadow(_decoration, _height, _width, _pdf, _context, _state,
        silhouette, _shadowWidth, _shadowHeight, areaRotation):
        assert canvas.drawImage.call_count == 0
        assert areaRotation == rotation
        shadows.append(silhouette)

    try:
        processAreaImageTag(imageTag, area, 100, rotation, 100, '',
            PdfProductStyle.AlbumSingleSide, str(tmp_path), PageProcessingType.RegularPage,
            canvas, 100, 50, 50, context, state, captureShadow, Mock())
        assert len(shadows) == 1
        assert shadows[0].getpixel(framePixel) == (0, 0, 255, 255)
        assert shadows[0].getpixel(holePixel)[3] == 0
        left, top = opening
        # The colour gradient must retain its direction inside the moved aperture.
        assert shadows[0].getpixel((left + 12, top + 12)) == (60, 84, 100, 255)
        assert canvas.translate.call_args_list[1] == call(left + 20 - 50, 50 - top - 15)
        assert canvas.rotate.call_args_list[0] == call(-rotation)
        assert canvas.rotate.call_args_list[-1] == call(rotation)
        with Image.open(state.temporary_files[0]) as maskedPhoto:
            assert maskedPhoto.getpixel((12, 12)) == (60, 84, 100, 255)
            assert maskedPhoto.getpixel((holePixel[0] - left, holePixel[1] - top))[3] == 0
        reader = canvas.drawImage.call_args_list[1].args[0]
        frame = Image.frombytes('RGB', reader.getSize(), reader.getRGBData())
        assert frame.getpixel(framePixel) == (0, 0, 255)
    finally:
        for name in state.temporary_files:
            Path(name).unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
