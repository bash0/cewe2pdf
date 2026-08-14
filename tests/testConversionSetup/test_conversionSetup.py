"""Tests for conversion setup when no CEWE installation is available."""

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
