"""Signed tracking and centring across TextArt's circular and elliptical paths."""

import math
from pathlib import Path
import sys
from unittest.mock import Mock, patch

import pytest
from lxml import etree
from reportlab.pdfbase import pdfmetrics

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from texts.art import (draw_styled_text_on_arc, getCentredTextArtStartAngle,
    getTextArtGlyphAngles, getTextArtGlyphPosition, measureTextArtGlyphs, parse_html_text, processTextArt)


HTML = '<body style="font-family:Helvetica; font-size:18pt;"><p>Hello World</p></body>'


def measuredGlyphs():
    parsed, _ = parse_html_text(HTML)
    return measureTextArtGlyphs(parsed, Mock())


@pytest.mark.parametrize('spacing', [10, 0, -5, -30])
def test_circle_extent_counts_only_between_character_gaps(spacing):
    glyphs = measuredGlyphs()
    _, extent = getTextArtGlyphAngles(glyphs, 100, 47, letterSpacing=spacing)
    expectedLength = pdfmetrics.stringWidth('Hello World', 'Helvetica', 18) + 10 * spacing
    assert math.radians(extent) * 100 == pytest.approx(expectedLength)


def test_spacing_does_not_change_single_character_placement():
    glyphs = measuredGlyphs()[:1]
    normal = getTextArtGlyphAngles(glyphs, 100, 20, 40)
    assert getTextArtGlyphAngles(glyphs, 100, 20, 40, 500) == normal
    assert getTextArtGlyphAngles(glyphs, 100, 20, 40, -500) == normal


@pytest.mark.parametrize('spacing', [10, 0, -5, -30])
@pytest.mark.parametrize('radii,centreAngle', [((100, None), 90), ((100, 35), 90),
    ((35, 100), 45), ((100, 35), 225), ((100, 100), -90)])
def test_measured_and_drawn_extent_share_the_requested_centre(spacing, radii, centreAngle):
    glyphs = measuredGlyphs()
    start = getCentredTextArtStartAngle(glyphs, radii[0], centreAngle, radii[1], spacing)
    _, extent = getTextArtGlyphAngles(glyphs, radii[0], start, radii[1], spacing)
    assert start + extent / 2 == pytest.approx(centreAngle, abs=1e-6)


@pytest.mark.parametrize('clockwise', [True, False])
@pytest.mark.parametrize('radiusY', [None, 35])
def test_tracking_preserves_glyphs_styles_and_direction(clockwise, radiusY):
    styledHtml = HTML.replace('<p>Hello World</p>',
        '<p><span style="font-family:Times-Roman; font-size:24pt; color:#ff0000;">Hello</span>'
        '<span style="font-family:Courier; font-size:12pt; color:#0000ff;"> World</span></p>')
    canvases = []
    for spacing in (-5, 0, 10):
        pdf = Mock()
        draw_styled_text_on_arc(pdf, styledHtml, 100, 45, Mock(), clockwise=clockwise,
            ellipseRadiusY=radiusY, letterSpacing=spacing)
        canvases.append(pdf)
    expectedText = 'Hello World'[::-1] if clockwise else 'Hello World'
    for pdf in canvases:
        assert ''.join(call.args[2] for call in pdf.drawString.call_args_list) == expectedText
        assert {call.args for call in pdf.setFont.call_args_list} == {('Times-Roman', 24), ('Courier', 12)}
        assert pdf.setFont.call_args_list == canvases[0].setFont.call_args_list
        assert pdf.setFillColor.call_args_list == canvases[0].setFillColor.call_args_list
        assert pdf.drawString.call_args_list == canvases[0].drawString.call_args_list
    assert canvases[0].translate.call_args_list != canvases[1].translate.call_args_list
    assert canvases[1].translate.call_args_list != canvases[2].translate.call_args_list


