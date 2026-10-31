import html
import re

import reportlab.lib.enums

from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics

from fonts.manager import getAvailableFont
from fonts.line_scales import LineScales
from conversionState import ConversionState


_WEB_ADDRESS = re.compile(r'https?://[^\s<]+', re.IGNORECASE)
# ReportLab's zero-size spans have invalid leading.  0.01 pt is below any
# visible PDF resolution while still producing a genuine word boundary.
_ZERO_WIDTH_SPACE = '<font size="0.01"> </font>'


def CreateParagraphStyle(textcolor, font, fontsize, font_size_adjust, line_scales: LineScales):
    # apply a tiny adjustment to the font size used by ReportLab for measuring
    adjusted_fs = fontsize * font_size_adjust
    parastyle = ParagraphStyle(None, None,
        alignment=reportlab.lib.enums.TA_LEFT,  # will often be overridden
        fontSize=adjusted_fs,
        fontName=font,
        leading=adjusted_fs * line_scales.lineScaleForFont(font),  # line spacing (text + leading)
        borderPadding=0,
        borderWidth=0,
        leftIndent=0,
        rightIndent=0,
        embeddedHyphenation=1,  # allow line break on existing hyphens
        # backColor=backgroundColor, # text bg not used since ColorFrame colours the whole bg
        textColor=textcolor)
    return parastyle


def LeadingForExplicitLineHeight(font, fontsize, line_height, line_scales: LineScales):
    """
    Return ReportLab leading for a CSS line-height percentage.

    ReportLab's ``autoLeading=\"max\"`` normally grows a line to fit the font's
    ascent and descent.  That is useful for ordinary CEWE text, but it makes an
    explicit 100% line height use the font metrics while larger percentages use
    our configured leading.  Use the same natural line box as the baseline,
    then apply the requested percentage consistently.
    """
    configured_leading = fontsize * line_scales.lineScaleForFont(font)
    try:
        ascent, descent = pdfmetrics.getAscentDescent(font, fontsize)
        natural_leading = ascent - descent
    except KeyError:
        natural_leading = configured_leading
    return max(configured_leading, natural_leading) * line_height


def IsBold(weight):
    return weight > 400


def IsItalic(itemstyle, outerstyle):
    if 'font-style' in itemstyle:
        return itemstyle['font-style'].strip(" ") == "italic"
    if 'font-style' in outerstyle:
        return outerstyle['font-style'].strip(" ") == "italic"
    return False


def IsUnderline(itemstyle, outerstyle):
    if 'text-decoration' in itemstyle:
        return itemstyle['text-decoration'].strip(" ") == "underline"
    if 'text-decoration' in outerstyle:
        return outerstyle['text-decoration'].strip(" ") == "underline"
    return False


def Dequote(s):
    """
    If a string has single or double quotes around it, remove them.
    Make sure the pair of quotes match.
    If a matching pair of quotes is not found, return the string unchanged.
    """
    if (s[0] == s[-1]) and s.startswith(("'", '"')):
        return s[1:-1]
    return s

    # we can not delete now, because file is opened by pdf library


def GetUnscaledFontSize(style, defaultSize):
    """Return the font size written in CEWE markup before layout adjustments."""
    if 'font-size' not in style:
        return float(defaultSize)

    try:
        return float(style['font-size'].strip("pt"))
    except Exception: # pylint: disable=broad-except
        return float(defaultSize)


def CollectFontInfo(item, pdf, additional_fonts, dfltfont, dfltfs, bweight,
                    fontScaleFactor, state: ConversionState):
    if item is None:
        return dfltfont, dfltfs, bweight, {}
    spanfont = dfltfont
    spanfs = dfltfs
    spanweight = bweight
    spanstyle = dict([kv.split(':') for kv in
                    item.get('style').lstrip(' ').rstrip(';').split('; ')])
    if 'font-family' in spanstyle:
        spanfamily = spanstyle['font-family'].strip("'")
        spanfont = getAvailableFont(spanfamily, pdf, additional_fonts, state)

    if 'font-weight' in spanstyle:
        try:
            spanweight = int(Dequote(spanstyle['font-weight']))
        except: # noqa: E722 # pylint: disable=bare-except
            spanweight = 400

    # Preserve fractional point sizes before applying the global adjustment.
    spanfs = GetUnscaledFontSize(spanstyle, dfltfs)
    # apply the small adjustment multiplier
    spanfs = spanfs * fontScaleFactor
    return spanfont, spanfs, spanweight, spanstyle


