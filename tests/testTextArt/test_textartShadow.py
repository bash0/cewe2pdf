"""WordArt shadows reuse the exact glyph drawing and the shared shadow engine."""

from pathlib import Path
import sys
from unittest.mock import Mock, patch

import pytest
from lxml import etree
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from conversionState import ConversionState
from texts.art import processTextArt
from texts.shadows import drawTextArtShadow, hasEnabledTextShadow, renderTextSilhouette


HTML = '<body style="font-family:Helvetica; font-size:18pt;"><p>Hello World</p></body>'


def context(config=None):
    return Mock(mcf_to_reportlab=1, image_resolution=72,
        default_config_section={} if config is None else config)


def shadowArea(enabled='1'):
    return etree.fromstring('<area backgroundcolor="#ffaef2c9"><decoration>'
        f'<shadow shadowEnabled="{enabled}"/><border/><cwtextart enabled="1"/>'
        '</decoration><text><textFormat letterSpacing="-5"/></text></area>')


@pytest.mark.parametrize('enabled,config,expected', [
    ('1', {}, True), ('0', {}, False), ('2', {}, False),
    ('1', {'noShadows': 'true'}, False), ('1', {'noShadows': 'false'}, True)])
def test_enabled_shadow_policy(enabled, config, expected):
    assert hasEnabledTextShadow(shadowArea(enabled), context(config)) is expected


def test_legacy_shadow_without_enabled_flag_is_supported():
    area = etree.fromstring('<area><decoration><shadow/></decoration></area>')
    assert hasEnabledTextShadow(area, context())


def test_disabled_shadow_does_not_rasterise_or_draw():
    drawing, pdf = Mock(), Mock()
    drawTextArtShadow(pdf, shadowArea(), 200, 200, 37, drawing,
        context({'noShadows': 'true'}), ConversionState())
    assert not drawing.mock_calls
    assert not pdf.mock_calls


@pytest.mark.parametrize('resolution', [72, 144])
def test_silhouette_has_transparent_background_and_uses_configured_dpi(resolution):
    def paint(pdf):
        pdf.setFont('Helvetica', 20)
        pdf.drawString(20, 40, 'A')
    image, bounds = renderTextSilhouette(paint, 100, 100, resolution)
    assert image.mode == 'RGBA'
    assert image.size == (100 * resolution // 72, 100 * resolution // 72)
    assert image.getpixel((0, 0))[3] == 0
    assert image.getchannel('A').getextrema() == (0, 255)
    assert bounds == (0, 0, 100, 100)


def test_mask_expands_for_letters_outside_all_sides_of_the_area():
    def paint(pdf):
        pdf.setFont('Helvetica', 20)
        pdf.drawString(-30, 25, 'MMMM')
        pdf.drawString(80, 120, 'MMMM')
        pdf.drawString(20, -20, 'MMMM')
    image, (left, bottom, width, height) = renderTextSilhouette(paint, 100, 100, 72, True)
    assert left < -20 and bottom < -15
    assert left + width > 135 and bottom + height > 125
    alpha = image.getchannel('A')
    # All three outlying pieces of text survive, rather than only the part
    # lying inside the original page's 0..100 rectangle.
    for x, y in [(-30, 25), (80, 120), (20, -20)]:
        rectangle = (int(x - left), int(bottom + height - y - 20),
            int(x - left + 65), int(bottom + height - y + 1))
        assert alpha.crop(rectangle).getbbox() is not None


def test_expanded_mask_keeps_its_original_position_and_page_relative_rotation():
    pdf = Mock()
    image = Image.new('RGBA', (140, 140))
    with patch('texts.shadows.renderTextSilhouette', return_value=(image, (-20, -10, 140, 140))), \
            patch('texts.shadows.processDecorationShadow') as engine:
        drawTextArtShadow(pdf, shadowArea(), 100, 100, 37, Mock(), context(), ConversionState())
    pdf.translate.assert_called_once_with(0, 10)
    assert engine.call_args.args[1:3] == (140, 140)
    assert engine.call_args.kwargs['areaRotation'] == 37
    assert engine.call_args.kwargs['im'] is image
    assert engine.call_args.kwargs['imgCropWidth_mcfunit'] == 140
    assert engine.call_args.kwargs['imgCropHeight_mcfunit'] == 140
    pdf.saveState.assert_called_once()
    pdf.restoreState.assert_called_once()


def test_mask_excludes_ring_and_border_and_fonts_are_resolved_once(caplog):
    area = shadowArea()
    body = etree.fromstring(HTML.replace('Helvetica', 'MissingWordArtFont'))
    state = ConversionState()
    with patch('texts.art.getMissingFontSubstitute', return_value='Helvetica'), \
            patch('texts.art.processDecorationBorders'), \
            patch('texts.shadows.processDecorationShadow') as engine:
        processTextArt(area, 200, 200, 0, Mock(), 0, 0, body, 0, 0,
            area.findall('decoration/cwtextart'), context(), state)
    mask = engine.call_args.kwargs['im']
    alpha = mask.getchannel('A')
    assert alpha.getbbox() is not None
    assert alpha.crop((0, mask.height // 2, mask.width, mask.height)).getbbox() is None
    assert sum('Unregistered font in TextArt' in record.message for record in caplog.records) == 1


def test_failed_shadow_still_draws_foreground_letters(caplog):
    area, pdf = shadowArea(), Mock()
    with patch('texts.shadows.renderTextSilhouette', side_effect=RuntimeError('test rendering failure')):
        processTextArt(area, 200, 200, 0, pdf, 0, 0, etree.fromstring(HTML), 0, 0,
            area.findall('decoration/cwtextart'), context(), ConversionState())
    assert pdf.drawString.call_count == len('Hello World')
    assert any('Could not create TextArt shadow silhouette' in record.message for record in caplog.records)


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__]))
