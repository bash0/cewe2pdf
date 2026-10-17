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
            urls.update(_urlsInText(''.join(body.itertext())))
    return urls


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
                for rects in _rectanglesForUrl(words, url):
                    for rect in rects:
                        page.insert_link({
                            'kind': pymupdf.LINK_URI,
                            'from': rect,
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
    return {url.rstrip(_TRAILING_PUNCTUATION) for url in _URL.findall(text)}


def _rectanglesForUrl(words, url):
    """Yield visible word rectangles which together spell ``url``."""
    # Text from separate areas can share a visual line.  ``sort=True`` puts
    # those words beside one another, which would interrupt a URL wrapped in
    # a single text area.  Follow only the words in each PDF text block.
    blocks = {}
    for word in words:
        blocks.setdefault(word[5], []).append(word)

    for blockWords in blocks.values():
        orderedWords = sorted(blockWords, key=lambda word: (word[6], word[7]))
        yield from _rectanglesWithinBlock(orderedWords, url)


def _rectanglesWithinBlock(words, url):
    """Yield URL rectangles from one continuous PDF text block."""
    for startIndex, word in enumerate(words):
        wordText = word[4]
        if wordText.startswith(url):
            yield [pymupdf.Rect(*word[:4])]
            continue
        if not url.startswith(wordText):
            continue

        matchedText = wordText
        rectangles = [pymupdf.Rect(*word[:4])]
        for nextWord in words[startIndex + 1:]:
            extendedText = matchedText + nextWord[4]
            if not url.startswith(extendedText):
                # The last visible fragment can include sentence punctuation.
                # It remains part of the clickable rectangle, but not the URL.
                if extendedText.rstrip(_TRAILING_PUNCTUATION) == url:
                    rectangles.append(pymupdf.Rect(*nextWord[:4]))
                    yield rectangles
                break
            rectangles.append(pymupdf.Rect(*nextWord[:4]))
            matchedText = extendedText
            if matchedText == url:
                yield rectangles
                break
