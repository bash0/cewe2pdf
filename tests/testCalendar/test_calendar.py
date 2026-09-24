"""Render the supported CEWE calendar fixtures and compare approved results."""

from datetime import date, datetime
from pathlib import Path
import sys

import pikepdf
import pytest
from lxml import etree
from reportlab.lib import colors

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from compare_pdf import ComparePDF, ShowDiffsStyle  # type: ignore
from calendarAreas import (_calendarHolidayEmphasis, _calendarWeekNumberSuffix,
                           _calendarWeekNumbers,
                           _captionCellForEvent,
                           _fontName, _weekRowHeights, _wrapCalendarCaption)
from calendarEntries import (CalendarEvent, personalCalendarEventsForYear,
                             resolveCalendarEventImage)
from calendarLayouts import CalendarCellLayout
from conversionState import ConversionState
from calendarLayouts import applyCalendarLayoutSubstitutions, loadCalendarLayouts
from calendarEntries import calendarEventsForYear, loadCalendarEntries
from calendarNames import calendarNamesForLocale, loadCalendarNames
from calendarSchemas import (applyCalendarSchemaSubstitutions, colourFromHex,
                             loadCalendarSchemas)
from cewe2pdf import convertMcf
from testutils import getLatestResultFile


TEST_DIRECTORY = Path(__file__).parent


def test_minimalCalendarSchemaIsLoaded():
    """The test resource exercises built-in-style colours without CEWE data."""
    schemas = loadCalendarSchemas(str(PROJECT_ROOT / 'tests'))
    substitutedSchemas = applyCalendarSchemaSubstitutions(
        schemas, 'new_15012019_160949, cewe2pdf-test-yellow-weekends')
    styles = substitutedSchemas['new_15012019_160949'].cell_styles

    assert styles['CALENDAR_CELL_TYPE_WEEKDAY'].background_colour is not None
    assert styles['CALENDAR_CELL_TYPE_SUNDAY'].background_colour is not None
    assert styles['CALENDAR_CELL_TYPE_SUNDAY'].text_colour.red > 0.5
    assert styles['CALENDAR_CELL_TYPE_SUNDAY'].text_colour.green < 0.2


def test_calendarColourVariantsFromCeweResources():
    """CEWE's shipped XML also uses bare hexadecimal and opacity spellings."""
    assert colourFromHex('545454') == colors.HexColor('#545454')
    assert colourFromHex('#333') == colors.HexColor('#333333')
    assert colourFromHex('transparent', colors.black) == colors.black
    translucentWhite = colourFromHex('ffffff,80')
    assert translucentWhite == colors.Color(1, 1, 1, alpha=0.8)


def test_minimalCalendarLayoutIsLoaded():
    """The no-CEWE resource provides fixed base sizes for calendar cells."""
    layouts = loadCalendarLayouts(str(PROJECT_ROOT / 'tests'))
    substitutedLayouts = applyCalendarLayoutSubstitutions(
        layouts, 'OneWeekPerRow (2), cewe2pdf-test-week-grid')
    weekGrid = substitutedLayouts['OneWeekPerRow (2)']

    assert weekGrid['CALENDAR_CELL_TYPE_WEEKDAY'].font_size == 14
    assert weekGrid['CALENDAR_CELL_TYPE_HEAD_WEEKDAY'].font_size == 16
    assert weekGrid['CALENDAR_CELL_TYPE_SUNDAY'].bold


def test_calendarEventsComeFromTheLocaleResource():
    """Recurring, movable, and year-specific CEWE events retain their meaning."""
    entries = loadCalendarEntries(str(PROJECT_ROOT / 'tests'))

    publicHolidays, captions = calendarEventsForYear(entries, 'nb_NO', 2028)

    assert date(2028, 5, 1) in publicHolidays
    assert [event.name for event in captions[date(2028, 4, 1)]] == ['Første April']
    assert [event.name for event in captions[date(2028, 5, 8)]] == ['Frigjøringsdagen']
    assert [event.name for event in captions[date(2028, 5, 25)]] == ['Kr. Himmelfartsdag']
    assert [event.name for event in captions[date(2028, 3, 26)]] == ['Sommertid']
    assert [(event.name, event.is_public_holiday)
            for event in captions[date(2028, 5, 17)]] == [
                ('Første etikett', True), ('Andre etikett', False)]
    assert date(2028, 3, 8) not in captions

    _, captions2027 = calendarEventsForYear(entries, 'nb_NO', 2027)
    assert [event.name for event in captions2027[date(2027, 2, 7)]] == [
        'Fastelavn']
    assert [event.name for event in captions2027[date(2027, 2, 14)]] == [
        'St. Valentines dag', 'Morsdag']


