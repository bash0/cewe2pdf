"""Render the calendar-specific areas in CEWE calendar products.

Calendar MCF files store the editable page areas in the familiar form, but
describe their generated calendarium using a compact ``calendararea`` element.
This module deliberately contains that product-specific interpretation; the
ordinary image, text and clip-art paths remain shared with photo albums.
"""

import calendar
from datetime import date, datetime, timedelta
from dataclasses import dataclass, replace
import logging

from reportlab.lib import colors
from reportlab.lib import fonts as reportlabFonts
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.utils import ImageReader

from calendarLayouts import CalendarCellLayout, CalendarLayouts
from calendarEntries import (CalendarEntries, calendarEventsForYear,
                             personalCalendarEventsForYear,
                             resolveCalendarEventImage)
from calendarNames import CalendarNames, calendarNamesForLocale
from calendarSchemas import CalendarCellStyle, CalendarSchemas, colourFromHex
from fontHandling import getAvailableFont
from renderContext import RenderContext


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


def _calendarWeekNumbers(fotobook):
    """Read the optional week-number column requested by the calendar MCF."""
    holidays = fotobook.find('holidays')
    features = (holidays.get('features', '').split(',')
                if holidays is not None else [])
    if 'show_week_of_year' not in (feature.strip() for feature in features):
        return False
    return True


def _calendarCellStyles(fotobook, calendarArea, calendarSchemas):
    """Return styles from an embedded scheme, or from CEWE's resource file."""
    schemeName = calendarArea.get('colorschema', '')
    schema = calendarSchemas.get(schemeName)
    styles = dict(schema.cell_styles) if schema is not None else {}
    gridColour = schema.grid_colour if schema is not None else None
    matchingSchemes = fotobook.xpath(
        f'./colorSchemata/calendararea[@colorschema="{schemeName}"]')
    if not matchingSchemes:
        return styles, CalendarCellStyle(colors.black, None), gridColour
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
                colourFromHex(cell.get('bgcolor'), defaultStyle.background_colour),
                colourFromHex(cell.get('bordercolor')))
    return styles, defaultStyle, gridColour


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


def _drawMonthHeading(pdf, monthDate, bounds, fontName, percentage, names,
                      layout, styles, defaultStyle):
    cell = _layoutCell(layout, 'CALENDAR_CELL_TYPE_MONTH',
                       CalendarCellLayout(font_size=22, bold=True))
    fontSize = _scaledLayoutFontSize(cell, percentage, 22)
    style = _calendarStyle(styles, defaultStyle, 'CALENDAR_CELL_TYPE_MONTH',
                           'CALENDAR_CELL_TYPE_TITLE')
    label = names.month_names[monthDate.month - 1]
    ascent, descent = _fontMetrics(fontName, fontSize, cell)
    left = bounds.x + cell.padding_left * CEWE_LAYOUT_PADDING_TO_POINT
    right = bounds.x + bounds.width - \
        cell.padding_right * CEWE_LAYOUT_PADDING_TO_POINT
    if 'AlignTop' in cell.text_align:
        y = bounds.y + bounds.height - \
            cell.padding_top * CEWE_LAYOUT_PADDING_TO_POINT - ascent
    elif 'AlignBottom' in cell.text_align:
        y = bounds.y + cell.padding_bottom * CEWE_LAYOUT_PADDING_TO_POINT - descent
    else:
        y = bounds.y + bounds.height / 2 - (ascent + descent) / 2
    pdf.setFont(_calendarFontName(fontName, cell), fontSize)
    pdf.setFillColor(style.text_colour)
    if 'AlignRight' in cell.text_align:
        pdf.drawRightString(right, y, label)
    elif 'AlignCenter' in cell.text_align or 'AlignHCenter' in cell.text_align:
        pdf.drawCentredString((left + right) / 2, y, label)
    else:
        pdf.drawString(left, y, label)


