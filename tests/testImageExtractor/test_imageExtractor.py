"""Regression test for extracting files from an .mcfx album container."""

import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

# Bootstrap the project root so this test can also run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from imageExtractor import extractMcfx


TEST_DIRECTORY = Path(__file__).parent
MCFX_FIXTURE = TEST_DIRECTORY / 'test_imageExtractor.mcfx'


def filesInMcfx(mcfxPath):
    """Return the original filename and bytes for every file in an .mcfx."""
    with sqlite3.connect(mcfxPath) as connection:
        return connection.execute('SELECT Filename, Data FROM Files').fetchall()


def test_extractMcfx_preservesContainedFiles():
    """Extracted photographs and other resources must be byte-for-byte copies."""
    if not MCFX_FIXTURE.is_file():
        pytest.skip(f'Fixture has not yet been added: {MCFX_FIXTURE.name}')

    sourceFiles = filesInMcfx(MCFX_FIXTURE)

    with tempfile.TemporaryDirectory() as temporaryDirectory:
        outputDirectory = Path(temporaryDirectory) / 'extracted'
        # The command-line tool normally receives a relative filename.  Keep
        # that case covered: unpackMcfx() temporarily changes directory.
        relativeFixture = MCFX_FIXTURE.relative_to(Path.cwd())
        extractedMcf = extractMcfx(relativeFixture, outputDirectory)

        assert extractedMcf == outputDirectory / 'data.mcf'
        assert extractedMcf.is_file()

        for fileName, sourceBytes in sourceFiles:
            extractedFile = outputDirectory / fileName
            assert extractedFile.is_file(), f'{fileName} was not extracted'

            # mcfx.py deliberately trims any non-XML trailing data from the
            # album's data.mcf.  Every other contained file should be exact.
            if not fileName.endswith('.mcf'):
                assert extractedFile.read_bytes() == sourceBytes


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-s']))
