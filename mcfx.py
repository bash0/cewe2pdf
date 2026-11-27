"""Compatibility entry point for the converter's MCFX extraction cache."""

import logging
from pathlib import Path
import sqlite3
import sys
import tempfile

from infrastructure.mcfx_archive import extract_mcfx


def unpackMcfx(mcfxPath: Path, tempdirPath):
    """Retain the converter's exit-on-error API and temporary-folder ownership."""
    temporary = None
    try:
        if tempdirPath is None:
            # The caller, rather than this wrapper's scope, owns successful extraction's lifetime.
            temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
            destination = Path(temporary.name)
        else:
            destination = Path(tempdirPath)
        result = extract_mcfx(mcfxPath, destination, reuse_existing=True)
    except (OSError, ValueError, sqlite3.Error) as error:
        if temporary is not None:
            temporary.cleanup()
        logging.error(f'Exiting: failure unpacking MCFX: {error}')
        sys.exit(1)
    return temporary, result.mcf_path