def test_missingCalendarLocaleDoesNotInventNorwegianEvents():
    """A calendar without its requested locale resource remains unannotated."""
    publicHolidays, captions = calendarEventsForYear({}, 'en_GB', 2028)

    assert not publicHolidays
    assert not captions


def test_calendarEventsUseTheRequestedBritishEnglishLocale():
    """The landscape fixture's en_GB locale cannot accidentally use nb_NO data."""
    entries = loadCalendarEntries(str(PROJECT_ROOT / 'tests'))

    publicHolidays, captions = calendarEventsForYear(entries, 'en_GB', 2028)

    assert date(2028, 1, 1) in publicHolidays
    assert [event.name for event in captions[date(2028, 1, 1)]] == [
        "New Year's Day"]


def test_calendarNamesUseTheRequestedResourceLocale():
    """Week, weekday, and month labels come from CEWE's locale resource."""
    names = loadCalendarNames(str(PROJECT_ROOT / 'tests'))

    norwegian = calendarNamesForLocale(names, 'nb_NO')
    britishEnglish = calendarNamesForLocale(names, 'en_GB')

    assert norwegian.week_name == 'uke'
    assert norwegian.weekday_names == ('ma', 'ti', 'on', 'to', 'fr', 'lø', 'sø')
    assert norwegian.month_names[0] == 'januar'
    assert britishEnglish.week_name == 'Wk'
    assert britishEnglish.month_names[8] == 'September'


def test_squareCalendarReadsWeekNumbersAndRecurringPersonalEvents():
    """The MCF controls both its ISO-week column and its own entries."""
    root = etree.parse(str(TEST_DIRECTORY / 'sq21' / 'sq21.mcf')).getroot()
    fotobook = root.find('fotobook') or root

    assert _calendarWeekNumbers(fotobook) is True
    events = personalCalendarEventsForYear(fotobook, 2027)
    assert [event.name for event in events[date(2027, 9, 23)]] == [
        "Somebody's birthday"]
    assert [event.name for event in events[date(2027, 9, 24)]] == ['No picture']
    assert events[date(2027, 9, 23)][0].image_path.endswith('.jpg')
    assert events[date(2027, 9, 24)][0].image_path is None


def test_a5CalendarUsesTheMcfWeekNumberPunctuation():
    """Week-number formatting comes from the calendar MCF, not its locale."""
    root = etree.parse(str(TEST_DIRECTORY / 'a5l' / 'a5l.mcf')).getroot()
    fotobook = root.find('fotobook') or root

    assert _calendarWeekNumbers(fotobook) is True
    assert _calendarWeekNumberSuffix(fotobook) == '.'


def test_calendarEventImageUsesConfiguredBasenameFallback(tmp_path):
    """A portable fixture can replace the editor's machine-local AppData path."""
    fallbackFolder = tmp_path / 'calendarEventFotos'
    fallbackFolder.mkdir()
    fallbackImage = fallbackFolder / 'editor-event.jpg'
    fallbackImage.write_bytes(b'fixture image')

    assert resolveCalendarEventImage(
        r'C:\\Users\\someone\\AppData\\Local\\CEWE\\editor-event.jpg',
        (str(fallbackFolder),)) == str(fallbackImage)


def test_weekdayHeaderRowIsShallowerThanCalendarWeeks():
    """CEWE's compact weekday header shares the grid height without dominating it."""
    headerHeight, weekHeight = _weekRowHeights(700, 6)

    assert headerHeight < weekHeight
    assert headerHeight + 6 * weekHeight == pytest.approx(700)


