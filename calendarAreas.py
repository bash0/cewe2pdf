"""Render the calendar-specific areas in CEWE calendar products.

Calendar MCF files store the editable page areas in the familiar form, but
describe their generated calendarium using a compact ``calendararea`` element.
This module deliberately contains that product-specific interpretation; the
ordinary image, text and clip-art paths remain shared with photo albums.
"""

import calendar
from datetime import date, datetime
from dataclasses import dataclass, replace
import logging

from reportlab.lib import colors
from reportlab.lib import fonts as reportlabFonts
from reportlab.pdfbase import pdfmetrics

from calendarLayouts import CalendarCellLayout, CalendarLayouts
from calendarEntries import CalendarEntries, calendarEventsForYear
from calendarSchemas import CalendarCellStyle, CalendarSchemas, colourFromHex
from fontHandling import getAvailableFont
from renderContext import RenderContext


NORWEGIAN_MONTHS = (
    'januar', 'februar', 'mars', 'april', 'mai', 'juni',
    'juli', 'august', 'september', 'oktober', 'november', 'desember')
NORWEGIAN_WEEKDAYS = ('ma', 'ti', 'on', 'to', 'fr', 'lø', 'sø')
ENGLISH_MONTHS = (
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December')
ENGLISH_WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')

# CEWE's calendar-layout resource describes font sizes in the editor's
# 96-dpi pixel units.  ReportLab uses typographic points (72 per inch).
CEWE_LAYOUT_UNIT_TO_POINT = 72 / 96
# Calendar cell padding uses a smaller editor unit than its font size.  The
# OneWeekPerRow reference layout's ``paddingtop=10`` visually corresponds to
# about 5 ReportLab points, rather than the 7.5-point font-unit conversion.
CEWE_LAYOUT_PADDING_TO_POINT = 0.5
# The weekday-label row in CEWE's OneWeekPerRow grid is visually a little
# shallower than an ordinary week.  It is not described in the MCF or the
# calendar-layout resource, so retain the measured renderer rule here.
WEEKDAY_HEADER_ROW_SCALE = 0.93


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


def _fontName(requestedFont, pdf, additionalFonts, state):
    """Resolve calendar fonts with the same policy as ordinary text areas."""
    return getAvailableFont(requestedFont, pdf, additionalFonts, state)


def _drawCentered(pdf, text, x, y, fontName, fontSize, colour=colors.black):
    pdf.setFont(fontName, fontSize)
    pdf.setFillColor(colour)
    pdf.drawCentredString(x, y, text)


def _layoutCell(layout, cellType, fallback):
    """Return a layout cell, preserving a usable fallback without CEWE data."""
    return layout.get(cellType, fallback)


def _scaledLayoutFontSize(cell, percentage, fallbackSize):
    """Apply CEWE's MCF percentage offset to a layout's fixed point size."""
    return ((cell.font_size or fallbackSize) * CEWE_LAYOUT_UNIT_TO_POINT *
            (1 + percentage / 100))


def _fontMetrics(fontName, fontSize, cell):
    """Return the ascent and descent for the same face used to draw a cell."""
    return pdfmetrics.getAscentDescent(_calendarFontName(fontName, cell), fontSize)


def _calendarFontName(fontName, cell):
    """Resolve a CEWE family to its registered regular or bold ReportLab face."""
    try:
        return reportlabFonts.tt2ps(fontName, int(cell.bold), 0)
    except ValueError:
        return 'Helvetica-Bold' if cell.bold and fontName == 'Helvetica' else fontName


def _drawCellText(pdf, text, x, y, fontName, fontSize, cell, colour=colors.black):
    """Draw one cell using its layout emphasis (alignment is handled by caller)."""
    _drawCentered(pdf, text, x, y, _calendarFontName(fontName, cell), fontSize,
                  colour)


def _wrapCalendarCaption(text, maximumWidth, fontName, fontSize, cell):
    """Wrap a holiday caption at word boundaries to fit its calendar cell."""
    lines = []
    words = text.split()
    currentLine = []
    resolvedFont = _calendarFontName(fontName, cell)
    for word in words:
        candidate = ' '.join(currentLine + [word])
        if (currentLine and pdfmetrics.stringWidth(candidate, resolvedFont, fontSize)
                > maximumWidth):
            lines.append(' '.join(currentLine))
            currentLine = [word]
        else:
            currentLine.append(word)
    if currentLine:
        lines.append(' '.join(currentLine))
    return lines


def _captionCellForEvent(caption, holidayCell, dayCell):
    """Apply public-holiday and Sunday emphasis to one event caption."""
    return replace(holidayCell,
                   bold=caption.is_public_holiday or dayCell.bold)


def _drawMonthHeading(pdf, monthDate, bounds, fontName, percentage, language,
                      layout):
    cell = _layoutCell(layout, 'CALENDAR_CELL_TYPE_MONTH',
                       CalendarCellLayout(font_size=22, bold=True))
    fontSize = _scaledLayoutFontSize(cell, percentage, 22)
    months, _ = _calendarNames(language)
    label = months[monthDate.month - 1]
    # The Month layout used by our portrait fixture explicitly requests top,
    # left alignment.  Other layouts retain the previous vertical centring.
    ascent, _ = _fontMetrics(fontName, fontSize, cell)
    y = (bounds.y + bounds.height - ascent if 'AlignTop' in cell.text_align
         else bounds.y + (bounds.height - fontSize) / 2)
    pdf.setFont(_calendarFontName(fontName, cell), fontSize)
    pdf.setFillColor(colors.black)
    pdf.drawString(bounds.x, y, label)


def _weekRowHeights(totalHeight, weekCount):
    """Split a grid into a shallow weekday header and equal day rows."""
    dayRowHeight = totalHeight / (weekCount + WEEKDAY_HEADER_ROW_SCALE)
    return dayRowHeight * WEEKDAY_HEADER_ROW_SCALE, dayRowHeight


def _drawWeekRows(pdf, monthDate, bounds, fontName, percentage,
                  holidayPercentage, showHolidays, language,
                  layout, calendarEntries): # pylint: disable=too-many-locals
    """Draw a Monday-to-Sunday month grid for CEWE's OneWeekPerRow layout."""
    firstWeekday, numberOfDays = calendar.monthrange(monthDate.year, monthDate.month)
    # CEWE's variant shows a compact row per week.  Leave a heading row for
    # weekday names, then include the partial first and final weeks.
    weekCount = (firstWeekday + numberOfDays + 6) // 7
    headerHeight, rowHeight = _weekRowHeights(bounds.height, weekCount)
    columnWidth = bounds.width / 7
    weekdayCell = _layoutCell(layout, 'CALENDAR_CELL_TYPE_WEEKDAY',
                              CalendarCellLayout(font_size=14))
    sundayCell = _layoutCell(layout, 'CALENDAR_CELL_TYPE_SUNDAY',
                             CalendarCellLayout(font_size=14, bold=True))
    headerCell = _layoutCell(layout, 'CALENDAR_CELL_TYPE_HEAD_WEEKDAY',
                             CalendarCellLayout(font_size=16, bold=True))
    holidayCell = _layoutCell(layout, 'CALENDAR_CELL_TYPE_SPECIAL_DAY',
                              CalendarCellLayout(font_size=10))
    fontSize = _scaledLayoutFontSize(weekdayCell, percentage, 14)
    headerFontSize = _scaledLayoutFontSize(headerCell, percentage, 16)
    # The editor's holiday-size control is relative to the ordinary day
    # number, not the special-caption cell's nominal 10-unit font.  This is
    # visible in the 50/100/150% editor samples: captions grow from the
    # OneWeekPerRow day base (14), while retaining the special cell's other
    # properties such as its non-bold face.
    holidayFontSize = max(
        5, _scaledLayoutFontSize(weekdayCell, holidayPercentage, 14))

    # CEWE's otherwise transparent calendar theme still places its month grid
    # on an opaque white panel, so that date labels remain readable over a
    # page background or photograph.
    pdf.setFillColor(colors.white)
    pdf.rect(bounds.x, bounds.y, bounds.width, bounds.height, fill=1, stroke=0)
    pdf.setStrokeColor(colors.black)
    pdf.setLineWidth(0.35)
    _, weekdays = _calendarNames(language)
    for column, weekday in enumerate(weekdays):
        _drawCellText(pdf, weekday, bounds.x + (column + 0.5) * columnWidth,
                      bounds.y + bounds.height - headerHeight * 0.72,
                      fontName, headerFontSize, headerCell)
    for row in range(weekCount + 1):
        pdf.line(bounds.x, bounds.y + row * rowHeight,
                 bounds.x + bounds.width, bounds.y + row * rowHeight)
    for column in range(8):
        pdf.line(bounds.x + column * columnWidth, bounds.y,
                 bounds.x + column * columnWidth,
                 bounds.y + bounds.height)
    pdf.line(bounds.x, bounds.y + bounds.height,
             bounds.x + bounds.width, bounds.y + bounds.height)

    # Calendar captions and holiday emphasis are locale data, not a property
    # of the renderer.  The requested MCF language selects CEWE's matching
    # Resources/calendarentries/<locale>.xml definitions.
    holidays, holidayCaptions = (
        calendarEventsForYear(calendarEntries, language, monthDate.year)
        if showHolidays else (set(), {}))
    for dayNumber in range(1, numberOfDays + 1):
        dayDate = date(monthDate.year, monthDate.month, dayNumber)
        cell = firstWeekday + dayNumber - 1
        row, column = divmod(cell, 7)
        dayX = bounds.x + (column + 0.5) * columnWidth
        dayCell = sundayCell if column == 6 or dayDate in holidays else weekdayCell
        cellTop = bounds.y + (weekCount - row) * rowHeight
        ascent, _ = _fontMetrics(fontName, fontSize, dayCell)
        # ``OneWeekPerRow (2)`` says AlignTop and paddingtop=10.  Positioning
        # the baseline from the glyph ascent avoids the old almost-clipped
        # result caused by treating the baseline as the top of the text.
        dayY = cellTop - dayCell.padding_top * CEWE_LAYOUT_PADDING_TO_POINT - ascent
        _drawCellText(pdf, str(dayNumber), dayX, dayY, fontName, fontSize, dayCell)

        captions = list(holidayCaptions.get(dayDate, ()))
        captionLines = []
        for caption in captions:
            captionCell = _captionCellForEvent(caption, holidayCell, dayCell)
            usableWidth = max(1, columnWidth - 4)
            captionLines.extend(
                (line, captionCell) for line in _wrapCalendarCaption(
                    caption.name, usableWidth, fontName, holidayFontSize,
                    captionCell))
        for lineNumber, (line, captionCell) in enumerate(captionLines):
            cellBottom = bounds.y + (weekCount - row - 1) * rowHeight
            _, descent = _fontMetrics(fontName, holidayFontSize, captionCell)
            _drawCellText(pdf, line, dayX,
                          cellBottom + 2 - descent +
                          (len(captionLines) - lineNumber - 1) * holidayFontSize,
                          fontName, holidayFontSize, captionCell)


def _drawYearHeading(pdf, startDate, bounds, fontName, percentage, layout):
    """Draw CEWE's ``Year (Long-Name-Big)`` cover heading.

    Despite its name, this layout does not contain a compact twelve-month
    calendar.  It reserves the area for the prominently centred year.
    """
    cell = _layoutCell(layout, 'CALENDAR_CELL_TYPE_YEAR',
                       CalendarCellLayout(font_size=64, bold=True))
    fontSize = _scaledLayoutFontSize(cell, percentage, 64)
    _drawCellText(pdf, str(startDate.year), bounds.x + bounds.width / 2,
                  bounds.y + (bounds.height - fontSize) / 2,
                  fontName, fontSize, cell)


def _drawOneRow(pdf, monthDate, bounds, fontName, percentage, styles,
                defaultStyle, language, layout):
    """Draw CEWE's landscape calendar strip: weekday and date in 31 columns."""
    _, weekdays = _calendarNames(language)
    _, numberOfDays = calendar.monthrange(monthDate.year, monthDate.month)
    columnWidth = bounds.width / numberOfDays
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
        headerCell = _layoutCell(
            layout, 'CALENDAR_CELL_TYPE_HEAD_' +
            ('SUNDAY' if dayDate.weekday() == 6 else
             'SATURDAY' if dayDate.weekday() == 5 else 'WEEKDAY'),
            CalendarCellLayout(font_size=10))
        dayCell = _layoutCell(
            layout, 'CALENDAR_CELL_TYPE_' +
            ('SUNDAY' if dayDate.weekday() == 6 else
             'SATURDAY' if dayDate.weekday() == 5 else 'WEEKDAY'),
            CalendarCellLayout(font_size=12))
        if headerStyle.background_colour is not None:
            pdf.setFillColor(headerStyle.background_colour)
            pdf.rect(dayX - columnWidth / 2, bounds.y + bounds.height * 0.5,
                     columnWidth, bounds.height * 0.5, fill=1, stroke=0)
        if dayStyle.background_colour is not None:
            pdf.setFillColor(dayStyle.background_colour)
            pdf.rect(dayX - columnWidth / 2, bounds.y, columnWidth,
                     bounds.height * 0.5, fill=1, stroke=0)
        _drawCellText(pdf, weekdays[dayDate.weekday()], dayX,
                      bounds.y + bounds.height * 0.63, fontName,
                      _scaledLayoutFontSize(headerCell, percentage, 10),
                      headerCell, headerStyle.text_colour)
        _drawCellText(pdf, str(dayNumber), dayX,
                      bounds.y + bounds.height * 0.20, fontName,
                      _scaledLayoutFontSize(dayCell, percentage, 12),
                      dayCell, dayStyle.text_colour)


def processCalendarArea(calendarArea, fotobook, pageNumber, area, pageHeight,
                        pdf, context: RenderContext,
                        calendarSchemas: CalendarSchemas,
                        calendarLayouts: CalendarLayouts,
                        calendarEntries: CalendarEntries, additionalFonts, state):
    """Render one calendar area using the CEWE layout names currently supported.

    Unsupported layouts are reported but do not prevent the user's editable
    areas on that page from reaching the PDF.
    """
    startDate = _calendarStartDate(fotobook)
    if startDate is None:
        return
    layout = calendarArea.get('layoutschema', '')
    cellLayout = calendarLayouts.get(layout, {})
    defaultFont = next((cell.font_face for cell in cellLayout.values()
                        if cell.font_face), '')
    fontName = _fontName(calendarArea.get('font', '') or defaultFont,
                         pdf, additionalFonts, state)
    percentage = float(calendarArea.get('fontsize_percentage', '0'))
    holidayPercentage = float(calendarArea.get('fontsize_percentage_holiddays', '0'))
    showHolidays = calendarArea.get('show_holiday') == '1'
    bounds = CalendarBounds.fromArea(area, pageHeight, context)
    language = _calendarLanguage(fotobook)

    if layout == 'Year (Long-Name-Big)':
        _drawYearHeading(pdf, startDate, bounds, fontName, percentage, cellLayout)
        return

    # Normal calendar pages follow the start month. A calendar beginning on
    # another date still has a stable, intuitive pagenr-to-month relationship.
    monthIndex = pageNumber - 1
    monthDate = date(startDate.year + (startDate.month - 1 + monthIndex) // 12,
                     (startDate.month - 1 + monthIndex) % 12 + 1, 1)
    if layout == 'Month':
        _drawMonthHeading(pdf, monthDate, bounds, fontName, percentage, language,
                          cellLayout)
    elif layout.startswith('OneWeekPerRow'):
        _drawWeekRows(pdf, monthDate, bounds, fontName, percentage,
                      holidayPercentage, showHolidays, language, cellLayout,
                      calendarEntries)
    elif layout.startswith('OneRow'):
        styles, defaultStyle = _calendarCellStyles(
            fotobook, calendarArea, calendarSchemas)
        _drawOneRow(pdf, monthDate, bounds, fontName, percentage, styles,
                    defaultStyle, language, cellLayout)
    else:
        logging.warning(f'Unsupported calendar layout {layout!r}; area omitted')
