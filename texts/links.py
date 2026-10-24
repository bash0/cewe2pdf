"""Find literal album web addresses and add invisible PDF link annotations."""

import logging
import re

from lxml import html
import pymupdf


_URL = re.compile(r'https?://[^\s<]+', re.IGNORECASE)
_TRAILING_PUNCTUATION = '.,;:!'


def getAlbumTextUrls(fotobook):
    """Return literal HTTP(S) addresses from CEWE text-area HTML.

    Parsing embedded HTML avoids treating its document type declaration as
    album text. The addresses are later located in the finished PDF, after
    the normal CEWE text layout has completed.
    """
    urls = set()
    for textElement in fotobook.findall('.//text'):
        if textElement.text is None:
            continue
        try:
            document = html.fromstring(textElement.text)
        except (TypeError, ValueError):
            continue
        body = document.find('body')
        if body is not None:
            paragraphs = body.xpath('.//p') or [body]
            for paragraph in paragraphs:
                urls.update(_urlsInText(_textWithBreaks(paragraph)))
    return urls


def _textWithBreaks(element):
    """Join inline text while retaining explicit HTML line breaks."""
    textParts = [element.text or '']
    for child in element:
        if child.tag.lower() == 'br':
            textParts.append('\n')
        else:
            textParts.append(_textWithBreaks(child))
        textParts.append(child.tail or '')
    return ''.join(textParts)


def addWebLinksToPdf(pdfFileName, urls):
    """Overlay external-link rectangles without changing rendered text."""
    if not urls:
        return 0

    renderedPdf = pymupdf.open(pdfFileName)
    linkCount = 0
    try:
        for page in renderedPdf:
            words = page.get_text('words', sort=True)
            for url in urls:
                for rects in _findUrlRectangles(words, url):
                    # A PDF link annotation has one rectangular hit area.
                    # Keeping one annotation per wrapped URL makes link lists
                    # in readers such as MJ PDF show duplicate destinations.
                    # Its enclosing rectangle is a slightly more generous
                    # hit target in return for representing one logical URL
                    # as one logical PDF link.
                    page.insert_link({
                        'kind': pymupdf.LINK_URI,
                        'from': _enclosingRectangle(rects),
                        'uri': url,
                    })
                    linkCount += 1
        if linkCount:
            renderedPdf.save(pdfFileName, incremental=True, encryption=0)
    finally:
        renderedPdf.close()

    if linkCount == 0:
        logging.warning('Could not locate any visible text for %d web link(s).', len(urls))
    else:
        logging.debug('Added %d PDF web-link annotation(s).', linkCount)
    return linkCount


def _urlsInText(text):
    return {_stripTrailingPunctuation(url) for url in _URL.findall(text)}


def _stripTrailingPunctuation(url):
    """Discard prose punctuation without losing brackets which belong to a URL."""
    url = url.rstrip(_TRAILING_PUNCTUATION)
    for closing, opening in ((')', '('), (']', '['), ('}', '{')):
        while url.endswith(closing) and url.count(closing) > url.count(opening):
            url = url[:-1]
    return url


def _enclosingRectangle(rectangles):
    """Return the smallest rectangle containing all visible URL fragments."""
    enclosingRectangle = pymupdf.Rect(rectangles[0])
    for rectangle in rectangles[1:]:
        enclosingRectangle.include_rect(rectangle)
    return enclosingRectangle


def _findUrlRectangles(words, url):
    """Yield groups of PDF word rectangles spelling visible occurrences of ``url``."""
    # PDF readers can report the tiny slash-break spaces as separate words or
    # text blocks. Match the exact URL in the page's reading order across those
    # boundaries; any unrelated word interrupts the match.
    for startIndex, word in enumerate(words):
        # A styled URL can touch its preceding opening parenthesis. PyMuPDF
        # then returns one word such as ``(https:/``. Start matching at the
        # scheme rather than requiring the PDF word to start with it.
        wordText = word[4]
        schemeStart = wordText.lower().find('http')
        if schemeStart < 0:
            continue
        firstFragment = wordText[schemeStart:]
        if firstFragment.startswith(url):
            yield [pymupdf.Rect(*word[:4])]
            continue
        if not url.startswith(firstFragment):
            continue

        matchedText = firstFragment
        fragmentRectangles = [pymupdf.Rect(*word[:4])]
        for nextWord in words[startIndex + 1:]:
            nextWordText = nextWord[4]
            candidateText = matchedText + nextWordText
            if not url.startswith(candidateText):
                # The last visible fragment can include sentence punctuation.
                # It remains part of the clickable rectangle, but not the URL.
                if _stripTrailingPunctuation(candidateText) == url:
                    fragmentRectangles.append(pymupdf.Rect(*nextWord[:4]))
                    yield fragmentRectangles
                break
            fragmentRectangles.append(pymupdf.Rect(*nextWord[:4]))
            matchedText = candidateText
            if matchedText == url:
                yield fragmentRectangles
                break