def _weekRowHeights(totalHeight, weekCount):
    """Split a grid into a shallow weekday header and equal day rows."""
    dayRowHeight = totalHeight / (weekCount + WEEKDAY_HEADER_ROW_SCALE)
    return dayRowHeight * WEEKDAY_HEADER_ROW_SCALE, dayRowHeight


def _drawWeekRows(pdf, monthDate, bounds, fontName, percentage,
                  holidayPercentage, showHolidays, language, layout,
                  calendarEntries, styles, defaultStyle, gridColour,
                  showWeekNumbers, names, fotobook,
                  eventImageFolders): # pylint: disable=too-many-locals
    """Draw a Monday-to-Sunday month grid for CEWE's OneWeekPerRow layout."""
    firstWeekday, numberOfDays = calendar.monthrange(monthDate.year, monthDate.month)
    # CEWE's variant shows a compact row per week.  Leave a heading row for
    # weekday names, then include the partial first and final weeks.
    weekCount = (firstWeekday + numberOfDays + 6) // 7
    headerHeight, rowHeight = _weekRowHeights(bounds.height, weekCount)
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
    weekNumberCell = _layoutCell(layout, 'CALENDAR_CELL_TYPE_WEEK_OF_YEAR',
                                  weekdayCell)
    weekNumberFontSize = _scaledLayoutFontSize(weekNumberCell, percentage, 14)
    weekNumberWidth = 0
    if showWeekNumbers:
        widestLabel = max(names.week_name, '53', key=len)
        weekNumberWidth = pdfmetrics.stringWidth(
            widestLabel, _calendarFontName(fontName, weekNumberCell),
            weekNumberFontSize)
        # CEWE's calendar cells include a small, font-relative horizontal
        # breathing space even when their XML layout has no explicit padding.
        # This keeps the week-number column legible without imposing a
        # product-specific fixed width.
        weekNumberWidth += weekNumberFontSize / 2
    columnWidth = (bounds.width - weekNumberWidth) / 7

    headerStyle = _calendarStyle(styles, defaultStyle,
                                 'CALENDAR_CELL_TYPE_HEAD_WEEKDAY')
    weekStyle = _calendarStyle(styles, defaultStyle,
                               'CALENDAR_CELL_TYPE_WEEK_OF_YEAR',
                               'CALENDAR_CELL_TYPE_WEEKDAY')
    for row in range(weekCount):
        for column in range(7):
            style = _calendarStyle(styles, defaultStyle,
                                   'CALENDAR_CELL_TYPE_WEEKDAY')
            if style.background_colour is not None:
                pdf.setFillColor(style.background_colour)
                pdf.rect(bounds.x + weekNumberWidth + column * columnWidth,
                         bounds.y + row * rowHeight, columnWidth, rowHeight,
                         fill=1, stroke=0)
        if showWeekNumbers and weekStyle.background_colour is not None:
            pdf.setFillColor(weekStyle.background_colour)
            pdf.rect(bounds.x, bounds.y + row * rowHeight, weekNumberWidth,
                     rowHeight, fill=1, stroke=0)
    if headerStyle.background_colour is not None:
        pdf.setFillColor(headerStyle.background_colour)
        pdf.rect(bounds.x + weekNumberWidth, bounds.y + weekCount * rowHeight,
                 bounds.width - weekNumberWidth, headerHeight, fill=1, stroke=0)
        if showWeekNumbers:
            pdf.rect(bounds.x, bounds.y + weekCount * rowHeight,
                     weekNumberWidth, headerHeight, fill=1, stroke=0)
    pdf.setStrokeColor(gridColour or colors.black)
    pdf.setLineWidth(0.35)
    for column, weekday in enumerate(names.weekday_names):
        _drawCellText(pdf, weekday, bounds.x + weekNumberWidth +
                      (column + 0.5) * columnWidth,
                      bounds.y + bounds.height - headerHeight * 0.72,
                      fontName, headerFontSize, headerCell,
                      headerStyle.text_colour)
    if showWeekNumbers:
        _drawCellText(pdf, names.week_name, bounds.x + weekNumberWidth / 2,
                      bounds.y + bounds.height - headerHeight * 0.72,
                      fontName, headerFontSize, headerCell,
                      headerStyle.text_colour)
    for row in range(weekCount + 1):
        pdf.line(bounds.x, bounds.y + row * rowHeight,
                 bounds.x + bounds.width, bounds.y + row * rowHeight)
    for column in range(8):
        pdf.line(bounds.x + weekNumberWidth + column * columnWidth, bounds.y,
                 bounds.x + weekNumberWidth + column * columnWidth,
                 bounds.y + bounds.height)
    if showWeekNumbers:
        pdf.line(bounds.x, bounds.y, bounds.x, bounds.y + bounds.height)

    # Calendar captions and holiday emphasis are locale data, not a property
    # of the renderer.  The requested MCF language selects CEWE's matching
    # Resources/calendarentries/<locale>.xml definitions.
    holidays, holidayCaptions = (
        calendarEventsForYear(calendarEntries, language, monthDate.year)
        if showHolidays else (set(), {}))
    personalCaptions = personalCalendarEventsForYear(fotobook, monthDate.year)
    captionStyle = _calendarStyle(styles, defaultStyle,
                                  'CALENDAR_CELL_TYPE_SPECIAL_DAY',
                                  'CALENDAR_CELL_TYPE_EXTRA_INFORMATION')
    for dayNumber in range(1, numberOfDays + 1):
        dayDate = date(monthDate.year, monthDate.month, dayNumber)
        cell = firstWeekday + dayNumber - 1
        row, column = divmod(cell, 7)
        dayX = bounds.x + weekNumberWidth + (column + 0.5) * columnWidth
        dayCell = sundayCell if column == 6 or dayDate in holidays else weekdayCell
        dayStyle = _calendarStyle(
            styles, defaultStyle,
            'CALENDAR_CELL_TYPE_HOLIDAY' if dayDate in holidays else
            ('CALENDAR_CELL_TYPE_SUNDAY' if column == 6 else
             'CALENDAR_CELL_TYPE_WEEKDAY'))
        captions = (list(holidayCaptions.get(dayDate, ())) +
                    list(personalCaptions.get(dayDate, ())))
        eventImages = []
        for caption in captions:
            imagePath = resolveCalendarEventImage(caption.image_path,
                                                   eventImageFolders)
            if imagePath is None:
                continue
            try:
                eventImages.append(ImageReader(imagePath))
            except OSError as exception:
                logging.warning('Cannot load calendar event image %s: %s',
                                imagePath, exception)
        cellTop = bounds.y + (weekCount - row) * rowHeight
        if not eventImages:
            ascent, _ = _fontMetrics(fontName, fontSize, dayCell)
            # ``OneWeekPerRow (2)`` says AlignTop and paddingtop=10.
            # Positioning the baseline from the glyph ascent avoids treating
            # the baseline as the top of the text.
            dayY = cellTop - dayCell.padding_top * CEWE_LAYOUT_PADDING_TO_POINT - ascent
            _drawCellText(pdf, str(dayNumber), dayX, dayY, fontName, fontSize,
                          dayCell, dayStyle.text_colour)

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
                          fontName, holidayFontSize, captionCell,
                          captionStyle.text_colour)
        for imageNumber, image in enumerate(eventImages):
            imageWidth, imageHeight = image.getSize()
            cellBottom = bounds.y + (weekCount - row - 1) * rowHeight
            contentWidth = max(
                0, columnWidth - (dayCell.padding_left + dayCell.padding_right) *
                CEWE_LAYOUT_PADDING_TO_POINT)
            contentTop = cellTop - dayCell.padding_top * CEWE_LAYOUT_PADDING_TO_POINT
            contentBottom = (cellBottom +
                             dayCell.padding_bottom * CEWE_LAYOUT_PADDING_TO_POINT +
                             len(captionLines) * holidayFontSize)
            maximumHeight = max(0, (contentTop - contentBottom) /
                                len(eventImages))
            renderedHeight = min(maximumHeight,
                                 contentWidth * imageHeight / imageWidth)
            if renderedHeight > 0:
                renderedWidth = renderedHeight * imageWidth / imageHeight
                pdf.drawImage(image, dayX - renderedWidth / 2,
                              contentTop - (imageNumber + 1) * renderedHeight,
                              renderedWidth, renderedHeight, mask='auto')
    if showWeekNumbers:
        firstMonday = date(monthDate.year, monthDate.month, 1) - \
            timedelta(days=firstWeekday)
        for row in range(weekCount):
            weekDate = firstMonday + timedelta(days=row * 7)
            _drawCellText(pdf, str(weekDate.isocalendar().week),
                          bounds.x + weekNumberWidth / 2,
                          bounds.y + (weekCount - row - 0.5) * rowHeight,
                          fontName, weekNumberFontSize, weekNumberCell,
                          weekStyle.text_colour)


