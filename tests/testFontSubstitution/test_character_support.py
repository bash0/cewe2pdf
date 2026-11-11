
"""Tests for per-character font-family overrides."""
from pathlib import Path
import sys

from unittest.mock import call

import pytest

from conversionState import ConversionState
from fonts import character_support
    
from texts import markup
from texts.markup import createTextRunContext


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

@pytest.mark.parametrize(
    ('bold', 'italic', 'expectedFace'),
    [
        (False, False, 'Override Regular'),
        (True, False, 'Override Bold'),
        (False, True, 'Override Italic'),
        (True, True, 'Override Bold Italic'),
    ],
)
def test_resolveCharacterFontOverrideSelectsCorrectStyle(
        monkeypatch, bold, italic, expectedFace):
    """An override must preserve the original bold/italic styling."""
    state = ConversionState()
    state.character_font_overrides['ŷ'] = 'Override Family'

    availableFonts = {
        'Override Regular': 'regular.ttf',
        'Override Bold': 'bold.ttf',
        'Override Italic': 'italic.ttf',
        'Override Bold Italic': 'bold-italic.ttf',
    }

    monkeypatch.setattr(
        character_support, 'tt2ps', lambda family, b, i: expectedFace)
    monkeypatch.setattr(
        character_support, 'supportsCharacter', lambda *args: True)

    result = character_support.resolveCharacterFontOverride(
        'ŷ', bold, italic, availableFonts, state)

    assert result == expectedFace


def test_resolveCharacterFontOverrideWithoutConfiguration():
    """Characters without an explicit override are left unchanged."""
    state = ConversionState()

    assert character_support.resolveCharacterFontOverride(
        'ŷ', False, False, {}, state) is None


def test_resolveCharacterFontOverrideWithUnknownFamily(monkeypatch):
    """An unregistered family must not be used."""
    state = ConversionState()
    state.character_font_overrides['ŷ'] = 'Unknown Family'

    def unknownFamily(family, bold, italic):
        raise KeyError(family)

    monkeypatch.setattr(character_support, 'tt2ps', unknownFamily)

    assert character_support.resolveCharacterFontOverride(
        'ŷ', False, False, {}, state) is None


def test_resolveCharacterFontOverrideWithMissingFace(monkeypatch):
    """A family mapping is not enough if its selected face is unavailable."""
    state = ConversionState()
    state.character_font_overrides['ŷ'] = 'Override Family'

    monkeypatch.setattr(
        character_support, 'tt2ps', lambda family, bold, italic: 'Missing Face')

    assert character_support.resolveCharacterFontOverride(
        'ŷ', False, False, {}, state) is None


@pytest.mark.parametrize('supportResult', [False, None])
def test_resolveCharacterFontOverrideRequiresConfirmedSupport(
        monkeypatch, supportResult):
    """An unsupported or uninspectable font must not be selected."""
    state = ConversionState()
    state.character_font_overrides['ŷ'] = 'Override Family'

    availableFonts = {'Override Regular': 'override.ttf'}

    monkeypatch.setattr(
        character_support, 'tt2ps',
        lambda family, bold, italic: 'Override Regular')
    monkeypatch.setattr(
        character_support, 'supportsCharacter',
        lambda *args: supportResult)

    assert character_support.resolveCharacterFontOverride(
        'ŷ', False, False, availableFonts, state) is None


def test_createTextRunContextPreservesEffectiveFormatting():
    """The context must capture all effective formatting for a text run."""
    state = ConversionState()
    availableFonts = {'Arial': 'arial.ttf'}

    context = createTextRunContext(
        'Arial',
        12.5,
        700,
        {'font-style': 'italic', 'text-decoration': 'underline',
         'color': '#123456'},
        {},
        availableFonts,
        state
    )

    assert context.font_name == 'Arial'
    assert context.font_size == 12.5
    assert context.bold
    assert context.italic
    assert context.underline
    assert context.color == '#123456'
    assert context.available_fonts is availableFonts
    assert context.state is state


