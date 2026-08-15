"""Tests for conversion setup when no CEWE installation is available."""

import configparser
import os
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

# Bootstrap the project root so this test can also run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from conversionSetup import prepareConversion
from conversionState import ConversionState
from extraLoggers import configlogger
from fontHandling import getMissingFontSubstitute, loadMissingFontSubstitutions


def test_prepareConversionWithoutCeweConfiguration():
    """A self-contained MCF can be prepared without CEWE configuration.

    Font registration is outside the scope of this setup test, and is mocked
    so the assertion does not depend on the fonts installed on the host.
    """
    sourceMcf = PROJECT_ROOT / 'tests' / 'testEmptyPageOne' / 'test_emptyPageOne.mcf'

    with TemporaryDirectory() as temporaryDirectory:
        temporaryPath = Path(temporaryDirectory)
        albumMcf = temporaryPath / sourceMcf.name
        shutil.copy2(sourceMcf, albumMcf)
        originalCwd = Path.cwd()
        try:
            # The temporary folder contains neither configuration format.
            # Changing cwd prevents the repository sample INI participating.
            os.chdir(temporaryPath)
            with patch('conversionSetup.findAndRegisterFonts', return_value={}):
                setup = prepareConversion(str(albumMcf), None, None, ConversionState())
        finally:
            os.chdir(originalCwd)

    assert setup.key_account_folder is None
    assert setup.background_locations == ()
    assert setup.clipart_files == {}
    assert setup.clipart_paths == ()
    assert setup.passepartout_folders == ()


def test_defaultFontSubstitutionsNeedAvailableReplacementFonts():
    """Standalone mode falls back to Helvetica, not an absent test font."""
    state = ConversionState()

    loadMissingFontSubstitutions(None, {}, state)

    assert 'CEWE Head' not in state.missing_font_substitutions
    assert getMissingFontSubstitute('CEWE Head', state) == 'Helvetica'


def test_configuredFontSubstitutionCanUseReportLabBaseFont():
    """An INI mapping may target a ReportLab font needing no file registration."""
    configuration = configparser.ConfigParser()
    configuration['DEFAULT'] = {
        'missingFontSubstitutions': 'Courier PS: Courier\nTimes New Roman: Times-Roman'
    }
    state = ConversionState()

    loadMissingFontSubstitutions(configuration['DEFAULT'], {}, state)

    assert getMissingFontSubstitute('Courier PS', state) == 'Courier'
    assert getMissingFontSubstitute('Times New Roman', state) == 'Times-Roman'


def test_configuredFontSubstitutionStillRejectsUnavailableReplacement():
    """A configured replacement must be a registered or ReportLab base font."""
    configuration = configparser.ConfigParser()
    configuration['DEFAULT'] = {
        'missingFontSubstitutions': 'Courier PS: A Font That Does Not Exist'
    }
    state = ConversionState()

    with patch.object(configlogger, 'error') as logError:
        loadMissingFontSubstitutions(configuration['DEFAULT'], {}, state)

    assert 'Courier PS' not in state.missing_font_substitutions
    logError.assert_called_once_with(
        "Font substitution with 'A Font That Does Not Exist' ignored, that font has not been found")
