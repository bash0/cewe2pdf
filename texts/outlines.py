"""CEWE text-outline parsing and ReportLab paragraph support."""

from dataclasses import dataclass
import logging

from reportlab.platypus import Paragraph

from colorUtils import ReorderColorBytesMcf2Rl
from texts.spacing import breakSpacedLines


@dataclass(frozen=True)
class TextOutline:
    """The visible outline applied to a CEWE text area."""

    color: object
    width: float


def getTextOutline(text_tag, mcf_to_reportlab):
    """
    Return the visible text-area outline, or ``None`` when there is none.

    CEWE writes the effective area-wide setting in an ``outline`` child of
    ``text``.  ``textFormat.hasOutline`` is only an editor flag: it may be set
    even when the stored outline colour is transparent.
    """
    outline_tag = text_tag.find('outline')
    if outline_tag is None:
        return None

    width_text = outline_tag.get('width')
    color_text = outline_tag.get('color')
    if width_text is None:
        logging.warning('Ignoring text outline setting without a width')
        return None

    try:
        width_mcf = float(width_text)
    except ValueError:
        logging.warning(f"Ignoring invalid text outline width {width_text!r}")
        return None

    # CEWE writes <outline width="0"/> for normal, unoutlined text.  In that
    # common disabled case no colour is stored, and no warning is appropriate.
    if width_mcf <= 0:
        return None

    if color_text is None:
        # CEWE also writes a positive width without a colour for text whose
        # outline control is present but not assigned a visible colour.
        return None

    try:
        color = ReorderColorBytesMcf2Rl(color_text)
    except (TypeError, ValueError):
        logging.warning(f"Ignoring invalid text outline colour {color_text!r}")
        return None

    if color.alpha == 0:
        return None

    return TextOutline(color, width_mcf * mcf_to_reportlab)


class TextEffectsParagraph(Paragraph):
    """A ReportLab paragraph which applies CEWE text effects when requested."""

    def breakLines(self, width):
        letter_spacing = getattr(self.style, 'letterSpacing', 0.0)
        if letter_spacing:
            lines = breakSpacedLines(self, width, letter_spacing)
            # ReportLab uses this measured width when sizing/splitting the
            # finished paragraph, alongside the normal FragLine structures.
            self._width_max = max((line.maxWidth - line.extraSpace for line in lines.lines), default=0)  # pylint: disable=attribute-defined-outside-init
            return lines
        return super().breakLines(width)

    def beginText(self, x, y):
        text_object = super().beginText(x, y)
        letter_spacing = getattr(self.style, 'letterSpacing', 0.0)
        if letter_spacing != 0.0:
            text_object.setCharSpace(letter_spacing)

        outline = getattr(self.style, 'textOutline', None)
        if outline is not None:
            # PDF text mode 2 paints each glyph with its fill and its stroke.
            # The canvas line width is emitted before ReportLab writes the text
            # object, so the same graphics state applies to every wrapped line.
            self.canv.setLineWidth(outline.width)
            text_object.setStrokeColor(outline.color)
            text_object.setTextRenderMode(2)
        return text_object
