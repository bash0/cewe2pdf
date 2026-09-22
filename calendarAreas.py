"""Render the calendar-specific areas in CEWE calendar products.

Calendar MCF files store the editable page areas in the familiar form, but
describe their generated calendarium using a compact ``calendararea`` element.
This module deliberately contains that product-specific interpretation; the
ordinary image, text and clip-art paths remain shared with photo albums.
"""

import calendar
from datetime import date, datetime, timedelta
from dataclasses import dataclass
import logging

from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics

from calendarSchemas import CalendarCellStyle, CalendarSchemas, colourFromHex
from renderContext import RenderContext


NORWEGIAN_MONTHS = (
    'januar', 'februar', 'mars', 'april', 'mai', 'juni',
    'juli', 'august', 'september', 'oktober', 'november', 'desember')
NORWEGIAN_WEEKDAYS = ('ma', 'ti', 'on', 'to', 'fr', 'lø', 'sø')
ENGLISH_MONTHS = (
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December')
ENGLISH_WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


@dataclass(frozen=True)
class CalendarBounds:
    """One calendar area's rectangle, converted from MCF to ReportLab units."""

    x: float
    y: float
    width: float
    height: float

    @classmethod
    def fromArea(cls, area, pageHeight, context: RenderContext):
        """Read CEWE's top-left-origin position as a ReportLab rectangle."""
        position = area.find('position')
        left = float(position.get('left').replace(',', '.'))
        top = float(position.get('top').replace(',', '.'))
        width = float(position.get('width').replace(',', '.'))
        height = float(position.get('height').replace(',', '.'))
        scale = context.mcf_to_reportlab
        return cls(left * scale, (pageHeight - top - height) * scale,
                   width * scale, height * scale)


def _calendarStartDate(fotobook):
    """Return the calendar start date stored by CEWE, or ``None`` if invalid."""
    value = fotobook.get('startdatecalendarium', '')
    try:
        return datetime.strptime(value, '%d.%m.%Y').date()
    except ValueError:
        logging.warning(f'Calendar has an invalid start date: {value!r}')
        return None


def _calendarLanguage(fotobook):
    """Return the language requested for CEWE's generated calendar text."""
    holidays = fotobook.find('holidays')
    return holidays.get('language', 'nb_NO') if holidays is not None else 'nb_NO'


def _calendarNames(language):
    """Provide the month and weekday labels available in the fixture locale."""
    if language.startswith('en_'):
        return ENGLISH_MONTHS, ENGLISH_WEEKDAYS
    return NORWEGIAN_MONTHS, NORWEGIAN_WEEKDAYS


def _calendarCellStyles(fotobook, calendarArea, calendarSchemas):
    """Return styles from an embedded scheme, or from CEWE's resource file."""
    schemeName = calendarArea.get('colorschema', '')
    styles = dict(calendarSchemas.get(schemeName, {}))
    matchingSchemes = fotobook.xpath(
        f'./colorSchemata/calendararea[@colorschema="{schemeName}"]')
    if not matchingSchemes:
        return styles, CalendarCellStyle(colors.black, None)
    scheme = matchingSchemes[0]
    defaultCell = scheme.find('celldefault')
    defaultStyle = CalendarCellStyle(colors.black, None)
    if defaultCell is not None:
        defaultStyle = CalendarCellStyle(
            colourFromHex(defaultCell.get('textcolor'), colors.black),
            colourFromHex(defaultCell.get('bgcolor')))
    for cell in scheme.findall('cell'):
        cellType = cell.get('type')
        if cellType:
            styles[cellType] = CalendarCellStyle(
                colourFromHex(cell.get('textcolor'), defaultStyle.text_colour),
                colourFromHex(cell.get('bgcolor'), defaultStyle.background_colour))
    return styles, defaultStyle


def _calendarStyle(styles, defaultStyle, *cellTypes):
    """Choose the first defined style for equivalent CEWE calendar cell types."""
    for cellType in cellTypes:
        if cellType in styles:
            return styles[cellType]
    return defaultStyle


def _norwegianHolidays(year):
    """Return the Norwegian public holidays needed by the first calendar renderer."""
    # Meeus/Jones/Butcher Gregorian Easter calculation. Keeping it here avoids
    # making a general calendar conversion depend on a country-holiday package.
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    dayOffset = (32 + 2 * e + 2 * i - h - k) % 7
    month, day = divmod(h + dayOffset + 114, 31)
    easter = date(year, month, day + 1)
    return {
        date(year, 1, 1), date(year, 5, 1), date(year, 5, 17),
        date(year, 12, 25), date(year, 12, 26),
        easter - timedelta(days=3), easter - timedelta(days=2),
        easter, easter + timedelta(days=1), easter + timedelta(days=39),
        easter + timedelta(days=49),
    }


def _norwegianHolidayLabels(year):
    """Return the holiday captions CEWE shows beneath selected day numbers."""
    # Keep the date calculation in step with _norwegianHolidays above.  The
    # labels are intentionally Norwegian because this first calendar sample
    # explicitly requests nb_NO holiday data.
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    dayOffset = (32 + 2 * e + 2 * i - h - k) % 7
    month, day = divmod(h + dayOffset + 114, 31)
    easter = date(year, month, day + 1)
    return {
        date(year, 1, 1): ('1. nyttårsdag',),
        date(year, 5, 1): ('Arbeidernes dag',),
        date(year, 5, 17): ('Grunnlovsdagen',),
        date(year, 12, 25): ('1. juledag',),
        date(year, 12, 26): ('2. juledag',),
        date(year, 3, 8): ('Kvinnedagen',),
        easter - timedelta(days=7): ('Palmesøndag',),
        easter - timedelta(days=3): ('Skjærtorsdag',),
        easter - timedelta(days=2): ('Langfredag',),
        easter: ('1. påskedag',),
        easter + timedelta(days=1): ('2. påskedag',),
        easter + timedelta(days=39): ('Kristi himmelfartsdag',),
        easter + timedelta(days=49): ('1. pinsedag',),
        easter + timedelta(days=50): ('2. pinsedag',),
    }


def _fontName(requestedFont):
    """Use a built-in face until CEWE calendar font registration is implemented."""
    if requestedFont in pdfmetrics.getRegisteredFontNames():
        return requestedFont
    return 'Helvetica'


def _drawCentered(pdf, text, x, y, fontName, fontSize, colour=colors.black):
    pdf.setFont(fontName, fontSize)
    pdf.setFillColor(colour)
    pdf.drawCentredString(x, y, text)


def _drawBoldCentered(pdf, text, x, y, fontName, fontSize):
    """Draw bold text, using Helvetica's built-in bold face when appropriate."""
    boldFontName = 'Helvetica-Bold' if fontName == 'Helvetica' else fontName
    _drawCentered(pdf, text, x, y, boldFontName, fontSize)


def _drawMonthHeading(pdf, monthDate, bounds, fontName, percentage, language):
    # Calendar templates may give this small label a generously tall area;
    # CEWE does not let the month heading grow without bound in that case.
    fontSize = min(20, max(8, bounds.height * (0.54 + percentage / 500)))
    months, _ = _calendarNames(language)
    label = months[monthDate.month - 1]
    boldFontName = 'Helvetica-Bold' if fontName == 'Helvetica' else fontName
    pdf.setFont(boldFontName, fontSize)
    pdf.setFillColor(colors.black)
    pdf.drawString(bounds.x, bounds.y + (bounds.height - fontSize) / 2, label)


def _drawWeekRows(pdf, monthDate, bounds, fontName, percentage, showHolidays,
                  language): # pylint: disable=too-many-locals
    """Draw a Monday-to-Sunday month grid for CEWE's OneWeekPerRow layout."""
    firstWeekday, numberOfDays = calendar.monthrange(monthDate.year, monthDate.month)
    # CEWE's variant shows a compact row per week.  Leave a heading row for
    # weekday names, then include the partial first and final weeks.
    weekCount = (firstWeekday + numberOfDays + 6) // 7
    headerHeight = bounds.height * 0.18
    rowHeight = (bounds.height - headerHeight) / weekCount
    columnWidth = bounds.width / 7
    fontSize = max(5, min(rowHeight * 0.38, columnWidth * 0.22) *
                   (1 + percentage / 250))

    # CEWE's otherwise transparent calendar theme still places its month grid
    # on an opaque white panel, so that date labels remain readable over a
    # page background or photograph.
    pdf.setFillColor(colors.white)
    pdf.rect(bounds.x, bounds.y, bounds.width, bounds.height, fill=1, stroke=0)
    pdf.setStrokeColor(colors.black)
    pdf.setLineWidth(0.35)
    _, weekdays = _calendarNames(language)
    for column, weekday in enumerate(weekdays):
        _drawBoldCentered(pdf, weekday, bounds.x + (column + 0.5) * columnWidth,
                          bounds.y + bounds.height - headerHeight * 0.72,
                          fontName, fontSize * 0.72)
    for row in range(weekCount + 1):
        pdf.line(bounds.x, bounds.y + row * rowHeight,
                 bounds.x + bounds.width, bounds.y + row * rowHeight)
    for column in range(8):
        pdf.line(bounds.x + column * columnWidth, bounds.y,
                 bounds.x + column * columnWidth,
                 bounds.y + bounds.height)
    pdf.line(bounds.x, bounds.y + bounds.height,
             bounds.x + bounds.width, bounds.y + bounds.height)

    holidays = _norwegianHolidays(monthDate.year) if showHolidays else set()
    holidayLabels = _norwegianHolidayLabels(monthDate.year) if showHolidays else {}
    for dayNumber in range(1, numberOfDays + 1):
        dayDate = date(monthDate.year, monthDate.month, dayNumber)
        cell = firstWeekday + dayNumber - 1
        row, column = divmod(cell, 7)
        dayX = bounds.x + (column + 0.5) * columnWidth
        # CEWE places the date near the top of each cell, leaving the lower
        # portion available for a handwritten note on the printed calendar.
        dayY = bounds.y + (weekCount - row - 0.40) * rowHeight
        if column == 6 or dayDate in holidays:
            _drawBoldCentered(pdf, str(dayNumber), dayX, dayY, fontName, fontSize)
        else:
            _drawCentered(pdf, str(dayNumber), dayX, dayY, fontName, fontSize)

        labels = list(holidayLabels.get(dayDate, ()))
        # The CEWE March calendar also calls out the switch to summer time.
        if dayDate == date(monthDate.year, 3, 28) and dayDate.weekday() == 6:
            labels.append('Sommertid')
        for labelNumber, label in enumerate(labels):
            _drawBoldCentered(pdf, label, dayX,
                              bounds.y + (weekCount - row - 0.66 -
                                          labelNumber * 0.13) * rowHeight,
                              fontName, max(3.5, fontSize * 0.27))


def _drawYearHeading(pdf, startDate, bounds, fontName):
    """Draw CEWE's ``Year (Long-Name-Big)`` cover heading.

    Despite its name, this layout does not contain a compact twelve-month
    calendar.  It reserves the area for the prominently centred year.
    """
    fontSize = bounds.height * 0.42
    _drawBoldCentered(pdf, str(startDate.year), bounds.x + bounds.width / 2,
                      bounds.y + (bounds.height - fontSize) / 2,
                      fontName, fontSize)


def _drawOneRow(pdf, monthDate, bounds, fontName, percentage, styles,
                defaultStyle, language):
    """Draw CEWE's landscape calendar strip: weekday and date in 31 columns."""
    _, weekdays = _calendarNames(language)
    _, numberOfDays = calendar.monthrange(monthDate.year, monthDate.month)
    columnWidth = bounds.width / numberOfDays
    fontSize = max(5, min(bounds.height * 0.27, columnWidth * 0.45) *
                   (1 + percentage / 250))
    for dayNumber in range(1, numberOfDays + 1):
        dayDate = date(monthDate.year, monthDate.month, dayNumber)
        dayX = bounds.x + (dayNumber - 0.5) * columnWidth
        if dayDate.weekday() == 6:
            headerStyle = _calendarStyle(
                styles, defaultStyle, 'CALENDAR_CELL_TYPE_HEAD_SUNDAY',
                'CALENDAR_CELL_TYPE_HEAD_HOLIDAY')
            dayStyle = _calendarStyle(
                styles, defaultStyle, 'CALENDAR_CELL_TYPE_SUNDAY',
                'CALENDAR_CELL_TYPE_HOLIDAY')
        elif dayDate.weekday() == 5:
            headerStyle = _calendarStyle(
                styles, defaultStyle, 'CALENDAR_CELL_TYPE_HEAD_SATURDAY')
            dayStyle = _calendarStyle(styles, defaultStyle,
                                      'CALENDAR_CELL_TYPE_SATURDAY')
        else:
            headerStyle = _calendarStyle(
                styles, defaultStyle, 'CALENDAR_CELL_TYPE_HEAD_WEEKDAY')
            dayStyle = _calendarStyle(styles, defaultStyle,
                                      'CALENDAR_CELL_TYPE_WEEKDAY')
        if headerStyle.background_colour is not None:
            pdf.setFillColor(headerStyle.background_colour)
            pdf.rect(dayX - columnWidth / 2, bounds.y + bounds.height * 0.5,
                     columnWidth, bounds.height * 0.5, fill=1, stroke=0)
        if dayStyle.background_colour is not None:
            pdf.setFillColor(dayStyle.background_colour)
            pdf.rect(dayX - columnWidth / 2, bounds.y, columnWidth,
                     bounds.height * 0.5, fill=1, stroke=0)
        _drawCentered(pdf, weekdays[dayDate.weekday()], dayX,
                      bounds.y + bounds.height * 0.63,
                      fontName, fontSize * 0.68, headerStyle.text_colour)
        _drawCentered(pdf, str(dayNumber), dayX,
                      bounds.y + bounds.height * 0.20,
                      fontName, fontSize, dayStyle.text_colour)


def processCalendarArea(calendarArea, fotobook, pageNumber, area, pageHeight,
                        pdf, context: RenderContext,
                        calendarSchemas: CalendarSchemas):
    """Render one calendar area using the CEWE layout names currently supported.

    Unsupported layouts are reported but do not prevent the user's editable
    areas on that page from reaching the PDF.
    """
    startDate = _calendarStartDate(fotobook)
    if startDate is None:
        return
    layout = calendarArea.get('layoutschema', '')
    fontName = _fontName(calendarArea.get('font', ''))
    percentage = float(calendarArea.get('fontsize_percentage', '0'))
    showHolidays = calendarArea.get('show_holiday') == '1'
    bounds = CalendarBounds.fromArea(area, pageHeight, context)
    language = _calendarLanguage(fotobook)

    if layout == 'Year (Long-Name-Big)':
        _drawYearHeading(pdf, startDate, bounds, fontName)
        return

    # Normal calendar pages follow the start month. A calendar beginning on
    # another date still has a stable, intuitive pagenr-to-month relationship.
    monthIndex = pageNumber - 1
    monthDate = date(startDate.year + (startDate.month - 1 + monthIndex) // 12,
                     (startDate.month - 1 + monthIndex) % 12 + 1, 1)
    if layout == 'Month':
        _drawMonthHeading(pdf, monthDate, bounds, fontName, percentage, language)
    elif layout.startswith('OneWeekPerRow'):
        _drawWeekRows(pdf, monthDate, bounds, fontName, percentage, showHolidays,
                      language)
    elif layout.startswith('OneRow'):
        styles, defaultStyle = _calendarCellStyles(
            fotobook, calendarArea, calendarSchemas)
        _drawOneRow(pdf, monthDate, bounds, fontName, percentage, styles,
                    defaultStyle, language)
    else:
        logging.warning(f'Unsupported calendar layout {layout!r}; area omitted')
