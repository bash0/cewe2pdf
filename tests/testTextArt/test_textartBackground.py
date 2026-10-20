"""TextArt backgrounds preserve the transparent hole, opacity and text geometry."""

from io import BytesIO
from pathlib import Path
import sys
from unittest.mock import Mock, patch

import pymupdf
import pytest
from lxml import etree
from reportlab.pdfgen import canvas

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from texts.art import processTextArt
from texts.backgrounds import drawTextArtBackground, getTextBackground


GREEN = (174, 242, 201)
BLUE = (0, 0, 255)


def renderRing(radiusY=None, centreY=0, colourAlpha=255, decorationAlpha=1):
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(200, 200))
    pdf.setFillColorRGB(0, 0, 1)
    pdf.rect(0, 0, 200, 200, stroke=0, fill=1)
    pdf.translate(100, 100)
    colour = (colourAlpha << 24) | 0xAEF2C9
    area = etree.fromstring(
        f'<area backgroundcolor="{colour}"><decoration alpha="{decorationAlpha}"/></area>')
    drawTextArtBackground(pdf, area, 40, radiusY, centreY, 20)
    # A following shape must retain the caller's opaque graphics state.
    pdf.setFillColorRGB(1, 0, 0)
    pdf.rect(-90, -90, 10, 10, stroke=0, fill=1)
    pdf.save()
    with pymupdf.open(stream=stream.getvalue(), filetype='pdf') as document:
        return document[0].get_pixmap()


def pixelAt(pdfPixmap, x, y):
    return pdfPixmap.pixel(x, pdfPixmap.height - y)


@pytest.mark.parametrize('radiusY,centreY', [(None, 0), (20, 0), (20, 20)])
def test_ring_has_a_real_hole_and_no_rectangle_background(radiusY, centreY):
    image = renderRing(radiusY, centreY)
    assert pixelAt(image, 100, 100 + centreY) == BLUE
    # PDF decimal colours can rasterize one 8-bit level below their source.
    assert pixelAt(image, 150, 100 + centreY) == pytest.approx(GREEN, abs=1)
    assert pixelAt(image, 170, 100 + centreY) == BLUE
    if radiusY is not None:
        assert pixelAt(image, 100, 130 + centreY) == pytest.approx(GREEN, abs=1)
        assert pixelAt(image, 130, 110 + centreY) == BLUE


@pytest.mark.parametrize('colourAlpha,decorationAlpha', [(128, 1), (255, 0.5), (128, 0.5)])
def test_colour_and_decoration_opacities_multiply(colourAlpha, decorationAlpha):
    image = renderRing(colourAlpha=colourAlpha, decorationAlpha=decorationAlpha)
    alpha = colourAlpha / 255 * decorationAlpha
    expected = tuple(round(alpha * foreground + (1 - alpha) * background)
        for foreground, background in zip(GREEN, BLUE))
    assert pixelAt(image, 150, 100) == pytest.approx(expected, abs=2)
    assert pixelAt(image, 100, 100) == BLUE
    assert pixelAt(image, 15, 15) == (255, 0, 0)


@pytest.mark.parametrize('xml', [
    '<area/>', '<area backgroundcolor="#00aef2c9"/>',
    '<area backgroundcolor="#ffaef2c9"><decoration alpha="0"/></area>'])
def test_missing_or_transparent_background_does_not_draw(xml):
    pdf = Mock()
    drawTextArtBackground(pdf, etree.fromstring(xml), 40, None, 0, 20)
    assert not pdf.mock_calls


@pytest.mark.parametrize('value,expected', [('invalid', 1), ('-0.2', 0), ('1.2', 1)])
def test_invalid_or_out_of_range_opacity_keeps_existing_text_policy(value, expected, caplog):
    area = etree.fromstring(f'<area backgroundcolor="#ffaef2c9"><decoration alpha="{value}"/></area>')
    colour, alpha = getTextBackground(area)
    assert tuple(round(channel * 255) for channel in (colour.red, colour.green, colour.blue)) == GREEN
    assert alpha == expected
    assert len(caplog.records) == 1


def test_background_is_painted_before_border_and_letters():
    area = etree.fromstring('<area backgroundcolor="#ffaef2c9"><decoration>'
        '<border/><cwtextart enabled="1"/></decoration></area>')
    body = etree.fromstring('<body style="font-family:Helvetica; font-size:18pt;"><p>AB</p></body>')
    order = Mock()
    with patch('texts.art.drawTextArtBackground') as background, \
            patch('texts.art.processDecorationBorders') as border, \
            patch('texts.art.handleTextArt') as text:
        order.attach_mock(background, 'background')
        order.attach_mock(border, 'border')
        order.attach_mock(text, 'text')
        processTextArt(area, 490, 490, 0, Mock(), 200, 200, body, 0, 0,
            area.findall('decoration/cwtextart'), Mock(mcf_to_reportlab=72 / 254), Mock())
    assert [call[0] for call in order.mock_calls] == ['background', 'border', 'text']
    # The editor's default ring has radii 171 and 245 MCF units.
    assert background.call_args.args[2] == pytest.approx(171 * 72 / 254)
    assert background.call_args.args[5] == pytest.approx(74 * 72 / 254)


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__]))
