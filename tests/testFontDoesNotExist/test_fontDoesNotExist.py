"""Test recovery from an unavailable additional-font definition."""

import sys
import pytest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

# Bootstrap the project root so this test can also run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from fontHandling import addAdditionalFontsFromFile
from extraLoggers import configlogger


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


if __name__ == '__main__':
    sys.exit(pytest.main([__file__]))
