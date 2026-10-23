"""Reposition page layouts after CEWE pages change spread sides."""

import argparse
from importlib import import_module
import math
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time

from lxml import etree


def parse_page_map(specification: str) -> list[tuple[int, int]]:
    """Expand comma-separated one-based old:new page pairs and ranges."""
    page_pairs = []
    for segment in specification.split(','):
        sides = segment.strip().split(':')
        if len(sides) != 2:
            raise ValueError(f'Invalid page map segment: {segment!r}')
        old_pages = _parse_page_range(sides[0])
        new_pages = _parse_page_range(sides[1])
        if len(old_pages) != len(new_pages):
            raise ValueError(
                f'Page map ranges must have equal lengths: {segment!r}')
        page_pairs.extend(zip(old_pages, new_pages))

    if not page_pairs:
        raise ValueError('Page map must contain at least one pair')
    if (len({pair[0] for pair in page_pairs}) != len(page_pairs)
            or len({pair[1] for pair in page_pairs}) != len(page_pairs)):
        raise ValueError('Each page may appear only once in a page map')
    return page_pairs


def _parse_page_range(value: str) -> range:
    parts = value.strip().split('-', maxsplit=1)
    try:
        start = int(parts[0])
        end = int(parts[1]) if len(parts) == 2 else start
    except ValueError as error:
        raise ValueError(f'Invalid page range: {value!r}') from error
    if start < 1 or end < start:
        raise ValueError(f'Invalid one-based page range: {value!r}')
    return range(start, end + 1)


def reposition_mcf(input_path: Path, page_map: list[tuple[int, int]],
                   output_path: Path | None = None, dry_run: bool = False):
    """Translate layouts on pages whose left/right side changed.

    ``page_map`` maps old editor page numbers to the corresponding page numbers
    in the already-edited MCF. Source MCF content is not required.
    """
    tree = etree.parse(str(input_path))
    root = tree.getroot()
    _validate_album(root)
    changed_pages = [
        (old_page, new_page)
        for old_page, new_page in page_map
        if old_page % 2 != new_page % 2]
    reports = []
    for old_page, new_page in changed_pages:
        report = _reposition_page(root, old_page, new_page)
        reports.append(report)

    if dry_run:
        return reports, None

    if output_path is None:
        output_path = input_path.with_name(
            f'{input_path.stem}.repositioned{input_path.suffix}')
    if output_path.resolve() == input_path.resolve():
        raise ValueError('Output path must not overwrite the input MCF')
    if output_path.exists():
        raise FileExistsError(f'Output file already exists: {output_path}')

    tree.write(
        str(output_path),
        encoding='UTF-8',
        xml_declaration=True,
        pretty_print=True)
    return reports, output_path


def reposition_album(input_path: Path, page_map: list[tuple[int, int]],
                     output_path: Path | None = None, dry_run: bool = False):
    """Reposition an MCF or MCFX album without modifying the input file."""
    input_path = Path(input_path)
    suffix = input_path.suffix.casefold()
    if suffix not in ('.mcf', '.mcfx'):
        raise ValueError('Input must be an .mcf or .mcfx album file')

    if output_path is None:
        output_path = input_path.with_name(
            f'{input_path.stem}.repositioned{input_path.suffix}')
    else:
        output_path = Path(output_path)
    if output_path.suffix.casefold() != suffix:
        raise ValueError(f'Output file must also have the {suffix} extension')
    if output_path.resolve() == input_path.resolve():
        raise ValueError('Output path must not overwrite the input album')
    if not dry_run and output_path.exists():
        raise FileExistsError(f'Output file already exists: {output_path}')

    if suffix == '.mcf':
        return reposition_mcf(input_path, page_map, output_path, dry_run)

    with tempfile.TemporaryDirectory(prefix='fixleftrightchanges-') as temporary_path:
        extracted_directory = Path(temporary_path) / 'extracted'
        extracted_directory.mkdir()
        _, extracted_mcf = _unpack_mcfx(input_path, extracted_directory)
        if dry_run:
            return reposition_mcf(extracted_mcf, page_map, dry_run=True)

        modified_mcf = extracted_directory / 'repositioned.mcf'
        reports, _ = reposition_mcf(
            extracted_mcf, page_map, output_path=modified_mcf)
        _replace_mcfx_mcf(
            input_path, output_path, extracted_mcf.name, modified_mcf)
        return reports, output_path


