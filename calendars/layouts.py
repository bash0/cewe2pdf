"""Load CEWE calendar-layout definitions when they are available.

``calendar_layout.xml`` supplies the otherwise absent semantics of a compact
MCF ``calendararea``: its individual cells' base point sizes, emphasis,
alignment, borders and padding.  The MCF supplies the chosen layout name,
font override and size adjustments.
"""

from dataclasses import dataclass
import logging
from pathlib import Path

from lxml import etree

from .substitutions import applyCalendarSubstitutions


@dataclass(frozen=True)
class CalendarCellLayout:
    """The rendering properties CEWE assigns to one type of calendar cell."""

    font_size: float | None = None
    font_face: str | None = None
    bold: bool = False
    text_align: str = ''
    border_type: str = ''
    padding_top: float = 0
    padding_bottom: float = 0
    padding_left: float = 0
    padding_right: float = 0


CalendarLayouts = dict[str, dict[str, CalendarCellLayout]]


def _number(value: str | None) -> float:
    """Read an optional CEWE numeric attribute, accepting decimal commas."""
    try:
        return float((value or '0').replace(',', '.'))
    except ValueError:
        return 0


def loadCalendarLayouts(ceweFolder: str | None) -> CalendarLayouts:
    """Load named calendar layouts from CEWE or from minimal test resources."""
    if not ceweFolder:
        return {}
    layoutFile = Path(ceweFolder) / 'Resources' / 'calendar_layout.xml'
    if not layoutFile.is_file():
        return {}
    try:
        root = etree.parse(str(layoutFile)).getroot()
    except (OSError, etree.XMLSyntaxError) as exception:
        logging.warning('Could not read calendar layouts from %s: %s',
                        layoutFile, exception)
        return {}

    layouts: CalendarLayouts = {}
    for calendarArea in root.findall('.//calendararea'):
        schemaName = calendarArea.get('schema')
        if not schemaName:
            continue
        cells = {}
        for cell in calendarArea.findall('cell'):
            cellType = cell.get('type')
            if not cellType:
                continue
            font = cell.find('font')
            cells[cellType] = CalendarCellLayout(
                font_size=_number(font.get('size')) if font is not None else None,
                font_face=font.get('face') if font is not None else None,
                bold=font is not None and font.get('bold', '').lower() == 'true',
                text_align=cell.get('textalign', ''),
                border_type=cell.get('bordertype', ''),
                padding_top=_number(cell.get('paddingtop')),
                padding_bottom=_number(cell.get('paddingbottom')),
                padding_left=_number(cell.get('paddingleft')),
                padding_right=_number(cell.get('paddingright')))
        if cells:
            layouts[schemaName] = cells
    logging.info('Loaded %d calendar layouts from %s', len(layouts), layoutFile)
    return layouts


def applyCalendarLayoutSubstitutions(layouts: CalendarLayouts,
                                     definitions: str) -> CalendarLayouts:
    """Alias editor layout names to local compatible definitions from the INI."""
    return applyCalendarSubstitutions(layouts, definitions, 'layout')
