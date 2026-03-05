from math import floor

import html
import logging
import reportlab.lib.enums

from reportlab.lib.styles import ParagraphStyle

from fontHandling import getAvailableFont, getMissingFontSubstitute, noteFontSubstitution
from lineScales import LineScales


def CreateParagraphStyle(textcolor, font, fontsize, font_size_adjust):
    # apply a tiny adjustment to the font size used by ReportLab for measuring
    adjusted_fs = fontsize * font_size_adjust
    parastyle = ParagraphStyle(None, None,
        alignment=reportlab.lib.enums.TA_LEFT,  # will often be overridden
        fontSize=adjusted_fs,
        fontName=font,
        leading=adjusted_fs * LineScales.lineScaleForFont(font),  # line spacing (text + leading)
        borderPadding=0,
        borderWidth=0,
        leftIndent=0,
        rightIndent=0,
        embeddedHyphenation=1,  # allow line break on existing hyphens
        # backColor=backgroundColor, # text bg not used since ColorFrame colours the whole bg
        textColor=textcolor)
    return parastyle


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


def CollectFontInfo(item, pdf, additional_fonts, dfltfont, dfltfs, bweight, fontScaleFactor):
    if item is None:
        return dfltfont, dfltfs, bweight, {}
    spanfont = dfltfont
    spanfs = dfltfs
    spanweight = bweight
    spanstyle = dict([kv.split(':') for kv in
                    item.get('style').lstrip(' ').rstrip(';').split('; ')])
    if 'font-family' in spanstyle:
        spanfamily = spanstyle['font-family'].strip("'")
        spanfont = getAvailableFont(spanfamily, pdf, additional_fonts)

    if 'font-weight' in spanstyle:
        try:
            spanweight = int(Dequote(spanstyle['font-weight']))
        except: # noqa: E722 # pylint: disable=bare-except
            spanweight = 400

    if 'font-size' in spanstyle:
        # preserve fractional point sizes and apply the global adjustment
        try:
            spanfs = float(spanstyle['font-size'].strip("pt"))
        except Exception:
            spanfs = float(dfltfs)
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


def AppendText(paratext, newtext):
    if newtext is None:
        return paratext
    return paratext + newtext.replace('\t', '&nbsp;&nbsp;&nbsp;')


def AppendBreak(paragraphText, parachild):
    br = parachild
    paragraphText = AppendText(paragraphText, "<br></br>&nbsp;")
    paragraphText = AppendText(paragraphText, br.tail)
    return paragraphText


def AppendSpanStart(paragraphText, font, fsize, fweight, fstyle, outerstyle):
    """
    Remember this is not really HTML, though it looks that way.
    See 6.2 Paragraph XML Markup Tags in the reportlabs user guide.
    """
    # format font size with two decimals so ReportLab receives a stable float
    paragraphText = AppendText(paragraphText, '<font name="' + font + '"' + ' size=' + ("{:.2f}".format(fsize)))

    if 'color' in fstyle:
        paragraphText = AppendText(paragraphText, ' color=' + fstyle['color'])

    # This old strategy doesn't interpret background alpha values correctly, background is
    # now done in processAreaTextTag (credit seaeagle1, changeset 687fe50)
    #    if bgColorAttrib is not None:
    #        paragraphText = AppendText(paragraphText, ' backcolor=' + bgColorAttrib)

    paragraphText = AppendText(paragraphText, '>')

    if IsBold(fweight):  # ref https://www.w3schools.com/csSref/pr_font_weight.asp
        paragraphText = AppendText(paragraphText, "<b>")
    if IsItalic(fstyle, outerstyle):
        paragraphText = AppendText(paragraphText, '<i>')
    if IsUnderline(fstyle, outerstyle):
        paragraphText = AppendText(paragraphText, '<u>')
    return paragraphText


def AppendSpanEnd(paragraphText, weight, style, outerstyle):
    if IsUnderline(style, outerstyle):
        paragraphText = AppendText(paragraphText, '</u>')
    if IsItalic(style, outerstyle):
        paragraphText = AppendText(paragraphText, '</i>')
    if IsBold(weight):
        paragraphText = AppendText(paragraphText, "</b>")
    paragraphText = AppendText(paragraphText, '</font>')
    return paragraphText


def AppendItemTextInStyle(paragraphText, text, item, pdf, additional_fonts, bodyfont, bodyfs, bweight, bstyle, fontScaleFactor): # pylint: disable= too-many-arguments
    pfont, pfs, pweight, pstyle = CollectFontInfo(item, pdf, additional_fonts, bodyfont, bodyfs, bweight, fontScaleFactor)
    paragraphText = AppendSpanStart(paragraphText, pfont, pfs, pweight, pstyle, bstyle)
    if text is None:
        paragraphText = AppendText(paragraphText, "")
    else:
        paragraphText = AppendText(paragraphText, html.escape(text))
    paragraphText = AppendSpanEnd(paragraphText, pweight, pstyle, bstyle)
    return paragraphText, pfs
