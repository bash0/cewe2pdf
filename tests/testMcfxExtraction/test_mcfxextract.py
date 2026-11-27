"""Standalone extraction and the converter cache share the same archive reader."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from contextlib import closing
from hashlib import sha256
import os
import sqlite3
import subprocess

import pytest

from infrastructure.mcfx_archive import extract_mcfx
from mcfx import unpackMcfx


XML = b'<?xml version="1.0" encoding="UTF-8"?><fotobook imagedir=""><opaque keep="yes"/></fotobook>'


def make_archive(path, members):
    with closing(sqlite3.connect(path)) as connection:
        connection.execute('CREATE TABLE Files(Filename TEXT, Data BLOB, LastModified)')
        connection.executemany('INSERT INTO Files VALUES (?, ?, ?)', members)
        connection.commit()
    return path


def test_extracts_all_resources_and_trims_only_main_document(tmp_path):
    picture = bytes(range(256))
    backup = XML + b'\x00\xfbbackup tail'
    archive = make_archive(tmp_path / 'album #1.mcfx', [
        ('data.mcf', XML + b'\r\n\0' + b'\xfb' * 4000, b'non-numeric'),
        ('pictures\\original-æ.jpg', picture, 0),
        ('folderid.xml', b'<opaque/>', 0),
        ('data.mcf~', backup, 0)])
    before, cwd = sha256(archive.read_bytes()).digest(), Path.cwd()
    output = tmp_path / 'extracted'
    result = extract_mcfx(archive, output)
    assert result.mcf_path == output / 'data.mcf'
    assert result.files_written == 4
    assert result.bytes_written == len(XML) + len(picture) + len(b'<opaque/>') + len(backup)
    assert result.mcf_path.read_bytes() == XML
    assert (output / 'pictures/original-æ.jpg').read_bytes() == picture
    assert (output / 'data.mcf~').read_bytes() == backup
    assert Path.cwd() == cwd and sha256(archive.read_bytes()).digest() == before
    # No SQLite handle remains open when a caller renames the input on Windows.
    archive.rename(tmp_path / 'closed.mcfx')


def test_cli_works_without_site_packages_and_refuses_an_existing_destination(tmp_path):
    archive = make_archive(tmp_path / 'album.mcfx', [('data.mcf', XML, 0)])
    command = [sys.executable, '-S', '-m', 'utilities.mcfxextract.mcfxextract', str(archive)]
    first = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stderr
    assert f'1 files ({len(XML):,} bytes)' in first.stdout
    output = tmp_path / 'album'
    assert (output / 'data.mcf').read_bytes() == XML
    sentinel = output / 'keep.txt'
    sentinel.write_bytes(b'never overwrite')
    second = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    assert second.returncode == 1 and 'Output already exists' in second.stderr
    assert sentinel.read_bytes() == b'never overwrite'
    explicit = tmp_path / 'explicit output'
    third = subprocess.run(command + ['-o', str(explicit)], cwd=PROJECT_ROOT,
        capture_output=True, text=True, check=False)
    assert third.returncode == 0 and (explicit / 'data.mcf').read_bytes() == XML


@pytest.mark.parametrize('members, message', [
    ([('data.mcf', XML, 0), ('../escaped.jpg', b'no', 0)], 'Unsafe'),
    ([('data.mcf', XML, 0), ('pictures/a.jpg', b'a', 0), ('pictures/A.jpg', b'b', 0)], 'Duplicate'),
    ([('data.mcf', XML, 0), ('other.mcf', XML, 0)], 'exactly one'),
    ([('data.mcf', b'<fotobook>broken', 0)], 'closing </fotobook>')])
def test_rejects_unsafe_or_invalid_archives_before_writing(tmp_path, members, message):
    archive = make_archive(tmp_path / 'bad.mcfx', members)
    output = tmp_path / 'output'
    with pytest.raises(ValueError, match=message):
        extract_mcfx(archive, output)
    assert not output.exists() and not (tmp_path / 'escaped.jpg').exists()


def test_missing_input_does_not_create_a_database_or_output(tmp_path):
    archive = tmp_path / 'missing.mcfx'
    with pytest.raises(FileNotFoundError):
        extract_mcfx(archive, tmp_path / 'output')
    assert not archive.exists() and not (tmp_path / 'output').exists()


def test_converter_cache_and_temporary_lifetime_are_preserved(tmp_path):
    archive = make_archive(tmp_path / 'album.mcfx', [('data.mcf', XML, 0), ('photo.jpg', b'first', 0)])
    cache = tmp_path / 'cache'
    temporary, document = unpackMcfx(archive, cache)
    assert temporary is None and document == cache / 'data.mcf'
    photo = cache / 'photo.jpg'
    photo.write_bytes(b'cached')
    future = archive.stat().st_mtime + 60
    os.utime(photo, (future, future))
    unpackMcfx(archive, cache)
    assert photo.read_bytes() == b'cached'
    with closing(sqlite3.connect(archive)) as connection:
        connection.execute('UPDATE Files SET Data=?, LastModified=? WHERE Filename=?',
            (b'new version', (future + 60) * 1000, 'photo.jpg'))
        connection.commit()
    unpackMcfx(archive, cache)
    assert photo.read_bytes() == b'new version'
    temporary, document = unpackMcfx(archive, None)
    assert document.is_file()
    temporary.cleanup()
    assert not document.exists()


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__]))