def CollectItemFontFamily(item, dfltfont):
    if item is None:
        return dfltfont
    itemfont = dfltfont
    itemstyle = dict([kv.split(':') for kv in
                    item.get('style').lstrip(' ').rstrip(';').split('; ')])
    if 'font-family' in itemstyle:
        itemfont = itemstyle['font-family'].strip("'")
    return itemfont


def AddBasicText(paratext, newtext):
    """Append trusted ReportLab paragraph markup."""
    if newtext is None:
        return paratext
    return paratext + newtext.replace('\t', '&nbsp;&nbsp;&nbsp;')


def AddAlbumText(paragraphText, text):
    """Append literal CEWE text while preserving its layout.

    Most ordinary CEWE text reaches this function through the ReportLab
    Paragraph route.  The supported simple-tab route is rendered directly by
    ``TabbedTextLine`` before that route and deliberately does not call here.
    If it cannot use that direct renderer, it falls back here and retains the
    older non-breaking-space tab approximation from ``AddBasicText``.

    Web-link annotations are added only after the complete PDF has been laid
    out. That keeps literal URL text subject to exactly the same wrapping as
    CEWE text which is not a link.
    """
    if text is None:
        return paragraphText
    escapedText = html.escape(text)
    # CEWE may wrap a web address after a slash. A literal space in a near-zero
    # font is invisible, but gives ReportLab a genuine word boundary. This
    # prevents ReportLab from splitting path components at arbitrary letters.
    escapedText = _WEB_ADDRESS.sub(_addUrlBreakOpportunities, escapedText)
    return AddBasicText(paragraphText, escapedText)


def _addUrlBreakOpportunities(match):
    """Return a URL with invisible optional breaks after its slashes."""
    return match.group().replace('/', f'/{_ZERO_WIDTH_SPACE}')


def AppendBreak(paragraphText, parachild):
    br = parachild
    paragraphText = AddBasicText(paragraphText, "<br></br>&nbsp;")
    paragraphText = AddAlbumText(paragraphText, br.tail)
    return paragraphText


def AppendSpanStart(paragraphText, font, fsize, fweight, fstyle, outerstyle):
    """
    Remember this is not really HTML, though it looks that way.
    See 6.2 Paragraph XML Markup Tags in the reportlabs user guide.
    """
    # format font size with two decimals so ReportLab receives a stable float
    paragraphText = AddBasicText(paragraphText, f'<font name="{font}" size={fsize:.2f}')

    if 'color' in fstyle:
        paragraphText = AddBasicText(paragraphText, ' color=' + fstyle['color'])

    # This old strategy doesn't interpret background alpha values correctly, background is
    # now done in processAreaTextTag (credit seaeagle1, changeset 687fe50)
    #    if bgColorAttrib is not None:
    #        paragraphText = AddBasicText(paragraphText, ' backcolor=' + bgColorAttrib)

    paragraphText = AddBasicText(paragraphText, '>')

    if IsBold(fweight):  # ref https://www.w3schools.com/csSref/pr_font_weight.asp
        paragraphText = AddBasicText(paragraphText, "<b>")
    if IsItalic(fstyle, outerstyle):
        paragraphText = AddBasicText(paragraphText, '<i>')
    if IsUnderline(fstyle, outerstyle):
        paragraphText = AddBasicText(paragraphText, '<u>')
    return paragraphText


def AppendSpanEnd(paragraphText, weight, style, outerstyle):
    if IsUnderline(style, outerstyle):
        paragraphText = AddBasicText(paragraphText, '</u>')
    if IsItalic(style, outerstyle):
        paragraphText = AddBasicText(paragraphText, '</i>')
    if IsBold(weight):
        paragraphText = AddBasicText(paragraphText, "</b>")
    paragraphText = AddBasicText(paragraphText, '</font>')
    return paragraphText


def AppendItemTextInStyle(paragraphText, text, item, pdf, additional_fonts, bodyfont, bodyfs,
        bweight, bstyle, fontScaleFactor, state: ConversionState): # pylint: disable= too-many-arguments
    pfont, pfs, pweight, pstyle = CollectFontInfo(
        item, pdf, additional_fonts, bodyfont, bodyfs, bweight, fontScaleFactor, state)
    paragraphText = AppendSpanStart(paragraphText, pfont, pfs, pweight, pstyle, bstyle)
    if text is None:
        paragraphText = AddBasicText(paragraphText, "")
    else:
        paragraphText = AddAlbumText(paragraphText, text)
    paragraphText = AppendSpanEnd(paragraphText, pweight, pstyle, bstyle)
    return paragraphText, pfs