@pytest.mark.parametrize('value,expected', [('35.25', 9.992125984), ('-17.625', -4.996062992), ('0', 0)])
def test_mcf_spacing_reaches_textart_renderer(value, expected):
    area = etree.fromstring(
        '<area><decoration><cwtextart enabled="1"/></decoration>'
        f'<text><textFormat letterSpacing="{value}"/></text></area>')
    body = etree.fromstring(HTML)
    context = Mock(mcf_to_reportlab=72 / 254)
    with patch('texts.art.handleTextArt') as drawArc:
        processTextArt(area, 1794, 676, 0, Mock(), 0, 0, body, 0, 0,
            area.findall('decoration/cwtextart'), context, Mock())
    assert drawArc.call_args.args[-1] == pytest.approx(expected)


def test_missing_font_is_reported_once_despite_ellipse_centring(caplog):
    html = '<body style="font-family:MissingWordArtFont; font-size:18pt;"><p>Unknown font</p></body>'
    with patch('texts.art.getMissingFontSubstitute', return_value='Helvetica'):
        draw_styled_text_on_arc(Mock(), html, 100, 0, Mock(), ellipseRadiusY=35, letterSpacing=10)
    assert sum('Unregistered font in TextArt' in record.message for record in caplog.records) == 1


def test_empty_text_has_no_extent_or_gaps():
    assert getTextArtGlyphAngles([], 100, 45, 35, -5) == ([], 0)
    assert getCentredTextArtStartAngle([], 100, 45, 35, -5) == 45


@pytest.mark.parametrize('clockwise', [True, False])
@pytest.mark.parametrize('widthAngle', [0, 45, 90, 120, 180, 225, 270, 315])
def test_zero_spacing_keeps_original_circular_advance_radius(clockwise, widthAngle):
    """Lock the crowded angular span verified against the editor, in both directions."""
    pdf = Mock()
    draw_styled_text_on_arc(pdf, HTML, 100, widthAngle, Mock(), clockwise=clockwise)
    text = 'Hello World'[::-1] if clockwise else 'Hello World'
    widths = [pdfmetrics.stringWidth(char, 'Helvetica', 18) for char in text]
    # Original renderer's formula, independently of the new layout helpers.
    advanceRadius = 100 + 18 * 0.9
    paintedRadius = advanceRadius - 18 * 0.7 if clockwise else advanceRadius
    centreAngle = 90 - widthAngle if clockwise else widthAngle - 90
    angle = centreAngle - math.degrees(sum(widths) / advanceRadius) / 2
    for width, position in zip(widths, pdf.translate.call_args_list):
        halfSpan = math.degrees(width / advanceRadius) / 2
        glyphAngle = math.radians(angle + halfSpan)
        assert position.args == pytest.approx((
            paintedRadius * math.cos(glyphAngle), paintedRadius * math.sin(glyphAngle)))
        angle += 2 * halfSpan


@pytest.mark.parametrize('radii', [(200, 70), (70, 200), (100, 100)])
@pytest.mark.parametrize('angle', [0, 30, 60, 90, 145, 225, 300])
def test_baseline_inset_is_perpendicular_and_has_constant_distance(radii, angle):
    radiusX, radiusY = radii
    theta = math.radians(angle)
    outerX, outerY = radiusX * math.cos(theta), radiusY * math.sin(theta)
    x, y, tangent = getTextArtGlyphPosition(radiusX, radiusY, angle, 18)
    dx, dy = x - outerX, y - outerY
    tangentX, tangentY = -radiusX * math.sin(theta), radiusY * math.cos(theta)
    assert math.hypot(dx, dy) == pytest.approx(18)
    assert dx * tangentX + dy * tangentY == pytest.approx(0, abs=1e-10)
    assert dx * outerX / radiusX ** 2 + dy * outerY / radiusY ** 2 < 0
    # Rotation follows the original curve, which is parallel to its offset.
    assert math.cos(math.radians(tangent)) == pytest.approx(tangentX / math.hypot(tangentX, tangentY))
    assert math.sin(math.radians(tangent)) == pytest.approx(tangentY / math.hypot(tangentX, tangentY))


@pytest.mark.parametrize('angle', [0, 45, 90, 225])
def test_uninset_ellipse_keeps_original_position(angle):
    x, y, _ = getTextArtGlyphPosition(200, 70, angle)
    assert x == pytest.approx(200 * math.cos(math.radians(angle)))
    assert y == pytest.approx(70 * math.sin(math.radians(angle)))


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__]))
