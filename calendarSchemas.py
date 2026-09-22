"""Load CEWE calendar colour-scheme definitions when they are available."""

from dataclasses import dataclass
import logging
from pathlib import Path

from lxml import etree
from reportlab.lib import colors


@dataclass(frozen=True)
class CalendarCellStyle:
    """Foreground and optional opaque background for one calendar cell type."""

    text_colour: colors.Color
    background_colour: colors.Color | None


CalendarSchemas = dict[str, dict[str, CalendarCellStyle]]


def colourFromHex(value, fallback=None):
    """Convert CEWE's ``#RRGGBB`` or ``#RRGGBBAA`` notation to a colour.

    A missing colour, and CEWE's explicit transparent form (alpha ``00``),
    deliberately become ``fallback`` rather than an opaque black rectangle.
    """
    if not value or len(value) < 7 or (len(value) >= 9 and value[7:9] == '00'):
        return fallback
    return colors.HexColor(value[:7])


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
                    colourFromHex(cell.get('bgcolor')))
        if cellStyles:
            schemas[schemaName] = cellStyles
    logging.info('Loaded %d calendar colour schemes from %s', len(schemas), schemaFile)
    return schemas


def applyCalendarSchemaSubstitutions(schemas: CalendarSchemas,
                                     definitions: str) -> CalendarSchemas:
    """Alias MCF scheme names to locally available replacement schemes.

    ``definitions`` is the newline-separated ``source, replacement`` value
    from the optional ``[CALENDAR]`` INI section.  This lets a test use a
    small invented schema while retaining the editor's original MCF value.
    """
    substitutedSchemas = dict(schemas)
    for definition in definitions.splitlines():
        if not definition.strip():
            continue
        sourceAndTarget = [part.strip() for part in definition.split(',', 1)]
        if len(sourceAndTarget) != 2 or not all(sourceAndTarget):
            logging.warning('Ignoring invalid calendar schema substitution: %r',
                            definition)
            continue
        source, target = sourceAndTarget
        replacement = schemas.get(target)
        if replacement is None:
            logging.warning(
                'Calendar schema substitution %r cannot use missing schema %r',
                source, target)
            continue
        substitutedSchemas[source] = replacement
        logging.info('Using calendar schema %s in place of %s', target, source)
    return substitutedSchemas
