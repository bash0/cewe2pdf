"""Read CEWE's localised calendar-event definitions."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
from pathlib import Path

from lxml import etree


@dataclass(frozen=True)
class CalendarEventDefinition:
    """One named CEWE calendar event before its date is resolved for a year."""

    name: str
    honour: str
    fixed_date: str | None = None
    event_id: int | None = None


@dataclass(frozen=True)
class CalendarEvent:
    """One visible event resolved to a calendar date."""

    name: str
    is_public_holiday: bool
    image_path: str | None = None


CalendarEntries = dict[str, tuple[CalendarEventDefinition, ...]]


def _easterSunday(year):
    """Return Gregorian Easter Sunday using the Meeus/Jones/Butcher algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    dayOffset = (32 + 2 * e + 2 * i - h - k) % 7
    month, day = divmod(h + dayOffset + 114, 31)
    return date(year, month, day + 1)


def _dateForEventId(year, eventId):
    """Resolve CEWE's movable and fixed nationwide event identifiers."""
    easter = _easterSunday(year)
    eventDates = {
        2: easter - timedelta(days=3),
        3: easter - timedelta(days=2),
        4: easter,
        5: easter + timedelta(days=1),
        6: date(year, 5, 1),
        7: easter + timedelta(days=39),
        8: easter + timedelta(days=49),
        9: easter + timedelta(days=50),
        15: date(year, 12, 24),
        16: date(year, 12, 25),
        17: date(year, 12, 26),
        18: date(year, 12, 31),
        19: date(year, 1, 1),
        22: easter - timedelta(days=7),
    }
    return eventDates.get(eventId)


def loadCalendarEntries(ceweFolder) -> CalendarEntries:
    """Load locale files shipped with CEWE, returning no entries when absent."""
    if not ceweFolder:
        return {}
    entriesFolder = Path(ceweFolder) / 'Resources' / 'calendarentries'
    entries = {}
    for entryFile in entriesFolder.glob('*.xml'):
        try:
            root = etree.parse(str(entryFile)).getroot()
        except (OSError, etree.XMLSyntaxError) as exception:
            logging.warning(f'Cannot read calendar event resource {entryFile}: {exception}')
            continue
        for country in root.findall('country'):
            locale = country.get('locale')
            if not locale:
                continue
            definitions = []
            for day in country.findall('./nationwide/day'):
                name = day.get('name', '')
                honour = day.get('honor', 'ignore')
                fixedDate = day.get('date')
                eventId = day.get('id')
                if name and (fixedDate or eventId):
                    definitions.append(CalendarEventDefinition(
                        name, honour, fixedDate,
                        int(eventId) if eventId is not None else None))
            entries[locale] = tuple(definitions)
    return entries


def calendarEventsForYear(entries: CalendarEntries, language, year):
    """Resolve visible CEWE event captions and public-holiday dates for ``year``."""
    eventsByDate = {}
    publicHolidays = set()
    for definition in entries.get(language, ()):
        if definition.honour not in ('free', 'show'):
            continue
        if definition.fixed_date:
            pattern = definition.fixed_date
            if pattern.startswith('XXXX-'):
                pattern = f'{year}-{pattern[5:]}'
            try:
                eventDate = date.fromisoformat(pattern)
            except ValueError:
                logging.warning(f'Invalid calendar event date {definition.fixed_date!r}')
                continue
        else:
            eventDate = _dateForEventId(year, definition.event_id)
        if eventDate is None:
            continue
        isPublicHoliday = definition.honour == 'free'
        eventsByDate.setdefault(eventDate, []).append(
            CalendarEvent(definition.name, isPublicHoliday))
        if isPublicHoliday:
            publicHolidays.add(eventDate)
    return publicHolidays, eventsByDate


def personalCalendarEventsForYear(fotobook, year):
    """Resolve the user's optional MCF calendar entries for one rendered year."""
    eventsByDate = {}
    for eventElement in fotobook.findall('./CalendarEvents/CalendarEvent'):
        name = (eventElement.findtext('Name') or '').strip()
        dateTime = (eventElement.findtext('DateTime') or '').strip()
        if not name or not dateTime:
            continue
        try:
            sourceDate = datetime.fromisoformat(dateTime.replace('Z', '+00:00')).date()
        except ValueError:
            logging.warning('Ignoring calendar event with invalid date %r', dateTime)
            continue
        recurring = (eventElement.findtext('Recurrent') or '').strip().lower() == 'yes'
        if recurring:
            try:
                eventDate = date(year, sourceDate.month, sourceDate.day)
            except ValueError:
                # A 29 February birthday understandably has no non-leap-year date.
                continue
        elif sourceDate.year == year:
            eventDate = sourceDate
        else:
            continue
        imagePath = (eventElement.findtext('Image') or '').strip() or None
        eventsByDate.setdefault(eventDate, []).append(
            CalendarEvent(name, False, imagePath))
    return eventsByDate


def resolveCalendarEventImage(imagePath, fallbackFolders):
    """Locate an event image at its MCF path or by basename in fallbacks."""
    if not imagePath:
        return None
    candidates = [Path(imagePath)]
    # MCFs written by the Windows editor retain backslashes even when this
    # renderer runs on GitHub's Linux workers.
    imageName = Path(imagePath.replace('\\', '/')).name
    candidates.extend(Path(folder) / imageName
                      for folder in fallbackFolders)
    for candidate in candidates:
        try:
            if candidate.is_file():
                return str(candidate)
        except OSError:
            continue
    return None