def _drawYearHeading(pdf, startDate, bounds, fontName, percentage, layout,
                     styles, defaultStyle):
    """Draw CEWE's ``Year (Long-Name-Big)`` cover heading.

    Despite its name, this layout does not contain a compact twelve-month
    calendar.  It reserves the area for the prominently centred year.
    """
    cell = _layoutCell(layout, 'CALENDAR_CELL_TYPE_YEAR',
                       CalendarCellLayout(font_size=64, bold=True))
    fontSize = _scaledLayoutFontSize(cell, percentage, 64)
    style = _calendarStyle(styles, defaultStyle, 'CALENDAR_CELL_TYPE_YEAR')
    _drawCellText(pdf, str(startDate.year), bounds.x + bounds.width / 2,
                  bounds.y + (bounds.height - fontSize) / 2,
                  fontName, fontSize, cell, style.text_colour)


def _drawOneRow(pdf, monthDate, bounds, fontName, percentage, styles,
                defaultStyle, names, layout):
    """Draw CEWE's landscape calendar strip: weekday and date in 31 columns."""
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
        _drawCellText(pdf, names.weekday_names[dayDate.weekday()], dayX,
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
                        calendarEntries: CalendarEntries,
                        calendarNames: CalendarNames,
                        calendarEventImageFolders, additionalFonts, state):
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
    names = calendarNamesForLocale(calendarNames, language)
    if names is None:
        logging.warning('Calendar language %r has no label resource; area omitted',
                        language)
        return
    showWeekNumbers = _calendarWeekNumbers(fotobook)
    styles, defaultStyle, gridColour = _calendarCellStyles(
        fotobook, calendarArea, calendarSchemas)

    if layout == 'Year (Long-Name-Big)':
        _drawYearHeading(pdf, startDate, bounds, fontName, percentage,
                         cellLayout, styles, defaultStyle)
        return

    # Normal calendar pages follow the start month. A calendar beginning on
    # another date still has a stable, intuitive pagenr-to-month relationship.
    monthIndex = pageNumber - 1
    monthDate = date(startDate.year + (startDate.month - 1 + monthIndex) // 12,
                     (startDate.month - 1 + monthIndex) % 12 + 1, 1)
    if layout == 'Month':
        _drawMonthHeading(pdf, monthDate, bounds, fontName, percentage, names,
                          cellLayout, styles, defaultStyle)
    elif layout.startswith('OneWeekPerRow'):
        _drawWeekRows(pdf, monthDate, bounds, fontName, percentage,
                      holidayPercentage, showHolidays, language, cellLayout,
                      calendarEntries, styles, defaultStyle, gridColour,
                      showWeekNumbers, names, fotobook,
                      calendarEventImageFolders)
    elif layout.startswith('OneRow'):
        _drawOneRow(pdf, monthDate, bounds, fontName, percentage, styles,
                    defaultStyle, names, cellLayout)
    else:
        logging.warning(f'Unsupported calendar layout {layout!r}; area omitted')
