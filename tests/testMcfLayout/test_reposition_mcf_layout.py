"""Focused tests for page-side layout correction."""

import tempfile
import sqlite3
import unittest
from pathlib import Path

from lxml import etree

from utilities.fixleftrightchanges.fixleftrightchanges import (
    parse_page_map,
    reposition_album,
    reposition_mcf,
)


def _write_mcf(path: Path, right_page_areas: str) -> None:
    path.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<fotobook productname="ALB15">
  <page pagenr="2" type="normalpage">
    <bundlesize width="2000" height="1000"/>
    <area areatype="imagearea"><position left="400" top="100" width="100" height="100"/>
      <image filename="left.jpg"/></area>
    {right_page_areas}
  </page>
</fotobook>''',
        encoding='UTF-8')


class TestParsePageMap(unittest.TestCase):
    def test_expands_single_pages_and_ranges(self):
        self.assertEqual(
            parse_page_map('1-2:1-2, 3-27:4-28'),
            [(1, 1), (2, 2)] + list(zip(range(3, 28), range(4, 29))))

    def test_rejects_unequal_ranges_and_repeated_pages(self):
        with self.assertRaisesRegex(ValueError, 'equal lengths'):
            parse_page_map('1-3:2-3')
        with self.assertRaisesRegex(ValueError, 'only once'):
            parse_page_map('1-2:1-2,2:3')


class TestRepositionMcf(unittest.TestCase):
    def test_moves_all_objects_to_preserve_inner_photo_gap(self):
        right_page = '''
    <area areatype="imagearea"><position left="1080" top="100" width="100" height="100"/>
      <image filename="new-inner.jpg"/></area>
    <area areatype="textarea"><position left="1300" top="300" width="100" height="100"/></area>
    <area areatype="imagearea"><position left="1700" top="100" width="100" height="100"/>
      <image filename="old-inner.jpg"/></area>'''
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'edited.mcf'
            _write_mcf(source, right_page)

            reports, output = reposition_mcf(source, [(2, 3)])

            self.assertEqual(reports[0]['status'], 'moved')
            self.assertEqual(reports[0]['old_anchor'], 'old-inner.jpg')
            self.assertEqual(reports[0]['new_anchor'], 'new-inner.jpg')
            self.assertEqual(reports[0]['margin_gap'], 200)
            self.assertEqual(reports[0]['horizontal_shift'], 120)
            self.assertEqual(output.name, 'edited.repositioned.mcf')

            root = etree.parse(str(output)).getroot()
            positions = [
                area.find('position').get('left')
                for area in root.findall('./page/area')]
            self.assertEqual(positions, ['400', '1200', '1420', '1820'])

    def test_skips_pages_without_photos(self):
        right_page = '''<area areatype="textarea">
          <position left="1300" top="100" width="100" height="100"/>
        </area>'''
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'edited.mcf'
            _write_mcf(source, right_page)

            reports, output = reposition_mcf(
                source, [(2, 3)], dry_run=True)

        self.assertIsNone(output)
        self.assertEqual(reports[0]['status'], 'no photo anchor')

    def test_moves_in_the_opposite_direction_for_a_new_left_page(self):
        left_page = '''
    <area areatype="imagearea"><position left="200" top="100" width="100" height="100"/>
      <image filename="old-inner.jpg"/></area>
    <area areatype="textarea"><position left="600" top="300" width="100" height="100"/></area>'''
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'edited.mcf'
            _write_mcf(source, left_page)

            reports, output = reposition_mcf(source, [(3, 2)])

            self.assertEqual(reports[0]['old_anchor'], 'old-inner.jpg')
            self.assertEqual(reports[0]['new_anchor'], 'left.jpg')
            self.assertEqual(reports[0]['margin_gap'], 200)
            self.assertEqual(reports[0]['horizontal_shift'], 300)
            root = etree.parse(str(output)).getroot()
            positions = [
                area.find('position').get('left')
                for area in root.findall('./page/area')]
            self.assertEqual(positions, ['700', '500', '900'])

    def test_pages_that_keep_their_side_are_not_changed(self):
        right_page = '''<area areatype="imagearea">
          <position left="1700" top="100" width="100" height="100"/>
          <image filename="photo.jpg"/></area>'''
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'edited.mcf'
            _write_mcf(source, right_page)

            reports, _ = reposition_mcf(source, [(3, 5)], dry_run=True)

        self.assertEqual(reports, [])


class TestRepositionMcfx(unittest.TestCase):
    def test_repositions_embedded_mcf_and_preserves_other_archive_files(self):
        right_page = '''
    <area areatype="imagearea"><position left="1080" top="100" width="100" height="100"/>
      <image filename="new-inner.jpg"/></area>
    <area areatype="textarea"><position left="1300" top="300" width="100" height="100"/></area>
    <area areatype="imagearea"><position left="1700" top="100" width="100" height="100"/>
      <image filename="old-inner.jpg"/></area>'''
        with tempfile.TemporaryDirectory() as directory:
            workdir = Path(directory)
            source = workdir / 'album.mcfx'
            output = workdir / 'album.repositioned.mcfx'
            mcf_bytes = _synthetic_mcf(right_page).encode('UTF-8')
            connection = sqlite3.connect(source)
            try:
                connection.execute(
                    'CREATE TABLE Files '
                    '(Filename TEXT PRIMARY KEY, Data BLOB, LastModified INTEGER)')
                connection.executemany(
                    'INSERT INTO Files VALUES (?, ?, ?)',
                    [('data.mcf', mcf_bytes, 1),
                     ('new-inner.jpg', b'photo data', 1)])
                connection.commit()
            finally:
                connection.close()
            original_bytes = source.read_bytes()

            reports, result = reposition_album(source, [(2, 3)], output)

            self.assertEqual(result, output)
            self.assertEqual(reports[0]['horizontal_shift'], 120)
            self.assertEqual(source.read_bytes(), original_bytes)
            connection = sqlite3.connect(output)
            try:
                rows = dict(connection.execute(
                    'SELECT Filename, Data FROM Files'))
            finally:
                connection.close()
            self.assertEqual(rows['new-inner.jpg'], b'photo data')
            extracted_mcf = etree.fromstring(rows['data.mcf'])
            shifted_left = extracted_mcf.find('./page/area/position').get('left')
            self.assertEqual(shifted_left, '400')
            self.assertEqual(
                extracted_mcf.findall('./page/area/position')[1].get('left'),
                '1200')


def _synthetic_mcf(right_page_areas: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<fotobook productname="ALB15">
  <page pagenr="2" type="normalpage">
    <bundlesize width="2000" height="1000"/>
    <area areatype="imagearea"><position left="400" top="100" width="100" height="100"/>
      <image filename="left.jpg"/></area>
    {right_page_areas}
  </page>
</fotobook>'''


if __name__ == '__main__':
    unittest.main()
