"""Support for simple HTML lists imported into CEWE text areas.

CEWE creates ``ul`` and ``ol`` elements when a list is pasted from another
application.  Its editor does not offer equivalent list creation tools, and
the exact marker positioning is not documented.  This module deliberately
supports only the flat imported lists currently observed in MCF files.
"""

# List processing receives the same text-rendering inputs as ordinary
# paragraphs so it can honour fonts, line scales, outlines and shrink retries.
# Keeping that interface avoids a second, subtly different text pipeline.
# pylint: disable=too-many-arguments,too-many-locals,too-many-nested-blocks
# pylint: disable=too-many-branches,too-many-statements

import html
import logging
from math import floor
from typing import Any

import reportlab.lib.enums
from lxml import etree
from reportlab.lib.styles import ParagraphStyle

from conversionState import ConversionState
from text import (AppendItemTextInStyle, AppendSpanEnd, AppendSpanStart,
                  AppendText, CollectFontInfo)
from textoutlines import TextEffectsParagraph


def processTextLists(pdf_flowableList, forceLeading, paragraphText: str, additional_fonts, body,  # noqa: C901
                     bodyfont: str | Any, bodyfs: int, bstyle: dict[Any, Any], bweight: int, pdf,
                     pdf_styleN, fontScaleFactor: float, unprocessed_children: set[Any], line_scales,
                     state: ConversionState) -> str:
    """Convert CEWE's imported HTML ``ul`` and ``ol`` elements to paragraphs.

    A marker is added to each ReportLab Paragraph and a hanging indent keeps
    continuation lines aligned.  Nested lists and non-standard list markers
    are intentionally left for the ordinary HTML path until real examples
    justify more elaborate handling.
    """
    htmlLists = body.findall("ul") + body.findall("ol")

    for htmlList in htmlLists:
        unprocessed_children.discard(htmlList)

        listItems = htmlList.findall("li")
        try:
            listNumber = int(htmlList.get('start', '1'))
        except ValueError:
            logging.warning(f"Ignoring invalid ordered-list start value {htmlList.get('start')}")
            listNumber = 1

        for listItem in listItems:
            maxFontSize = 0

            listStyle = ParagraphStyle('list_item', parent=pdf_styleN)
            markerIndent = bodyfs * 1.65
            listStyle.leftIndent = markerIndent
            listStyle.firstLineIndent = -markerIndent / 2
            markerText = f'{listNumber}. ' if htmlList.tag == 'ol' else '• '
            listNumber += 1

            if listItem.get('align') == 'center':
                listStyle.alignment = reportlab.lib.enums.TA_CENTER
            elif listItem.get('align') == 'right':
                listStyle.alignment = reportlab.lib.enums.TA_RIGHT
            elif listItem.get('align') == 'justify':
                listStyle.alignment = reportlab.lib.enums.TA_JUSTIFY
            else:
                listStyle.alignment = reportlab.lib.enums.TA_LEFT

            lineHeight = 1.0
            itemStyleAttribute = listItem.get('style')
            if itemStyleAttribute is not None:
                itemStyle = dict(kv.split(':') for kv in
                                 itemStyleAttribute.lstrip(' ').rstrip(';').split('; '))
                if 'line-height' in itemStyle:
                    try:
                        lineHeight = floor(float(itemStyle['line-height'].strip('%'))) / 100.0
                    except ValueError:
                        logging.warning(f"Ignoring invalid list item line-height setting {itemStyleAttribute}")
            leadingFactor = line_scales.lineScaleForFont(bodyfont) * lineHeight

            paragraphText = '<para autoLeading="max">'
            itemChildren = listItem.findall(".*")
            markerPlusText = markerText + (listItem.text if listItem.text is not None else '')
            paragraphText, maxFontSize = AppendItemTextInStyle(
                paragraphText, markerPlusText, listItem, pdf, additional_fonts,
                bodyfont, bodyfs, bweight, bstyle, fontScaleFactor, state)

            for item in itemChildren:
                if item.tag == 'br':
                    paragraphText += '<br/>'
                    if item.tail:
                        paragraphText, maxFontSize = AppendItemTextInStyle(
                            paragraphText, item.tail, listItem, pdf, additional_fonts,
                            bodyfont, bodyfs, bweight, bstyle, fontScaleFactor, state)
                elif item.tag == 'span':
                    spanfont, spanfs, spanweight, spanstyle = CollectFontInfo(
                        item, pdf, additional_fonts, bodyfont, bodyfs, bweight,
                        fontScaleFactor, state)
                    maxFontSize = max(maxFontSize, spanfs)
                    paragraphText = AppendSpanStart(
                        paragraphText, spanfont, spanfs, spanweight, spanstyle, bstyle)
                    if item.text is not None:
                        paragraphText = AppendText(paragraphText, html.escape(item.text))

                    breaks = item.findall('.//br')
                    if breaks:
                        paragraphText = AppendSpanEnd(paragraphText, spanweight, spanstyle, bstyle)
                        for lineBreak in breaks:
                            paragraphText += '<br/>'
                            if lineBreak.tail:
                                paragraphText, maxFontSize = AppendItemTextInStyle(
                                    paragraphText, lineBreak.tail, item, pdf, additional_fonts,
                                    bodyfont, bodyfs, bweight, bstyle, fontScaleFactor, state)
                    else:
                        paragraphText = AppendSpanEnd(paragraphText, spanweight, spanstyle, bstyle)

                    if item.tail is not None:
                        paragraphText = AppendText(paragraphText, html.escape(item.tail))
                else:
                    logging.warning(
                        f"Ignoring unhandled tag {item.tag} in list item "
                        f"(tag content: {etree.tostring(item, encoding='unicode')[:100]}...)")

            paragraphText += '</para>'
            useFontSize = maxFontSize if maxFontSize > 0 else bodyfs
            listStyle.leading = (useFontSize * forceLeading if forceLeading is not None
                                 else useFontSize * leadingFactor)
            pdf_flowableList.append(TextEffectsParagraph(paragraphText, listStyle))

    return paragraphText
