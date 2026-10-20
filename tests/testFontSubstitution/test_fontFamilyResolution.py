"""Resolve CEWE family names whose only installed face is not regular."""

from io import BytesIO
from pathlib import Path
import sys

import pytest
from reportlab.lib import fonts
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from conversionState import ConversionState
from fonts.manager import getAvailableFont, registerFontFamilies


@pytest.fixture
def isolatedFontRegistry(monkeypatch):
    # ReportLab's mappings are process-wide. Test registrations must not
    # affect later album conversions or depend on earlier test registrations.
    for module, name in ((pdfmetrics, '_fonts'), (pdfmetrics, '_dynFaceNames'),
            (fonts, '_tt2ps_map'), (fonts, '_ps2tt_map')):
        monkeypatch.setattr(module, name, getattr(module, name).copy())


@pytest.mark.parametrize('onlyStyle', ['italic', 'bold', 'boldItalic'])
def test_familyWithNoRegularFaceUsesChosenAlternate(isolatedFontRegistry, onlyStyle):
    family = f'Fallback test family {onlyStyle}'
    face = f'{family} face'
    fontFile = PROJECT_ROOT / 'tests/Resources/photofun/fonts/LiberationSansItalic-RJre.ttf'
    pdfmetrics.registerFont(TTFont(face, str(fontFile)))
    members = dict.fromkeys(('normal', 'bold', 'italic', 'boldItalic'))
    members[onlyStyle] = face
    registerFontFamilies({family: members}, [])
    pdf = Canvas(BytesIO())
    state = ConversionState()
    # Even an explicit missing-font rule must not override an available family.
    state.missing_font_substitutions[family] = 'Courier'

    selectedFace = getAvailableFont(family, pdf, {face: str(fontFile)}, state)

    assert selectedFace == face
    assert state.noted_font_substitutions == set()
    paragraph = Paragraph('Normal <b>bold</b> <i>italic</i> <b><i>both</i></b>',
        ParagraphStyle('family fallback', fontName=selectedFace))
    assert all(fragment.fontName == face for fragment in paragraph.frags)
    paragraph.wrap(300, 100)
    paragraph.drawOn(pdf, 10, 10)
    pdf.save()


def test_familyMappingFromEarlierConversionIsNotEnough(isolatedFontRegistry):
    family = 'Unavailable family from earlier conversion'
    pdfmetrics.registerFontFamily(family, normal='Courier')
    state = ConversionState()

    assert getAvailableFont(family, Canvas(BytesIO()), {}, state) == 'Helvetica'
    assert state.noted_font_substitutions == {f'{family}/Helvetica'}


if __name__ == '__main__':
    sys.exit(pytest.main([__file__]))
