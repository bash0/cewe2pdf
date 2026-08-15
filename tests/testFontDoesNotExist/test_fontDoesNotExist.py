"""Test recovery from an unavailable additional-font definition."""

import configparser
import os
import sys
import pytest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

# Bootstrap the project root so this test can also run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from conversionState import ConversionState
from fontHandling import addAdditionalFontsFromFile, findAndRegisterFonts
from extraLoggers import configlogger
from pathutils import systemfont_dirs


def test_missingAdditionalFontIsLoggedAndIgnored():
    """A bad definition must not prevent usable definitions being collected."""
    with TemporaryDirectory() as temporaryDirectory:
        temporaryPath = Path(temporaryDirectory)
        existingFontFile = temporaryPath / 'available.ttf'
        existingFontFile.touch()
        existingFontDirectory = temporaryPath / 'font-directory'
        existingFontDirectory.mkdir()
        missingFontFile = temporaryPath / 'not-there.ttf'
        fontDefinitions = temporaryPath / 'additional_fonts.txt'
        fontDefinitions.write_text(
            f'# A comment is ignored\n'
            f'Legacy definition = {missingFontFile}\n'
            f'{existingFontFile}\n'
            f'{existingFontDirectory}\n',
            encoding='utf-8')

        ttfFiles = []
        fontDirs = []

        with patch.object(configlogger, 'error') as logError:
            addAdditionalFontsFromFile(fontDefinitions, ttfFiles, fontDirs)

        assert ttfFiles == [str(existingFontFile)]
        assert fontDirs == [str(existingFontDirectory)]
        logError.assert_called_once_with(
            f'Custom additional font file does not exist: {missingFontFile}')


def test_systemFontFoldersAreOptIn():
    """System font discovery must remain disabled unless configured."""
    with TemporaryDirectory() as temporaryDirectory:
        temporaryPath = Path(temporaryDirectory)

        configuration = configparser.ConfigParser()
        configuration['DEFAULT'] = {}

        # IGNORELOCALFONTS prevents fonts installed specifically for the test
        # user's account affecting this platform-independent assertion.
        # additional_fonts.txt is optional.  Pretend it is not present so that
        # the repository's sample file cannot participate when the test runs
        # with the project root as its working directory.  ValueError is the
        # normal signal from findFileInDirs when a file is not found.
        with patch.dict(os.environ, {'IGNORELOCALFONTS': '1'}), \
                patch('fontHandling.findFileInDirs', side_effect=ValueError):
            availableFonts = findAndRegisterFonts(
                configuration['DEFAULT'], None, str(temporaryPath), None,
                ConversionState())

        assert availableFonts == {}

        configuration['DEFAULT']['loadSystemFonts'] = 'True'
        expectedSystemFontFolders = [str(fontDirectory) for fontDirectory in systemfont_dirs()
                                     if fontDirectory.exists()]
        # Use the real system folders and parse their real font files, but do
        # not mutate ReportLab's process-wide registry.  The mocked methods
        # receive every registration request, allowing the final assertion to
        # verify that each discovered font would have been registered.
        with patch.dict(os.environ, {'IGNORELOCALFONTS': '1'}), \
                patch('fontHandling.findFileInDirs', side_effect=ValueError), \
                patch('fontHandling.pdfmetrics.registerFont') as registerFont, \
                patch('fontHandling.pdfmetrics.registerFontFamily'):
            availableFonts = findAndRegisterFonts(
                configuration['DEFAULT'], None, str(temporaryPath), None,
                ConversionState())

        print(
            f'loadSystemFonts found {len(availableFonts)} fonts '
            f'from {expectedSystemFontFolders}')
        assert expectedSystemFontFolders
        assert availableFonts
        assert registerFont.call_count == len(availableFonts)


def test_systemFontDirsMatchCurrentPlatform():
    """The real system-font directory selection is correct for this platform."""
    if sys.platform.startswith('win'):
        expectedDirectories = (Path(os.getenv('WINDIR', r'C:\\Windows')) / 'Fonts',)
    elif sys.platform.startswith('darwin'):
        expectedDirectories = (Path('/Library/Fonts'), Path('/System/Library/Fonts'))
    else:
        expectedDirectories = (Path('/usr/local/share/fonts'), Path('/usr/share/fonts'))

    assert systemfont_dirs() == expectedDirectories


if __name__ == '__main__':
    # -s leaves the discovered-system-font count visible for an interactive run.
    sys.exit(pytest.main([__file__, '-s']))