def test_AddAlbumTextWithFontOverridesAppliesOnlyConfiguredCharacters(
        monkeypatch):
    """An override changes the font only for the configured character."""
    state = ConversionState()
    state.character_font_overrides['ŷ'] = 'Arial'

    context = markup.TextRunContext(
        font_name='Original Font',
        font_size=12,
        bold=True,
        italic=True,
        underline=True,
        color='#123456',
        available_fonts={},
        state=state
    )

    monkeypatch.setattr(
        markup,
        'resolveCharacterFontOverride',
        lambda character, bold, italic, fonts, state:
            'Arial Bold Italic' if character == 'ŷ' else None
    )
    monkeypatch.setattr(
        markup, 'tt2ps', lambda *args: 'Original Font')
    monkeypatch.setattr(
        markup, 'supportsCharacter', lambda character, *args:
            False if character == 'ŷ' else True)

    result = markup.AddAlbumTextWithFontOverrides(
        '', 'the garden at Tŷ Hanes', context)

    assert result == (
        'the garden at T'
        '<font name="Arial Bold Italic">ŷ</font>'
        ' Hanes'
    )


def test_AddAlbumTextWithFontOverridesPreservesParagraphFormatting(
        monkeypatch):
    """A character override must retain the original run's styling."""

    from io import BytesIO

    from reportlab.lib import colors, fonts
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import Paragraph

    from texts import markup

    # Isolate ReportLab's global font registries from the other tests.
    for module, name in (
            (pdfmetrics, '_fonts'),
            (pdfmetrics, '_dynFaceNames'),
            (fonts, '_tt2ps_map'),
            (fonts, '_ps2tt_map')):
        monkeypatch.setattr(module, name, getattr(module, name).copy())

    fontDirectory = (
        PROJECT_ROOT / 'tests/Resources/photofun/fonts')

    fontFiles = {
        'normal': 'LiberationSans-BaDn.ttf',
        'bold': 'LiberationSansBold-1adM.ttf',
        'italic': 'LiberationSansItalic-RJre.ttf',
        'boldItalic': 'LiberationSansBoldItalic-ngV4.ttf',
    }


    def registerFamily(familyName):
        faces = {}

        styleFlags = {
            'normal': (0, 0),
            'bold': (1, 0),
            'italic': (0, 1),
            'boldItalic': (1, 1),
        }

        for style, fileName in fontFiles.items():
            faceName = f'{familyName} {style}'
            fontPath = fontDirectory / fileName

            pdfmetrics.registerFont(TTFont(faceName, str(fontPath)))
            faces[style] = faceName

            bold, italic = styleFlags[style]
            fonts.addMapping(familyName, bold, italic, faceName)

        pdfmetrics.registerFontFamily(
            familyName,
            normal=faces['normal'],
            bold=faces['bold'],
            italic=faces['italic'],
            boldItalic=faces['boldItalic'])

        return faces


    originalFamily = 'Original test family'
    overrideFamily = 'Override test family'

    originalFaces = registerFamily(originalFamily)
    overrideFaces = registerFamily(overrideFamily)

    availableFonts = {
        face: str(fontDirectory / fontFiles[style])
        for faces in (originalFaces, overrideFaces)
        for style, face in faces.items()
    }

    state = ConversionState()
    state.character_font_overrides['ŷ'] = overrideFamily

    textRunContext = markup.TextRunContext(
        font_name=originalFamily,
        font_size=14,
        bold=True,
        italic=True,
        underline=True,
        color='#123456',
        available_fonts=availableFonts,
        state=state
    )

    # Simulate the original font lacking ŷ. The override font is still
    # checked using its real character map by resolveCharacterFontOverride.
    monkeypatch.setattr(
        markup, 'supportsCharacter', lambda *args: False)

    # The ordinary text uses the original family. The overridden character
    # should use the bold-italic face of the configured override family.
    paragraphText = (
        f'<font name="{originalFaces["normal"]}" size="14" color="#123456">'
        '<b><i><u>'
    )
    paragraphText = markup.AddAlbumTextWithFontOverrides(
        paragraphText, 'Tŷ', textRunContext)
    paragraphText += '</u></i></b></font>'

    paragraph = Paragraph(
        paragraphText,
        ParagraphStyle(
            'override-test',
            fontName='Helvetica',
            fontSize=14))

    # Exercise ReportLab's layout and drawing paths as well as its parser.
    output = BytesIO()
    canvas = Canvas(output)
    width, height = paragraph.wrap(300, 50)
    paragraph.drawOn(canvas, 0, 0)
    canvas.save()

    fragments = [
        item[0]
        for item in paragraph.frags[0][1:]
    ]

    ordinaryFragment = next(
        fragment for fragment in fragments
        if fragment.text == 'T')
    overrideFragment = next(
        fragment for fragment in fragments
        if fragment.text == 'ŷ')

    assert ordinaryFragment.fontName == originalFaces['boldItalic']
    assert overrideFragment.fontName == overrideFaces['boldItalic']

    for fragment in (ordinaryFragment, overrideFragment):
        assert fragment.fontSize == pytest.approx(14)
        assert fragment.textColor == colors.HexColor('#123456')
        assert fragment.us_lines

    assert width > 0
    assert height > 0
    assert output.getvalue().startswith(b'%PDF')



