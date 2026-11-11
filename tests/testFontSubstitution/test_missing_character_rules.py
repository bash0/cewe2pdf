
"""Tests for loading font-specific missing-character rules from the INI file."""

import configparser
import logging

from conversionState import ConversionState
from conversionSetup import loadMissingCharacterRules


def _loadRules(iniText):
    """Parse INI text and load its missing-character rules."""
    configuration = configparser.ConfigParser()
    configuration.read_string(iniText)

    state = ConversionState()
    loadMissingCharacterRules(configuration, state)

    return state


def test_loadsReplacementsAndFontOverrides():
    """Load both types of font-specific rules."""
    state = _loadRules("""
[MissingCharacterHandling]
Replacements =
    Crafty Girls, U+0177 = y
    SomeFont, U+00E6 = ae

FontOverrides =
    Arial Rounded MT Bold, U+0177 = Archivo Narrow
""")

    assert state.character_replacements == {
        ('Crafty Girls', 'ŷ'): 'y',
        ('SomeFont', 'æ'): 'ae',
    }

    assert state.character_font_overrides == {
        ('Arial Rounded MT Bold', 'ŷ'): 'Archivo Narrow',
    }


def testPreservesFontFamilyCasingAndWhitespace():
    """Font-family names and rule values retain their intended casing."""
    state = _loadRules("""
[MissingCharacterHandling]
Replacements =
    Crafty Girls, U+0177 = y
    Arial Rounded MT Bold, U+00E6 = ae
""")

    assert ('Crafty Girls', 'ŷ') in state.character_replacements
    assert ('crafty girls', 'ŷ') not in state.character_replacements
    assert ('Arial Rounded MT Bold', 'æ') in state.character_replacements

    assert state.character_replacements[
        ('Arial Rounded MT Bold', 'æ')
    ] == 'ae'


def testSupportsFontNamesContainingCommas():
    """The final comma separates the font family from the character code."""
    state = _loadRules("""
[MissingCharacterHandling]
Replacements =
    Family, With, Commas, U+0177 = y
""")

    assert state.character_replacements == {
        ('Family, With, Commas', 'ŷ'): 'y',
    }


def testIgnoresDuplicateRules(caplog):
    """Duplicate font/character rules are rejected rather than overwritten."""
    with caplog.at_level(logging.WARNING):
        state = _loadRules("""
[MissingCharacterHandling]
Replacements =
    Crafty Girls, U+0177 = y
    Crafty Girls, U+0177 = x
    Crafty Girls, U+0177 = z
""")

    assert state.character_replacements == {}

    assert 'duplicate' in caplog.text.lower()


def testIgnoresMalformedRules(caplog):
    """Malformed entries and invalid Unicode values are ignored."""
    with caplog.at_level(logging.WARNING):
        state = _loadRules("""
[MissingCharacterHandling]
Replacements =
    Crafty Girls, U+0177 = y
    Missing separator
    , U+0177 = y
    Crafty Girls, U+ZZZZ = y
    Crafty Girls, U+110000 = y
    Crafty Girls, U+D800 = y
    Crafty Girls, U+0177 =
""")

    assert state.character_replacements == {
        ('Crafty Girls', 'ŷ'): 'y',
    }

    assert 'invalid' in caplog.text.lower()


def testIgnoresConflictingReplacementAndOverride(caplog):
    """A font/character pair cannot have both kinds of rule."""
    with caplog.at_level(logging.WARNING):
        state = _loadRules("""
[MissingCharacterHandling]
Replacements =
    Crafty Girls, U+0177 = y
    SomeFont, U+00E6 = ae

FontOverrides =
    Crafty Girls, U+0177 = Archivo Narrow
    SomeFont, U+00F8 = Arial
""")

    assert state.character_replacements == {
        ('SomeFont', 'æ'): 'ae',
    }

    assert state.character_font_overrides == {
        ('SomeFont', 'ø'): 'Arial',
    }

    assert 'conflicting' in caplog.text.lower()


def testEmptySectionProducesEmptyRules():
    """An empty configuration section produces no rules."""
    state = _loadRules("""
[MissingCharacterHandling]
""")

    assert state.character_replacements == {}
    assert state.character_font_overrides == {}


def testMissingSectionDoesNotRaiseAnError():
    """The loader tolerates configurations without the new section."""
    configuration = configparser.ConfigParser()
    configuration.read_string("""
[OtherSection]
SomeOption = some value
""")

    state = ConversionState()
    loadMissingCharacterRules(configuration, state)

    assert state.character_replacements == {}
    assert state.character_font_overrides == {}
