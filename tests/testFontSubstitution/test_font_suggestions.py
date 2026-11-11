
from fonts import font_suggestions


def test_excludes_original_family(monkeypatch):
    monkeypatch.setattr(
        font_suggestions,
        'supportsCharacter',
        lambda character, fontFile, state: True
    )

    fonts = {
        'Arial': 'arial.ttf',
        'Verdana': 'verdana.ttf'
    }
    families = {
        'Arial': {'normal': 'Arial'},
        'Verdana': {'normal': 'Verdana'}
    }

    provider = font_suggestions.FontSuggestionProvider(
        fonts, families, None)

    result = provider.findAlternatives('ŷ', 'Arial', False, False)

    assert result == ['Verdana']


def test_prefers_matching_style(monkeypatch):
    monkeypatch.setattr(
        font_suggestions,
        'supportsCharacter',
        lambda character, fontFile, state: True
    )

    fonts = {
        'NormalFont': 'normal.ttf',
        'BoldFont': 'bold.ttf',
        'ItalicFont': 'italic.ttf'
    }
    families = {
        'Alpha': {'normal': 'NormalFont'},
        'Beta': {'bold': 'BoldFont'},
        'Gamma': {'italic': 'ItalicFont'}
    }

    provider = font_suggestions.FontSuggestionProvider(
        fonts, families, None)

    result = provider.findAlternatives('ŷ', 'Original', True, False)

    assert result == ['Beta', 'Alpha', 'Gamma']


def test_returns_at_most_three_families(monkeypatch):
    monkeypatch.setattr(
        font_suggestions,
        'supportsCharacter',
        lambda character, fontFile, state: True
    )

    fonts = {f'Font{i}': f'font{i}.ttf' for i in range(5)}
    families = {
        f'Family{i}': {'normal': f'Font{i}'}
        for i in range(5)
    }

    provider = font_suggestions.FontSuggestionProvider(
        fonts, families, None)

    result = provider.findAlternatives('ŷ', 'Original', False, False)

    assert len(result) == 3
    assert result == ['Family0', 'Family1', 'Family2']


def test_ignores_unsupported_and_unavailable_faces(monkeypatch):
    def mockSupportsCharacter(character, fontFile, state):
        return fontFile == 'supported.ttf'

    monkeypatch.setattr(
        font_suggestions, 'supportsCharacter', mockSupportsCharacter)

    fonts = {
        'SupportedFont': 'supported.ttf',
        'UnsupportedFont': 'unsupported.ttf'
    }
    families = {
        'Supported': {'normal': 'SupportedFont'},
        'Unsupported': {'normal': 'UnsupportedFont'},
        'Unregistered': {'normal': 'MissingFont'}
    }

    provider = font_suggestions.FontSuggestionProvider(
        fonts, families, None)

    result = provider.findAlternatives('ŷ', 'Original', False, False)

    assert result == ['Supported']


def test_does_not_suggest_uninspectable_fonts(monkeypatch):
    monkeypatch.setattr(
        font_suggestions,
        'supportsCharacter',
        lambda character, fontFile, state: None
    )

    fonts = {'Font': 'font.ttf'}
    families = {'Family': {'normal': 'Font'}}

    provider = font_suggestions.FontSuggestionProvider(
        fonts, families, None)

    result = provider.findAlternatives('ŷ', 'Original', False, False)

    assert result == []