def _unpack_mcfx(input_path: Path, extracted_directory: Path):
    """Call the normal MCFX reader when the script is launched by file path."""
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        # A nested script's directory, not the current directory, is sys.path[0].
        sys.path.insert(0, str(project_root))
    return import_module('mcfx').unpackMcfx(
        input_path.resolve(), extracted_directory)


def _replace_mcfx_mcf(input_path: Path, output_path: Path,
                      mcf_filename: str, modified_mcf: Path):
    """Copy an MCFX and replace only its embedded MCF database row."""
    shutil.copy2(input_path, output_path)
    connection = None
    try:
        connection = sqlite3.connect(output_path)
        cursor = connection.execute(
            'UPDATE Files SET Data = ?, LastModified = ? WHERE Filename = ?',
            (modified_mcf.read_bytes(), time.time_ns() // 1_000_000,
             mcf_filename))
        if cursor.rowcount != 1:
            raise ValueError(
                'Could not find exactly one embedded MCF row in the MCFX')
        connection.commit()
    except (OSError, sqlite3.Error, ValueError):
        if connection is not None:
            connection.close()
            connection = None
        output_path.unlink(missing_ok=True)
        raise
    finally:
        if connection is not None:
            connection.close()


def _validate_album(root):
    product_name = root.get('productname', '').upper()
    if not product_name.startswith('ALB'):
        raise ValueError(
            'This utility currently supports CEWE album MCF files only')
    if not root.findall("./page[@type='normalpage']"):
        raise ValueError('The MCF has no normal album pages')


# pylint: disable=too-many-locals
# Keep the geometry intermediates named here so reported anchor bounds and the
# applied translation use the same explicit values.
def _reposition_page(root, old_page: int, new_page: int) -> dict:
    page_element, page_origin, page_width = _get_page_record(root, new_page)
    areas = _areas_on_physical_page(page_element, page_origin, page_width)
    if not areas:
        return {
            'old_page': old_page,
            'new_page': new_page,
            'status': 'no areas'}

    page_left = page_origin
    page_right = page_origin + page_width
    all_bounds = [bounds for _, bounds in areas]
    content_left = min(bounds[0] for bounds in all_bounds)
    content_right = max(bounds[1] for bounds in all_bounds)
    photos = [
        (area, bounds)
        for area, bounds in areas
        if area.get('areatype', '').casefold() in ('imagearea', 'imagebackgroundarea')
        and (area.find('image') is not None or area.find('imagebackground') is not None)]
    if not photos:
        return {
            'old_page': old_page,
            'new_page': new_page,
            'status': 'no photo anchor'}

    old_anchor, new_anchor, old_margin_gap, displacement = (
        _anchor_translation(photos, new_page, page_left, page_right))

    for area, _ in areas:
        position = area.find('position')
        left = _read_number(position.get('left'))
        position.set('left', _format_number(left + displacement))

    moved_left = content_left + displacement
    moved_right = content_right + displacement
    return {
        'old_page': old_page,
        'new_page': new_page,
        'status': (
            'moved'
            if not math.isclose(displacement, 0, abs_tol=0.01)
            else 'already aligned'),
        'old_anchor': _photo_name(old_anchor[0]),
        'new_anchor': _photo_name(new_anchor[0]),
        'margin_gap': old_margin_gap,
        'horizontal_shift': displacement,
        'content_bounds_after': (moved_left, moved_right),
        'page_bounds': (page_left, page_right),
    }


def _get_page_record(root, page_number: int):
    if page_number == 1:
        opening_page = root.find(
            "./page[@pagenr='0'][@type='emptypage'][area]")
        if opening_page is None:
            raise ValueError('Cannot find the opening page 1 area record')
        record = opening_page
        right_side = True
    else:
        record_number = page_number if page_number % 2 == 0 else page_number - 1
        record = root.find(
            f"./page[@pagenr='{record_number}'][@type='normalpage']")
        if record is None:
            raise ValueError(
                f'Cannot find the spread record for new page {page_number}')
        right_side = page_number % 2 == 1

    bundle_size = record.find('bundlesize')
    if bundle_size is None:
        raise ValueError(f'Page {page_number} has no bundle size')
    spread_width = _read_number(bundle_size.get('width'))
    if spread_width <= 0 or spread_width % 2:
        raise ValueError(
            f'Page {page_number} has an invalid double-page bundle width')
    page_width = spread_width / 2
    page_origin = page_width if right_side else 0.0
    return record, page_origin, page_width


