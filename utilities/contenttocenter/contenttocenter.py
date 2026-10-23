"""Center selected page content in CEWE albums."""

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


def parse_pages(specification: str) -> list[int]:
    """Expand comma-separated one-based page numbers and inclusive ranges."""
    pages = []
    for segment in specification.split(','):
        parts = segment.strip().split('-', maxsplit=1)
        try:
            start = int(parts[0])
            end = int(parts[1]) if len(parts) == 2 else start
        except ValueError as error:
            raise ValueError(f'Invalid page selection: {segment!r}') from error
        if start < 1 or end < start:
            raise ValueError(f'Invalid one-based page range: {segment!r}')
        pages.extend(range(start, end + 1))

    if not pages:
        raise ValueError('Page selection must contain at least one page')
    if len(set(pages)) != len(pages):
        raise ValueError('Each page may appear only once in the selection')
    return pages


def center_content_mcf(input_path: Path, pages: list[int],
                       output_path: Path | None = None, dry_run: bool = False):
    """Center content on the selected pages of an edited MCF."""
    tree = etree.parse(str(input_path))
    root = tree.getroot()
    _validate_album(root)
    page_geometry = []
    for page_number in pages:
        page_element, page_origin, page_width = _get_page_record(
            root, page_number)
        areas = _areas_on_physical_page(
            page_element, page_origin, page_width)
        page_geometry.append((page_number, page_origin, page_width, areas))

    # Resolve each page's areas before moving any of them. Pages in the same
    # spread share an MCF record, so a centered area could cross the gutter.
    reports = [
        _center_page_content(page_number, page_origin, page_width, areas)
        for page_number, page_origin, page_width, areas in page_geometry]

    if dry_run:
        return reports, None

    if output_path is None:
        output_path = input_path.with_name(
            f'{input_path.stem}.centered{input_path.suffix}')
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


def center_content_album(input_path: Path, pages: list[int],
                         output_path: Path | None = None, dry_run: bool = False):
    """Center content in an MCF or MCFX album without modifying the input."""
    input_path = Path(input_path)
    suffix = input_path.suffix.casefold()
    if suffix not in ('.mcf', '.mcfx'):
        raise ValueError('Input must be an .mcf or .mcfx album file')

    if output_path is None:
        output_path = input_path.with_name(
            f'{input_path.stem}.centered{input_path.suffix}')
    else:
        output_path = Path(output_path)
    if output_path.suffix.casefold() != suffix:
        raise ValueError(f'Output file must also have the {suffix} extension')
    if output_path.resolve() == input_path.resolve():
        raise ValueError('Output path must not overwrite the input album')
    if not dry_run and output_path.exists():
        raise FileExistsError(f'Output file already exists: {output_path}')

    if suffix == '.mcf':
        return center_content_mcf(input_path, pages, output_path, dry_run)

    with tempfile.TemporaryDirectory(prefix='contenttocenter-') as temporary_path:
        extracted_directory = Path(temporary_path) / 'extracted'
        extracted_directory.mkdir()
        _, extracted_mcf = _unpack_mcfx(input_path, extracted_directory)
        if dry_run:
            return center_content_mcf(extracted_mcf, pages, dry_run=True)

        modified_mcf = extracted_directory / 'centered.mcf'
        reports, _ = center_content_mcf(
            extracted_mcf, pages, output_path=modified_mcf)
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
# Keep geometry intermediates named so reported content bounds and the applied
# translation use the same explicit values.
def _center_page_content(page_number: int, page_origin: float,
                         page_width: float, areas: list) -> dict:
    if not areas:
        return {
            'page': page_number,
            'status': 'no areas'}

    page_left = page_origin
    page_right = page_origin + page_width
    all_bounds = [bounds for _, bounds in areas]
    content_left = min(bounds[0] for bounds in all_bounds)
    content_right = max(bounds[1] for bounds in all_bounds)
    displacement = (
        (page_left + page_right - content_left - content_right) / 2)

    for area, _ in areas:
        position = area.find('position')
        left = _read_number(position.get('left'))
        position.set('left', _format_number(left + displacement))

    moved_left = content_left + displacement
    moved_right = content_right + displacement
    return {
        'page': page_number,
        'status': (
            'moved'
            if not math.isclose(displacement, 0, abs_tol=0.01)
            else 'already aligned'),
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
                f'Cannot find the spread record for page {page_number}')
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description='Center content on selected CEWE album pages.')
    parser.add_argument(
        'album', type=Path,
        help='Edited MCF or MCFX album')
    parser.add_argument(
        '--pages', required=True,
        help='One-based pages to center, as comma-separated numbers or ranges, e.g. 2-65')
    parser.add_argument(
        '--output', type=Path,
        help='Output album (default: <input>.centered.<extension>); input is never overwritten')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Report content bounds and horizontal offsets without writing an MCF')
    args = parser.parse_args(argv)

    try:
        pages = parse_pages(args.pages)
        reports, output_path = center_content_album(
            args.album, pages, args.output, dry_run=args.dry_run)
    except (OSError, ValueError, sqlite3.Error, etree.XMLSyntaxError) as error:
        parser.error(str(error))

    moved_pages = 0
    for report in reports:
        status = report['status']
        if status == 'moved':
            moved_pages += 1
            print(
                f"Page {report['page']}: "
                f"content centered with {report['horizontal_shift']:.2f} "
                'MCF units horizontal shift; '
                f"content bounds {report['content_bounds_after']}.")
        else:
            print(
                f"Page {report['page']}: "
                f"{status}; no movement applied.")

    if args.dry_run:
        print(
            f'Dry run: {len(reports)} page(s) selected; '
            f'{moved_pages} would move.')
    else:
        print(
            f'Wrote {output_path}; {len(reports)} page(s) selected, '
            f'{moved_pages} moved.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
