"""Load CEWE calendar colour-scheme definitions when they are available."""

from dataclasses import dataclass
import logging
from pathlib import Path

from lxml import etree
from reportlab.lib import colors

from .substitutions import applyCalendarSubstitutions


@dataclass(frozen=True)
class CalendarCellStyle:
    """Foreground and optional opaque background for one calendar cell type."""

    text_colour: colors.Color
    background_colour: colors.Color | None
    border_colour: colors.Color | None = None


@dataclass(frozen=True)
class CalendarSchema:
    """The cell styles and grid colour belonging to one named CEWE schema."""

    cell_styles: dict[str, CalendarCellStyle]
    grid_colour: colors.Color | None = None


CalendarSchemas = dict[str, CalendarSchema]


def colourFromHex(value, fallback=None):
    """Convert CEWE's calendar colour notation to a ReportLab colour.

    CEWE uses more than one spelling in its supplied resources: ``#RRGGBB``,
    CSS's short ``#RGB`` form, bare ``RRGGBB``,
    ``RRGGBB,opacity-percent``, and ``transparent``.  A missing or transparent
    colour deliberately becomes ``fallback`` rather than an opaque black
    rectangle.
    """
    if not value:
        return fallback
    colourValue, separator, opacity = value.strip().lower().partition(',')
    if colourValue == 'transparent':
        return fallback
    if colourValue.startswith('#'):
        colourValue = colourValue[1:]
    if len(colourValue) in (3, 4):
        colourValue = ''.join(component * 2 for component in colourValue)
    if len(colourValue) not in (6, 8):
        logging.warning('Ignoring invalid CEWE calendar colour %r', value)
        return fallback
    try:
        colour = colors.HexColor('#' + colourValue[:6])
    except ValueError:
        logging.warning('Ignoring invalid CEWE calendar colour %r', value)
        return fallback
    if len(colourValue) == 8 and colourValue[6:8] == '00':
        return fallback
    if separator:
        try:
            alpha = max(0, min(100, float(opacity))) / 100
        except ValueError:
            logging.warning('Ignoring invalid CEWE calendar opacity %r', value)
            return colour
        return colors.Color(colour.red, colour.green, colour.blue, alpha=alpha)
    return colour


def loadCalendarSchemas(ceweFolder: str | None) -> CalendarSchemas:
    """Load named calendar schemes supplied by a CEWE installation.

    Test fixtures can point ``cewe_folder`` at a small local resource tree,
    which exercises precisely the same parsing path without distributing CEWE
    resource data.
    """
    if not ceweFolder:
        return {}
    schemaFile = Path(ceweFolder) / 'Resources' / 'calendar_schema.xml'
    if not schemaFile.is_file():
        return {}
    try:
        root = etree.parse(str(schemaFile)).getroot()
    except (OSError, etree.XMLSyntaxError) as exception:
        logging.warning('Could not read calendar colour schemas from %s: %s',
                        schemaFile, exception)
        return {}

    schemas: CalendarSchemas = {}
    for calendarArea in root.findall('.//calendararea'):
        schemaName = calendarArea.get('schema')
        if not schemaName:
            continue
        cellStyles = {}
        for cell in calendarArea.findall('cell'):
            cellType = cell.get('type')
            if cellType:
                cellStyles[cellType] = CalendarCellStyle(
                    colourFromHex(cell.get('textcolor'), colors.black),
                    colourFromHex(cell.get('bgcolor')),
                    colourFromHex(cell.get('bordercolor')))
        if cellStyles:
            schemas[schemaName] = CalendarSchema(
                cellStyles, colourFromHex(calendarArea.get('gridcolor')))
    logging.info('Loaded %d calendar colour schemes from %s', len(schemas), schemaFile)
    return schemas


def applyCalendarSchemaSubstitutions(schemas: CalendarSchemas,
                                     definitions: str) -> CalendarSchemas:
    """Alias MCF scheme names to locally available replacement schemes.

    ``definitions`` is the newline-separated ``source, replacement`` value
    from the optional ``[CALENDAR]`` INI section.  This lets a test use a
    small invented schema while retaining the editor's original MCF value.
    """
    return applyCalendarSubstitutions(schemas, definitions, 'schema')
