"""Exact 8 mm CEWE tab stops for deliberately simple text paragraphs.

ReportLab's ``Paragraph`` flowable has no tab-stop support.  This module draws
the runs itself when a left-aligned paragraph has literal tab characters,
preserving the ordinary text attributes that can vary per span: font family,
bold, italic, size, colour and underline.  The normal area-wide text outline
and letter spacing are also retained.

It is intentionally not a replacement for ReportLab's paragraph layout.  A
tabbed paragraph containing line breaks, nested markup, tables, lists, or
alignment other than left is left to the older Paragraph path, where tabs have
the established non-breaking-space approximation.  In particular, this
flowable does not wrap text across tab stops, so it is also not used when its
resolved tab stops would exceed the available text width.
"""

from dataclasses import dataclass
from math import floor

import reportlab.lib.colors
from reportlab.lib.fonts import tt2ps
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Flowable

from text import CollectFontInfo, IsBold, IsItalic, IsUnderline
from conversionState import ConversionState


@dataclass(frozen=True)
class TabbedTextRun:
    """One styled text run in a paragraph containing literal tab characters."""

    text: str
    font_name: str
    font_size: float
    color: object
    underline: bool


class TabbedTextLine(Flowable):
    """Draw one unwrapped, left-aligned CEWE paragraph with 8 mm tab stops."""

    def __init__(self, runs, leading, text_outline=None, letter_spacing=0.0):
        super().__init__()
        self.runs = runs
        self.leading = leading
        self.text_outline = text_outline
        self.letter_spacing = letter_spacing
        self.width = 0.0
        self.height = leading

    def _advance(self, text, run):
        character_count = max(0, len(text) - 1)
        return (pdfmetrics.stringWidth(text, run.font_name, run.font_size) +
                character_count * self.letter_spacing)

    def _layout(self):
        position = 0.0
        placements = []
        tab_pitch = 8 * mm

        for run in self.runs:
            text_parts = run.text.split('\t')
            for part_number, text_part in enumerate(text_parts):
                if text_part:
                    placements.append((position, text_part, run))
                    position += self._advance(text_part, run)
                if part_number != len(text_parts) - 1:
                    position = (floor(position / tab_pitch) + 1) * tab_pitch

        return placements, position

    def wrap(self, available_width, available_height):
        _placements, required_width = self._layout()
        self.width = required_width
        return required_width, self.height

    def draw(self):
        placements, _required_width = self._layout()
        if not placements:
            return

        largest_ascent = max(
            pdfmetrics.getAscent(run.font_name, run.font_size)
            for _position, _text, run in placements
        )
        baseline = self.height - largest_ascent

        for position, text, run in placements:
            text_object = self.canv.beginText(position, baseline)
            text_object.setFont(run.font_name, run.font_size)
            text_object.setFillColor(run.color)
            if self.letter_spacing:
                text_object.setCharSpace(self.letter_spacing)
            if self.text_outline is not None:
                self.canv.setLineWidth(self.text_outline.width)
                text_object.setStrokeColor(self.text_outline.color)
                text_object.setTextRenderMode(2)
            text_object.textOut(text)
            self.canv.drawText(text_object)

            if run.underline:
                # This mirrors ReportLab Paragraph's <u> support for the
                # tabbed renderer, whose runs are drawn directly on the
                # canvas.  The conventional underline sits just below the
                # font baseline and follows the rendered run width.
                underline_y = baseline - run.font_size * 0.1
                self.canv.setStrokeColor(run.color)
                self.canv.setLineWidth(max(0.5, run.font_size * 0.05))
                self.canv.line(position, underline_y,
                               position + self._advance(text, run), underline_y)


def getTabbedTextLine(paragraph, pdf, additional_fonts, body_font, body_size,
                      body_weight, body_style, font_scale_factor,
                      leading, state: ConversionState, text_outline=None, letter_spacing=0.0):
    """Return a direct-drawing flowable for a supported tabbed paragraph.

    ``None`` tells the caller to use the existing Paragraph implementation.
    That preserves its established handling of complicated markup, but its
    tab characters remain an approximation rather than genuine tab stops.
    """
    if '\t' not in ''.join(paragraph.itertext()):
        return None
    if paragraph.get('align') not in (None, 'left'):
        return None
    if paragraph.find('.//br') is not None:
        return None

    runs = []

    def add_run(text, item):
        if text is None or text == '':
            return
        font, font_size, weight, item_style = CollectFontInfo(
            item, pdf, additional_fonts, body_font, body_size, body_weight,
            font_scale_factor, state)
        try:
            font_name = tt2ps(font, IsBold(weight),
                              IsItalic(item_style, body_style))
        except ValueError:
            # A configured font may be an individual face rather than a
            # ReportLab font family.  It remains usable, but has no mapped
            # bold/italic counterpart.
            font_name = font

        # Canvas.getAvailableFonts() contains the built-in fonts only; it
        # omits the registered TrueType variants (for example
        # ``EB Garamond Bold``).  Use pdfmetrics' registry so tabs retain the
        # same bold and italic face selected by ordinary Paragraph handling.
        if font_name not in pdfmetrics.getRegisteredFontNames():
            font_name = font
        color = reportlab.lib.colors.HexColor(
            item_style.get('color', body_style.get('color', '#000000')))
        runs.append(TabbedTextRun(
            text, font_name, font_size, color,
            IsUnderline(item_style, body_style)))

    add_run(paragraph.text, paragraph)
    for item in paragraph:
        if item.tag != 'span':
            return None
        add_run(item.text, item)
        add_run(item.tail, paragraph)

    return TabbedTextLine(runs, leading, text_outline, letter_spacing)
