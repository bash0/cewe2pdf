"""CEWE text-outline parsing and ReportLab paragraph support."""

from dataclasses import dataclass
import logging

from reportlab.platypus import Paragraph

from colorUtils import ReorderColorBytesMcf2Rl


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
    if width_text is None or color_text is None:
        logging.warning('Ignoring incomplete text outline setting')
        return None

    try:
        width_mcf = float(width_text)
        color = ReorderColorBytesMcf2Rl(color_text)
    except (TypeError, ValueError):
        logging.warning(f"Ignoring invalid text outline setting color={color_text!r}, width={width_text!r}")
        return None

    if width_mcf <= 0 or color.alpha == 0:
        return None

    return TextOutline(color, width_mcf * mcf_to_reportlab)


class TextOutlineParagraph(Paragraph):
    """A normal ReportLab paragraph which optionally strokes its text glyphs."""

    def beginText(self, x, y):
        text_object = super().beginText(x, y)
        outline = getattr(self.style, 'textOutline', None)
        if outline is not None:
            # PDF text mode 2 paints each glyph with its fill and its stroke.
            # The canvas line width is emitted before ReportLab writes the text
            # object, so the same graphics state applies to every wrapped line.
            self.canv.setLineWidth(outline.width)
            text_object.setStrokeColor(outline.color)
            text_object.setTextRenderMode(2)
        return text_object
