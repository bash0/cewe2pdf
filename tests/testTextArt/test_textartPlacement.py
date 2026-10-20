"""Placement invariants for current and legacy TextArt geometry."""

from pathlib import Path
import sys
from unittest.mock import Mock, patch

import pytest
from lxml import etree

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from texts.art import processTextArt


MCF_TO_POINTS = 72 / 254


def getArcGeometry(width, height, fontSize, margin=0, legacyRadius=None):
    """Observe the area-to-arc boundary without requiring installed fonts."""
    body = etree.fromstring(
        f'<body style="font-family:Helvetica; font-size:{fontSize}pt;">'
        '<p>Hello World</p></body>')
    area = etree.fromstring('<area><decoration><cwtextart direction="1" enabled="1"/></decoration></area>')
    context = Mock(mcf_to_reportlab=MCF_TO_POINTS)
    pdf = Mock()
    leftPad = margin * MCF_TO_POINTS
    topPad = leftPad if legacyRadius is None else leftPad + legacyRadius * MCF_TO_POINTS
    with patch('texts.art.handleTextArt') as drawArc:
        processTextArt(area, width, height, 37, pdf, 125, 250, body,
            leftPad, topPad, area.findall('decoration/cwtextart'), context, Mock())
    # Area rotation belongs outside arc layout and must be restored.
    assert pdf.method_calls == [
        ('translate', (125, 250), {}), ('rotate', (-37,), {}),
        ('rotate', (37,), {}), ('translate', (-125, -250), {})]
    args = drawArc.call_args.args
    radiusX, centreY, radiusY = args[1], args[5], args[6]
    if radiusY is None:
        radiusY = radiusX
    topInset = height * MCF_TO_POINTS / 2 - (centreY + radiusY)
    return radiusX, radiusY, centreY, topInset


@pytest.mark.parametrize('fontSize', [18, 26, 72])
def test_box_resize_does_not_scale_font_inset(fontSize):
    """Stretch the curve with the box, without moving its top away from the text."""
    original = getArcGeometry(490, 490, fontSize)
    for width, height in [(490, 902.027), (784.974, 490), (1794, 676), (1741.38, 521.654)]:
        stretched = getArcGeometry(width, height, fontSize)
        assert stretched[3] == pytest.approx(original[3])


def test_larger_font_reserves_more_room_above_arc():
    small = getArcGeometry(1794, 676, 18)
    large = getArcGeometry(1794, 676, 72)
    assert large[3] == pytest.approx(4 * small[3])
    # A placement correction translates the ellipse, preserving its curvature.
    assert large[:2] == pytest.approx(small[:2])
    assert large[2] < small[2]


def test_inside_margin_keeps_centre_and_shrinks_arc():
    withoutMargin = getArcGeometry(1794, 676, 72)
    withMargin = getArcGeometry(1794, 676, 72, margin=50)
    assert withMargin[2] == pytest.approx(withoutMargin[2])
    assert withMargin[0] < withoutMargin[0]
    assert withMargin[1] < withoutMargin[1]
    assert withMargin[3] - withoutMargin[3] == pytest.approx(50 * MCF_TO_POINTS)


@pytest.mark.parametrize('width,height', [(490, 490), (490, 902.027), (784.974, 490)])
def test_original_18_point_geometry_is_preserved(width, height):
    radiusX, radiusY, centreY, _ = getArcGeometry(width, height, 18)
    oldTop = MCF_TO_POINTS * (height / 2 - min(width, height) * (0.5 - 171 / 490))
    assert centreY + radiusY == pytest.approx(oldTop)
    assert radiusX == pytest.approx(width * MCF_TO_POINTS * 171 / 490)


def test_legacy_stored_radius_keeps_original_centre():
    radiusX, radiusY, centreY, _ = getArcGeometry(490, 490, 72, legacyRadius=171)
    assert radiusX == pytest.approx(171 * MCF_TO_POINTS)
    assert radiusY == pytest.approx(radiusX)
    assert centreY == 0


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__]))