def _makeCharacterReplacementContext():
    """Create a minimal context for character replacement tests."""

    state = ConversionState()

    context = markup.TextRunContext(
        font_name='Original family',
        font_size=14,
        bold=False,
        italic=False,
        underline=False,
        color='#123456',
        available_fonts={},
        state=state
    )

    return context


def test_characterReplacementUsedWhenNoFontOverride(
        monkeypatch):
    """Use the configured replacement when the original font lacks a glyph."""

    context = _makeCharacterReplacementContext()
    context.state.character_replacements['ŷ'] = 'y'

    monkeypatch.setattr(
        markup, 'tt2ps', lambda *args: 'Original face')
    monkeypatch.setattr(
        markup, 'supportsCharacter', lambda *args: False)

    result = markup.AddAlbumTextWithFontOverrides(
        '', 'Tŷ', context)

    assert result == 'Ty'


def test_fontOverrideTakesPriorityOverCharacterReplacement(
        monkeypatch):
    """A valid font override takes priority over a replacement."""

    context = _makeCharacterReplacementContext()
    context.state.character_font_overrides['ŷ'] = 'Override family'
    context.state.character_replacements['ŷ'] = 'y'

    monkeypatch.setattr(
        markup, 'tt2ps', lambda *args: 'Original face')
    monkeypatch.setattr(
        markup, 'supportsCharacter', lambda *args: False)
    monkeypatch.setattr(
        markup, 'resolveCharacterFontOverride',
        lambda *args: 'Override face')

    result = markup.AddAlbumTextWithFontOverrides(
        '', 'Tŷ', context)

    assert result == (
        'T<font name="Override face">ŷ</font>')


def test_unavailableFontOverrideFallsBackToReplacement(
        monkeypatch):
    """Use the replacement if the configured font override cannot resolve."""

    context = _makeCharacterReplacementContext()
    context.state.character_font_overrides['ŷ'] = 'Missing family'
    context.state.character_replacements['ŷ'] = 'y'

    monkeypatch.setattr(
        markup, 'tt2ps', lambda *args: 'Original face')
    monkeypatch.setattr(
        markup, 'supportsCharacter', lambda *args: False)
    monkeypatch.setattr(
        markup, 'resolveCharacterFontOverride',
        lambda *args: None)

    result = markup.AddAlbumTextWithFontOverrides(
        '', 'Tŷ', context)

    assert result == 'Ty'


def test_characterReplacementIsHtmlEscaped(monkeypatch):
    """Replacement text is escaped like ordinary CEWE text."""

    context = _makeCharacterReplacementContext()
    context.state.character_replacements['ŷ'] = '&<'

    monkeypatch.setattr(
        markup, 'tt2ps', lambda *args: 'Original face')
    monkeypatch.setattr(
        markup, 'supportsCharacter', lambda *args: False)

    result = markup.AddAlbumTextWithFontOverrides(
        '', 'Tŷ', context)

    assert result == 'T&amp;&lt;'

    
def test_supportedCharacterIsNotReplaced(monkeypatch):
    """Leave a character alone when the original font supports it."""

    context = _makeCharacterReplacementContext()
    context.state.character_font_overrides['ŷ'] = 'Override family'
    context.state.character_replacements['ŷ'] = 'y'

    monkeypatch.setattr(
        markup, 'tt2ps', lambda *args: 'Original face')
    monkeypatch.setattr(
        markup, 'supportsCharacter', lambda *args: True)

    result = markup.AddAlbumTextWithFontOverrides(
        '', 'Tŷ', context)

    assert result == 'Tŷ'
