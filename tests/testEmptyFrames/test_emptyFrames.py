"""Empty CEWE frames print their artwork with a transparent photograph opening."""

from pathlib import Path
import sys
from unittest.mock import Mock
from xml.etree import ElementTree

from PIL import Image
import pymupdf
import pytest
from reportlab.pdfgen import canvas

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from ceweInfo import PdfProductStyle
from conversionState import ConversionState
from imageareas import processAreaImageTag
from pageTypes import PageProcessingType
from renderContext import RenderContext


@pytest.fixture
def resources(tmp_path):
    (tmp_path / 'frame.svg').write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
        '<path fill="#000000" fill-rule="evenodd" '
        'd="M0 0H100V100H0Z M20 20H80V80H20Z"/></svg>', encoding='utf-8')
    descriptor = tmp_path / 'frame.xml'
    descriptor.write_text(
        '<decorations><decoration type="fading" designElementId="1" id="frame">'
        '<fading designElementType="passepartout" file="mask.svg">'
        '<clipart file="frame.svg"/></fading></decoration>'
        '<decoration type="fading" designElementId="2" id="mask">'
        '<fading designElementType="passepartout" file="mask.svg"/></decoration></decorations>',
        encoding='utf-8')
    context = RenderContext(1, 254, 80, 254, Image.Resampling.LANCZOS, {}, {}, ())
    state = ConversionState(passepartout_files={1: str(descriptor), 2: str(descriptor)})
    area = ElementTree.fromstring(
        '<area areatype="imagearea"><position width="80" height="80" rotation="0"/>'
        '<decoration alpha="0.5"><border enabled="1" color="#ff00ff00" width="5"/>'
        '<shadow shadowEnabled="1" shadowDistance="10"/></decoration>'
        '<image passepartoutDesignElementId="1"><ClipartConfiguration><colors>'
        '<color source="#000000" target="#ff0000"/>'
        '</colors></ClipartConfiguration></image></area>')
    return area, context, state


def draw(area, context, state, pdf, folder):
    processAreaImageTag(area.find('image'), area, 80, float(area.find('position').get('rotation')), 80,
        '', PdfProductStyle.AlbumSingleSide, str(folder), PageProcessingType.RegularPage,
        pdf, 100, 50, 50, context, state, Mock(side_effect=AssertionError('Unexpected photo shadow')),
        Mock(side_effect=AssertionError('Unexpected photo border')))


def render(area, context, state, tmp_path):
    output = tmp_path / 'candidate.pdf'
    pdf = canvas.Canvas(str(output), pagesize=(100, 100))
    pdf.setFillColorRGB(0, 0, 1)
    pdf.rect(0, 0, 100, 100, stroke=0, fill=1)
    draw(area, context, state, pdf, tmp_path)
    pdf.save()
    with pymupdf.open(output) as document:
        raster = document[0].get_pixmap()
        return Image.frombytes('RGB', (raster.width, raster.height), raster.samples)


def test_empty_frame_preserves_opening_colour_and_opacity_without_photo_decorations(resources, tmp_path):
    area, context, state = resources
    before = ElementTree.tostring(area)
    result = render(area, context, state, tmp_path)
    assert result.getpixel((50, 50)) == (0, 0, 255), 'The empty opening must reveal the page'
    red, green, blue = result.getpixel((15, 50))
    assert red >= 120 and red <= 135 and green == 0 and blue >= 120 and blue <= 135
    assert result.getpixel((5, 50)) == (0, 0, 255), 'No placeholder or photo shadow outside the frame'
    assert not state.temporary_files and ElementTree.tostring(area) == before


def test_empty_frame_honours_mirroring_and_rotation(resources, tmp_path):
    area, context, state = resources
    (tmp_path / 'frame.svg').write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
        '<rect width="25" height="25" fill="#000000"/></svg>', encoding='utf-8')
    area.find('position').set('rotation', '90')
    area.find('image').set('filename', '')
    area.find('image/ClipartConfiguration').set('mirror', 'y')
    result = render(area, context, state, tmp_path)
    assert result.getpixel((80, 80))[0] > 120
    assert result.getpixel((20, 20)) == (0, 0, 255)
    assert result.getpixel((80, 20)) == (0, 0, 255)


def test_empty_plain_mask_only_and_unavailable_frames_remain_blank(resources, tmp_path):
    area, context, state = resources
    for resource in (None, '2', '999'):
        image = area.find('image')
        if resource is None:
            image.attrib.pop('passepartoutDesignElementId', None)
        else:
            image.set('passepartoutDesignElementId', resource)
        pdf = Mock()
        draw(area, context, state, pdf, tmp_path)
        assert not pdf.mock_calls
    # A referenced-but-missing photograph is not an empty frame. Keep its
    # established warning/omission behaviour instead of hiding the broken link.
    area.find('image').set('passepartoutDesignElementId', '1')
    area.find('image').set('filename', 'missing-photo.jpg')
    pdf = Mock()
    draw(area, context, state, pdf, tmp_path)
    assert not pdf.mock_calls


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
