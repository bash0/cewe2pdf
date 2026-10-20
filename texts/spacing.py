"""CEWE letter-spacing parsing."""

import logging
from collections import deque

from reportlab.pdfbase.pdfmetrics import getAscentDescent, stringWidth
from reportlab.platypus.paragraph import (
    FragLine, ParaLines, _getFragWords, _HSFrag, sameFrag)


def getLetterSpacing(text_format, mcf_to_reportlab):
    """
    Return CEWE's area-wide letter spacing in ReportLab points.

    ``letterSpacing`` is stored in MCF units (0.1 mm), unlike the equivalent
    HTML CSS declaration which is expressed in Qt pixels.  Using the MCF value
    avoids an otherwise undocumented pixel-to-point conversion.

    This initial implementation deliberately applies one value to the whole
    text area. Per-span character spacing is not implemented.
    """
    if text_format is None:
        return 0.0

    spacing_text = text_format.get('letterSpacing')
    if spacing_text is None:
        return 0.0

    try:
        return float(spacing_text) * mcf_to_reportlab
    except ValueError:
        logging.warning(f"Ignoring invalid text letterSpacing setting {spacing_text!r}")
        return 0.0


def _textAdvance(fragment, spacing):
    """Include the advance after the last character, as PDF text does."""
    return (stringWidth(fragment.text, fragment.fontName, fragment.fontSize)
        + len(fragment.text) * spacing)


def _splitSpacedWord(fragments, width, spacing):
    """Split an overlong word without losing its inline font/style changes."""
    head = []
    tail = []
    advance = 0.0
    full = False
    for fragment in fragments:
        prefix = ''
        for index, character in enumerate(fragment.text):
            characterAdvance = stringWidth(character, fragment.fontName, fragment.fontSize) + spacing
            if full or ((head or prefix) and advance + characterAdvance - spacing > width):
                tail.append(fragment.clone(text=fragment.text[index:]))
                full = True
                break
            prefix += character
            advance += characterAdvance
        if prefix:
            head.append(fragment.clone(text=prefix))
    return head, tail


def _getSpacedWords(fragments, embeddedHyphenation):
    words = deque()
    # _getFragWords and _HSFrag are ReportLab's word/style representation:
    # _HSFrag marks a word followed by a collapsible space, not a visible glyph.
    for word in _getFragWords(fragments):
        fragments = [fragment.clone(text=text) for fragment, text in word[1:]]
        portions = [[]]
        for fragment in fragments:
            # Preserve the configured opportunity to break after existing
            # hyphens, including hyphenated words spanning inline styles.
            parts = fragment.text.split('-') if embeddedHyphenation else [fragment.text]
            for index, part in enumerate(parts):
                hasHyphen = index < len(parts) - 1
                portions[-1].append(fragment.clone(text=part + ('-' if hasHyphen else '')))
                if hasHyphen:
                    portions.append([])
        for index, portion in enumerate(portions):
            trailingSpace = index == len(portions) - 1 and isinstance(word, _HSFrag)
            words.append((portion, trailingSpace))

    return words


def breakSpacedLines(paragraph, widths, spacing):
    """Lay out spaced words using ReportLab's parsed text/style fragments.

    ReportLab's ordinary breaker measures glyph widths without PDF character
    spacing. Keep its fragment parser and drawing/height machinery, but measure
    each line's actual advance here. Nothing in ReportLab's shared registries or
    module-level measurement functions is changed for this paragraph.
    """
    if not isinstance(widths, (tuple, list)):
        widths = [widths]
    words = _getSpacedWords(paragraph.frags, paragraph.style.embeddedHyphenation)

    lines = []
    line = []
    advance = 0.0
    pendingSpace = None

    def finishLine(explicitBreak=False):
        nonlocal line, advance, pendingSpace
        width = widths[min(len(lines), len(widths) - 1)]
        textWidth = advance - spacing if line else 0
        bounds = [getAscentDescent(fragment.fontName, fragment.fontSize) for fragment in line]
        lines.append(FragLine(
            extraSpace=width - textWidth, wordCount=1 + sum(fragment.text.count(' ') for fragment in line),
            lineBreak=explicitBreak, words=line,
            fontSize=max((fragment.fontSize for fragment in line), default=paragraph.style.fontSize),
            ascent=max((bound[0] for bound in bounds), default=paragraph.style.fontSize),
            descent=min((bound[1] for bound in bounds), default=0), maxWidth=width))
        line = []
        advance = 0.0
        pendingSpace = None

    while words:
        fragments, trailingSpace = words.popleft()
        if getattr(fragments[0], 'lineBreak', False):
            finishLine(explicitBreak=True)
            continue
        wordAdvance = sum(_textAdvance(fragment, spacing) for fragment in fragments)
        gap = _textAdvance(pendingSpace, spacing) if line and pendingSpace else 0
        width = widths[min(len(lines), len(widths) - 1)]
        if line and advance + gap + wordAdvance - spacing > width:
            finishLine()
            width = widths[min(len(lines), len(widths) - 1)]
            gap = 0
        if not line and wordAdvance - spacing > width and paragraph.style.splitLongWords:
            fragments, remainder = _splitSpacedWord(fragments, width, spacing)
            if remainder:
                words.appendleft((remainder, trailingSpace))
                trailingSpace = False
            wordAdvance = sum(_textAdvance(fragment, spacing) for fragment in fragments)
        if line and pendingSpace is not None:
            line.append(pendingSpace)
            advance += gap
        for fragment in fragments:
            if line and sameFrag(line[-1], fragment):
                line[-1].text += fragment.text
            else:
                line.append(fragment.clone())
        advance += wordAdvance
        pendingSpace = fragments[-1].clone(text=' ') if trailingSpace else None
    if line:
        finishLine()
    return ParaLines(kind=1, lines=lines)
