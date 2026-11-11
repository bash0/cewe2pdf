
"""Utilities for checking Unicode character support in registered fonts."""

import logging
import os

from fontTools.ttLib import TTFont
from reportlab.lib.fonts import tt2ps
from reportlab.pdfbase import _glyphlist, pdfmetrics

logger = logging.getLogger(__name__)


def getFontCharacterMap(fontFile, state):
    """Return the Unicode code points supported by a font.

    The result is cached in ConversionState.
    Returns None if the font cannot be inspected.
    """

    cacheKey = os.path.normcase(os.path.abspath(fontFile))

    if cacheKey in state.font_character_maps:
        return state.font_character_maps[cacheKey]

    characterMap = None
    font = None

    try:
        font = TTFont(fontFile, lazy=True)
        cmap = font.getBestCmap()

        if cmap is not None:
            characterMap = set(cmap.keys())

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "Cannot inspect character map in font '%s': %s",
            fontFile, exc
        )

    finally:
        if font is not None:
            font.close()

    state.font_character_maps[cacheKey] = characterMap
    return characterMap


def supportsCharacter(character, fontFile, state, fontName=None):
    """Return True/False for supported/unsupported, None if unknown."""

    if fontFile is None:
        if fontName is not None:
            return supportsBuiltInCharacter(character, fontName)
        return None

    characterMap = getFontCharacterMap(fontFile, state)

    if characterMap is None:
        return None

    return ord(character) in characterMap


def resolveCharacterFontOverride(
        fontFamily, character, bold, italic, fonts, state):
    """Return the registered override face and replacement character.

    Return None if the override family is not registered, the requested
    face is unavailable, or that face does not support the character.
    """

    override = state.character_font_overrides.get(
        (fontFamily, character))

    if not override:
        return None

    overrideFamily, overrideCharacter = override
    # Resolve the appropriate face within the override family.
    try:
        fontFace = tt2ps(
            overrideFamily, int(bold), int(italic))
    except (KeyError, ValueError):
        return None

    # Only use faces that were successfully registered for this conversion.
    fontFile = fonts.get(fontFace)

    if fontFile is None:
        return None

    # The replacement face must support the replacement character.
    if supportsCharacter(
            overrideCharacter, fontFile, state) is not True:
        return None

    return fontFace, overrideCharacter


def findFontsSupportingCharacter(character, fonts, state, excludedFont=None):
    """Return registered font faces which support the given character."""

    alternatives = []

    for fontName, fontFile in fonts.items():
        if fontName == excludedFont:
            continue

        if supportsCharacter(character, fontFile, state):
            alternatives.append(fontName)

    return sorted(alternatives, key=str.casefold)


def checkCharacterSupport(text, fontName, bold, italic, fonts, state):
    """Log unsupported characters in text for the actual ReportLab font face."""

    if not text:
        return

    # Resolve the face using the same ReportLab mapping used by <b> and <i>.
    try:
        fontFace = tt2ps(fontName, int(bold), int(italic))
    except (KeyError, ValueError):
        fontFace = fontName

    fontFile = fonts.get(fontFace)

    for character in text:
        # Ignore control characters; they are not printable glyphs.
        if ord(character) < 32:
            continue

        if supportsCharacter(character, fontFile, state, fontFace) is not False:
            continue

        ruleKey = (fontName, character)

        # A successfully resolved explicit override handles this character.
        if ruleKey in state.character_font_overrides:
            if resolveCharacterFontOverride(
                    fontName, character, bold, italic, fonts, state
            ) is not None:
                continue

        # A configured replacement also handles this character.
        if ruleKey in state.character_replacements:
            continue

        warningKey = (fontFace, character)

        if not state.show_all_unsupported_characters:
            if warningKey in state.unsupported_character_warnings:
                continue
            state.unsupported_character_warnings.add(warningKey)

        # A configured suggestion takes priority over automatic discovery.
        suggestion = state.character_font_suggestions.get(character)

        if suggestion is None:
            alternatives = findFontsSupportingCharacter(
                character, fonts, state, excludedFont=fontFace)
            if alternatives:
                suggestion = alternatives[0]

        if suggestion:
            logger.warning(
                "Character '%s' (U+%04X) is not supported by font '%s'. "
                "Consider using '%s' instead.",
                character, ord(character), fontFace, suggestion
            )
        else:
            logger.warning(
                "Character '%s' (U+%04X) is not supported by font '%s'. "
                "No alternative registered font was found.",
                character, ord(character), fontFace
            )


def supportsBuiltInCharacter(character, fontName):
    """Check character support in a built-in ReportLab font."""

    try:
        font = pdfmetrics.getFont(fontName)
    except KeyError:
        return None

    if not font.face.builtIn:
        return None

    unicodeValues = {
        _glyphlist._glyphname2unicode[glyphName]
        for glyphName in font.encoding.vector
        if glyphName in _glyphlist._glyphname2unicode
    }

    return ord(character) in unicodeValues