def _anchor_translation(photos, new_page, page_left, page_right):
    """Return outer/inner photo anchors and the required horizontal shift."""
    # Once a page changes sides, its old inner edge becomes its outer edge.
    # The outermost photo preserves the old photo-to-margin gap; the photo at
    # the opposite edge becomes the new inner-margin anchor.
    new_page_is_right = new_page % 2 == 1
    if new_page_is_right:
        old_anchor = max(photos, key=lambda item: item[1][1])
        new_anchor = min(photos, key=lambda item: item[1][0])
        margin_gap = page_right - old_anchor[1][1]
        desired_new_edge = page_left + margin_gap
        displacement = desired_new_edge - new_anchor[1][0]
    else:
        old_anchor = min(photos, key=lambda item: item[1][0])
        new_anchor = max(photos, key=lambda item: item[1][1])
        margin_gap = old_anchor[1][0] - page_left
        desired_new_edge = page_right - margin_gap
        displacement = desired_new_edge - new_anchor[1][1]
    return old_anchor, new_anchor, margin_gap, displacement


def _areas_on_physical_page(page_element, page_origin, page_width):
    areas = []
    page_left = page_origin
    page_right = page_origin + page_width
    for area in page_element.findall('area'):
        position = area.find('position')
        if position is None:
            continue
        bounds = _area_horizontal_bounds(position)
        centre = (bounds[0] + bounds[1]) / 2
        if page_left <= centre <= page_right:
            areas.append((area, bounds))
    return areas


def _area_horizontal_bounds(position):
    left = _read_number(position.get('left'))
    width = _read_number(position.get('width'))
    height = _read_number(position.get('height'))
    rotation = math.radians(_read_number(position.get('rotation', '0')))
    rotated_width = abs(width * math.cos(rotation)) + abs(height * math.sin(rotation))
    centre = left + width / 2
    return centre - rotated_width / 2, centre + rotated_width / 2


def _read_number(value: str | None) -> float:
    if value is None:
        raise ValueError('Missing numeric MCF position')
    return float(value.replace(',', '.'))


def _format_number(value: float) -> str:
    if math.isclose(value, round(value), abs_tol=1e-9):
        return str(round(value))
    return f'{value:.6f}'.rstrip('0').rstrip('.')


def _photo_name(area) -> str:
    image = area.find('image')
    if image is None:
        image = area.find('imagebackground')
    return Path(image.get('filename', '(unnamed photo)')).name


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description='Reposition layouts on CEWE album pages moved to the other spread side.')
    parser.add_argument(
        'album', type=Path,
        help='Edited MCF or MCFX after page insertion, deletion or reorder')
    parser.add_argument(
        '--page-map', required=True,
        help='One-based old:new editor-page pairs or equal-length ranges, e.g. 1-25:2-26')
    parser.add_argument(
        '--output', type=Path,
        help='Output album (default: <input>.repositioned.<extension>); input is never overwritten')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Report anchor photos and horizontal offsets without writing an MCF')
    args = parser.parse_args(argv)

    try:
        page_map = parse_page_map(args.page_map)
        reports, output_path = reposition_album(
            args.album, page_map, args.output, dry_run=args.dry_run)
    except (OSError, ValueError, sqlite3.Error, etree.XMLSyntaxError) as error:
        parser.error(str(error))

    changed_pages = 0
    for report in reports:
        status = report['status']
        if status == 'moved':
            changed_pages += 1
            print(
                f"Old page {report['old_page']} -> new page {report['new_page']}: "
                f"{report['old_anchor']} to {report['new_anchor']}, "
                f"{report['horizontal_shift']:.2f} MCF units horizontally "
                f"(old margin gap {report['margin_gap']:.2f}).")
        else:
            print(
                f"Old page {report['old_page']} -> new page {report['new_page']}: "
                f"{status}; no movement applied.")

    if args.dry_run:
        print(f'Dry run: {changed_pages} page(s) would move.')
    else:
        print(f'Wrote {output_path}; {changed_pages} page(s) moved.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