def test_holidayCaptionWrapsWithinItsCalendarCell():
    """Long CEWE captions do not extend through a neighbouring date cell."""
    lines = _wrapCalendarCaption('Kr. Himmelfartsdag', 60,
                                 'Helvetica', 8, CalendarCellLayout())

    assert lines == ['Kr.', 'Himmelfartsdag']


def test_showEventCaptionInheritsSundayEmphasis():
    """A Sunday observance is bold even when it is not a public holiday."""
    showEvent = CalendarEvent('Fastelavn', is_public_holiday=False)
    freeEvent = CalendarEvent('Kr. Himmelfartsdag', is_public_holiday=True)
    regularCell = CalendarCellLayout(bold=False)
    sundayCell = CalendarCellLayout(bold=True)
    captionCell = CalendarCellLayout(bold=False)

    assert _captionCellForEvent(showEvent, captionCell, regularCell, True).bold is False
    assert _captionCellForEvent(showEvent, captionCell, sundayCell, True).bold is True
    assert _captionCellForEvent(freeEvent, captionCell, regularCell, True).bold is True
    assert _captionCellForEvent(freeEvent, captionCell, regularCell, False).bold is False


def test_a5CalendarSeparatesHolidayNamesFromHolidayEmphasis():
    """The MCF can show names without applying CEWE's holiday emphasis."""
    root = etree.parse(str(TEST_DIRECTORY / 'a5l' / 'a5l.mcf')).getroot()
    fotobook = root.find('fotobook') or root

    assert _calendarHolidayEmphasis(fotobook) is False


def test_calendarFontUsesTheConfiguredMissingFontSubstitution():
    """Calendar text shares the normal text area's missing-font policy."""
    class EmptyFontCanvas:
        @staticmethod
        def getAvailableFonts():
            return ()

    state = ConversionState(
        missing_font_substitutions={'FranklinGothic': 'Courier'})

    assert _fontName('FranklinGothic', EmptyFontCanvas(), {}, state) == 'Courier'


def buildAndCompareCalendar(fixtureName, pageDimensions, caplog):
    """Render one fixture, retaining its PDF for manual or pixel comparison."""
    sourceMcf = TEST_DIRECTORY / fixtureName / f'{fixtureName}.mcf'
    date = datetime.today().strftime('%Y%m%d')
    outputPdf = sourceMcf.with_name(f'{fixtureName}.mcf.{date}.pdf')
    approvedPdf = getLatestResultFile(str(Path(TEST_DIRECTORY.name) / fixtureName),
                                      f'{fixtureName}.mcf.*.pdf')

    if outputPdf.exists():
        outputPdf.unlink()

    assert convertMcf(str(sourceMcf), keepDoublePages=False,
                      outputFileName=str(outputPdf))

    with pikepdf.Pdf.open(outputPdf) as renderedPdf:
        assert len(renderedPdf.pages) == 13
        firstPage = renderedPdf.pages[0]
        pageBox = firstPage.mediabox
        assert round(float(pageBox[2])) == pageDimensions[0]
        assert round(float(pageBox[3])) == pageDimensions[1]

    assert not any('Unsupported calendar layout' in record.message
                   for record in caplog.records)

    if approvedPdf is None:
        print(f'No approved PDF result for {fixtureName} to compare with')
        return

    print(f'Compare {outputPdf} with {approvedPdf}')
    comparison = ComparePDF([str(outputPdf), approvedPdf],
                            ShowDiffsStyle.Nothing)
    try:
        assert comparison.compare(), 'Pixel comparison failed'
    finally:
        comparison.cleanup()


@pytest.mark.parametrize(('fixtureName', 'pageDimensions'), [
    ('a4p', (595, 842)),
    ('a4l', (842, 595)),
    ('a5l', (595, 420)),
    ('sq21', (595, 595)),
])
def test_calendarRendersIndependentPages(caplog, fixtureName, pageDimensions):
    """Each fixture produces its cover plus twelve independent month pages."""
    buildAndCompareCalendar(fixtureName, pageDimensions, caplog)


if __name__ == '__main__':
    import pytest
    raise SystemExit(pytest.main([__file__, '-s']))
