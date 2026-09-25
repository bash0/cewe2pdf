"""Read CEWE's translated calendar month, weekday, and week labels."""

from dataclasses import dataclass
import logging
from pathlib import Path

from lxml import etree


@dataclass(frozen=True)
class CalendarLocaleNames:
    """The short labels and full month names for one CEWE locale."""

    weekday_names: tuple[str, ...]
    month_names: tuple[str, ...]
    week_name: str


CalendarNames = dict[str, CalendarLocaleNames]


def loadCalendarNames(ceweFolder) -> CalendarNames:
    """Load ``CalendarWeekNames.xml`` from a CEWE or local test resource root."""
    if not ceweFolder:
        return {}
    namesFile = Path(ceweFolder) / 'Resources' / 'international' / \
        'CalendarWeekNames.xml'
    try:
        root = etree.parse(str(namesFile)).getroot()
    except (OSError, etree.XMLSyntaxError) as exception:
        logging.warning('Cannot read calendar name resource %s: %s',
                        namesFile, exception)
        return {}

    names = {}
    for languageElement in root.findall('Language'):
        language = languageElement.get('language')
        country = languageElement.get('country')
        weekdays = tuple(
            day.find('shortname').get('name', '')
            for day in languageElement.findall('./daysofweek/day')
            if day.find('shortname') is not None)
        months = tuple(
            month.find('longname').get('name', '')
            for month in languageElement.findall('./monthnames/month')
            if month.find('longname') is not None)
        weekName = languageElement.find('./weekname/shortname')
        if language and country and len(weekdays) == 7 and len(months) == 12 and \
                weekName is not None:
            names[f'{language}_{country}'] = CalendarLocaleNames(
                weekdays, months, weekName.get('name', ''))
    return names


def calendarNamesForLocale(names: CalendarNames, locale):
    """Return the exact locale, or its sole resource-language equivalent."""
    if locale in names:
        return names[locale]
    language = locale.partition('_')[0]
    matches = [labels for key, labels in names.items()
               if key.partition('_')[0] == language]
    return matches[0] if len(matches) == 1 else None
