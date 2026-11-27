"""Read-only extraction of CEWE's SQLite MCFX containers, without PDF dependencies."""

from contextlib import closing
from dataclasses import dataclass
import logging
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import sqlite3


@dataclass(frozen=True)
class ExtractionResult:
    """The extracted document and the bytes actually written (excluding padding)."""

    mcf_path: Path
    files_written: int
    bytes_written: int


def _member_path(filename):
    """Use portable member names, rejecting paths that could escape extraction."""
    if not isinstance(filename, str) or not filename:
        raise ValueError('MCFX contains an empty or non-text filename')
    # Accept nested Windows/POSIX paths on either platform, but not drive paths,
    # device names or Windows alternate-data-stream syntax.
    portable = filename.replace('\\', '/')
    parts = portable.split('/')
    if (portable.startswith('/') or ':' in portable or any(part in ('', '.', '..') for part in parts)
            or any(character in '<>"|?*' or ord(character) < 32 for character in portable)
            or any(part.endswith((' ', '.')) or PureWindowsPath(part).is_reserved() for part in parts)):
        raise ValueError(f'Unsafe MCFX member path: {filename!r}')
    return Path(*PurePosixPath(portable).parts)


def _archive_members(connection):
    members = []
    keys = set()
    for filename, modified, data_type in connection.execute('SELECT Filename, LastModified, typeof(Data) FROM Files'):
        relative = _member_path(filename)
        key = relative.as_posix().casefold()
        if key in keys:
            raise ValueError(f'Duplicate MCFX member path: {filename!r}')
        if data_type != 'blob':
            raise ValueError(f'MCFX member is not binary data: {filename!r}')
        keys.add(key)
        members.append((filename, relative, modified))
    for _filename, relative, _modified in members:
        if any(parent.as_posix().casefold() in keys for parent in relative.parents if parent != Path('.')):
            raise ValueError(f'MCFX member conflicts with a directory: {relative}')
    return members


def _document_data(connection, members):
    documents = [filename for filename, relative, _modified in members if relative.suffix.casefold() == '.mcf']
    if len(documents) != 1:
        raise ValueError('MCFX must contain exactly one .mcf document')
    filename = documents[0]
    data = connection.execute('SELECT Data FROM Files WHERE Filename = ?', (filename,)).fetchone()[0]
    # Native document BLOBs may reserve 4 MiB and append 0xFB/other bytes.
    # Keep the XML byte-for-byte through its end tag, not the trailing storage.
    end_tag = b'</fotobook>'
    end = data.find(end_tag)
    if end == -1:
        raise ValueError('The MCFX document has no closing </fotobook> tag')
    return filename, data[:end + len(end_tag)]


def _member_timestamp(modified, fallback):
    try:
        timestamp = float(modified) / 1000
    except (TypeError, ValueError, OverflowError):
        return fallback, True
    if not math.isfinite(timestamp):
        return fallback, True
    return timestamp or fallback, False


def _write_members(connection, members, document, destination, fallback, reuse_existing):
    files_written = 0
    bytes_written = 0
    warned_timestamp = False
    document_name, document_data = document
    mcf_path = None
    for filename, relative, modified in members:
        target = destination / relative
        if target.is_symlink() or not target.resolve().is_relative_to(destination):
            raise ValueError(f'MCFX member resolves outside its extraction directory: {filename!r}')
        if filename == document_name:
            mcf_path = target
        timestamp, invalid = _member_timestamp(modified, fallback)
        if invalid and not warned_timestamp:
            logging.warning('Ignoring non-numeric Files.LastModified values; using the MCFX file timestamp')
            warned_timestamp = True
        if reuse_existing and target.is_file() and timestamp < target.stat().st_mtime:
            continue
        data = (document_data if filename == document_name else
            connection.execute('SELECT Data FROM Files WHERE Filename = ?', (filename,)).fetchone()[0])
        target.parent.mkdir(parents=True, exist_ok=True)
        # Only the converter's explicit cache mode may replace extracted files.
        with target.open('wb' if reuse_existing else 'xb') as stream:
            stream.write(data)
        files_written += 1
        bytes_written += len(data)
    return ExtractionResult(mcf_path, files_written, bytes_written)


def extract_mcfx(source: Path, destination: Path, *, reuse_existing=False):
    """Extract all members without changing cwd, opening the archive read-only.

    Normally destination must not exist. The converter alone opts into its
    historical timestamp-based extraction cache via reuse_existing. Failures
    raise ordinary exceptions; an I/O failure can leave a partial output folder.
    """
    source = Path(source).resolve()
    destination = Path(destination).absolute()
    if not source.is_file():
        raise FileNotFoundError(f'MCFX input file not found: {source}')
    if destination.is_symlink() or (destination.exists() and not reuse_existing):
        raise FileExistsError(f'Output already exists; choose a new directory: {destination}')
    destination = destination.resolve()
    fallback = source.stat().st_mtime
    # sqlite3's connection context manager does not close the connection.
    # closing() releases handles before callers reopen or clean up files.
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as connection:
        with connection:
            connection.execute('BEGIN')  # Validate and read BLOBs in one database snapshot.
            members = _archive_members(connection)
            document = _document_data(connection, members)
            destination.mkdir(parents=True, exist_ok=reuse_existing)
            return _write_members(connection, members, document, destination, fallback, reuse_existing)
