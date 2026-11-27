"""Extract all embedded files from a CEWE MCFX archive without generating a PDF."""

import argparse
from pathlib import Path
import sqlite3

from infrastructure.mcfx_archive import extract_mcfx


def main(argv=None):
    """Extract into a new directory and report the actual output size."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path, help='CEWE .mcfx file to extract')
    parser.add_argument('-o', '--output', type=Path,
        help='New output directory (default: album name beside the archive)')
    args = parser.parse_args(argv)
    destination = args.output or args.archive.with_suffix('')
    try:
        result = extract_mcfx(args.archive, destination)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f'mcfxextract: {error}\n')
    print(f'Extracted {result.files_written} files ({result.bytes_written:,} bytes) to {destination.resolve()}')
    print(f'MCF: {result.mcf_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
