"""Interpret CEWE's page layout as ordered pages ready for rendering.

MCF files use several ``pagenr=0`` elements for covers and inside covers, and
store ordinary album content in two-page bundles.  This module contains those
format-specific rules.  It deliberately does not create a PDF or draw a
background: :mod:`pages` consumes the resolved pages and performs rendering.
"""

from dataclasses import dataclass
import logging
from math import floor
from typing import Any, Iterator

from ceweInfo import ProductInfo, PdfProductStyle
from pageSelection import PageSelection
from pageTypes import PageProcessingType


@dataclass(frozen=True)
class ResolvedPage:
    """One CEWE page element and the rendering role assigned to it."""

    element: Any
    page_number: int
    page_type: PageProcessingType
    odd_page: bool
    last_page: bool
    source_number: int
    finish_page: bool = True


def getPageElementForPageNumber(fotobook, pageNumber):
    """Return the MCF page element containing the requested normal page."""
    return fotobook.find(f"./page[@pagenr='{floor(2 * (pageNumber / 2))}']")


def _fullCoverPage(fotobook):
    """Return CEWE's single usable full-cover element, if present."""
    fullCoverPages = [candidate for candidate in
        fotobook.findall("./page[@pagenr='0'][@type='FULLCOVER']")
        + fotobook.findall("./page[@pagenr='0'][@type='fullcover']")
        if candidate.find("./area") is not None]
    if len(fullCoverPages) == 1:
        return fullCoverPages[0]
    return None


def _openingContentPage(fotobook):
    """Return CEWE's pagenr=0 record holding page 1's content."""
    pages = [candidate for candidate in
        fotobook.findall("./page[@pagenr='0'][@type='EMPTY']")
        + fotobook.findall("./page[@pagenr='0'][@type='emptypage']")
        if candidate.find("./area") is not None or
        candidate.find("./background[@alignment='1']") is not None]
    return pages[0] if pages else None


def _backInsideCoverPage(fotobook):
    """Return the pagenr=0 element CEWE uses for the back inside cover."""
    pages = [candidate for candidate in
        fotobook.findall("./page[@pagenr='0'][@type='EMPTY']")
        + fotobook.findall("./page[@pagenr='0'][@type='emptypage']")
        if candidate.find("./area") is None or
        candidate.find("./background[@alignment='3']") is not None]
    return pages[0] if pages else None


def resolvePages(fotobook, productStyle, pageCount, pageNumbers=None) -> Iterator[ResolvedPage]:  # noqa: C901
    """Yield selected output pages in CEWE's required rendering order.

    The selection rules intentionally reproduce the original renderer's
    behaviour.  In particular, rendering an album's final ordinary page is
    followed by its back inside cover, while the front inside-cover background
    is rendered first so it cannot obscure its elements.
    """

    selection = PageSelection.from_value(pageNumbers)
    selectedContentPages = _selectedContentPages(
        selection, productStyle, pageCount - 2)

    if ProductInfo.isAlbumProduct(productStyle):
        yield from _resolveAlbumPages(
            fotobook, productStyle, pageCount, selection, selectedContentPages)
        return

    if productStyle == PdfProductStyle.Calendar:
        yield from _resolveCalendarPages(
            fotobook, pageCount, selection, selectedContentPages)
        return

    if productStyle == PdfProductStyle.MemoryCard:
        yield from _resolveMemoryCardPages(
            fotobook, selection, selectedContentPages)
        return

    raise ValueError(f'Unsupported PDF product style: {productStyle!r}')


def _resolveCalendarPages(fotobook, pageCount, selection, selectedContentPages):
    """Yield independently renderable calendar cover and month pages."""
    calendarPages = fotobook.findall("./page[@type='calendarcoverfront']") \
        + fotobook.findall("./page[@type='normalpage']")
    for page in calendarPages:
        pageNumber = int(page.get('pagenr'))
        selected = (_wantsCover(selection) if pageNumber == 0
                    else _wantsContentPage(selection, selectedContentPages, pageNumber))
        if selected:
            yield ResolvedPage(page, pageNumber, PageProcessingType.CalendarPage,
                               False, pageNumber == pageCount - 1, pageNumber)


def _resolveMemoryCardPages(fotobook, selection, selectedContentPages):
    """Yield CEWE Photo Pairs cards, which are independent normal pages."""
    for page in fotobook.findall("./page[@type='normalpage']"):
        pageNumber = int(page.get('pagenr'))
        if _wantsContentPage(selection, selectedContentPages, pageNumber):
            yield ResolvedPage(page, pageNumber, PageProcessingType.RegularPage,
                               _isOddPage(pageNumber), False, pageNumber)


def _resolveAlbumPages(fotobook, productStyle, pageCount, selection,
                       selectedContentPages):
    """Yield album covers, content pages, and required endpaper operations."""
    for number in range(pageCount):
        lastPage = _isLastPage(number, pageCount)

        # Normal MCF pages run from pagenr 1 to 26. A default album also
        # contains five pagenr 0 elements for covers and inside covers.
        if number == 0 or _isBackCover(number, pageCount):
            page = _fullCoverPage(fotobook)
            if page is None:
                logging.warning("Cannot locate a cover page, is this really an album?")
                continue
            if ProductInfo.isAlbumDoubleSide(productStyle) and _isBackCover(number, pageCount):
                # The final double-page output already includes the left side
                # of the cover, so CEWE's cover element must not be repeated.
                continue
            if not _wantsCover(selection):
                continue
            yield ResolvedPage(page, number, PageProcessingType.Cover,
                               number == 0, lastPage, number)
            continue

        if ProductInfo.isAlbumProduct(productStyle) and number == 1:
            # Draw the first normal page's background before the inside-cover
            # elements. It is a prerequisite of rendering content page one.
            realFirstPages = fotobook.findall("./page[@pagenr='1'][@type='normalpage']")
            if realFirstPages and _wantsContentPage(selection, selectedContentPages, 1):
                yield ResolvedPage(realFirstPages[0], 1,
                                   PageProcessingType.FrontInsideCoverBackground,
                                   True, False, number)

            page = _openingContentPage(fotobook)
            if page is None:
                logging.error(f'Failed to locate opening content record when processing page {number}')
                continue
            if _wantsContentPage(selection, selectedContentPages, 1):
                yield ResolvedPage(page, 1, PageProcessingType.OpeningContentPage,
                                   True, lastPage, number)
            continue

        if ProductInfo.isAlbumProduct(productStyle) and lastPage:
            # The final ordinary page and the back inside cover are two
            # distinct rendering operations in the same position in the MCF.
            if _wantsContentPage(selection, selectedContentPages, number):
                yield ResolvedPage(getPageElementForPageNumber(fotobook, number), number,
                                   PageProcessingType.RegularPage, _isOddPage(number),
                                   True, number, finish_page=False)

            page = _backInsideCoverPage(fotobook)
            if page is None:
                logging.error(f'Failed to locate final emptypage when processing last page {number}')
                continue
            backInsideCoverNumber = number + 1
            if _wantsContentPage(selection, selectedContentPages, number):
                yield ResolvedPage(page, backInsideCoverNumber,
                                   PageProcessingType.BackInsideCover,
                                   _isOddPage(backInsideCoverNumber), True, number)
            continue

        if not _wantsContentPage(selection, selectedContentPages, number):
            continue
        yield ResolvedPage(getPageElementForPageNumber(fotobook, number), number,
                           PageProcessingType.RegularPage, _isOddPage(number),
                           lastPage, number)


def _selectedContentPages(selection, productStyle, finalContentPage):
    """Return requested content pages, expanded to double-page spread mates."""
    selectedContentPages = set() if selection is None else set(selection.page_numbers)
    if ProductInfo.isAlbumDoubleSide(productStyle):
        return _expandDoublePageSelection(selectedContentPages, finalContentPage)
    return selectedContentPages


def _wantsContentPage(selection, selectedContentPages, pageNumber):
    return selection is None or pageNumber in selectedContentPages


def _wantsCover(selection):
    return selection is None or selection.include_cover


def _isBackCover(number, pageCount):
    return number == pageCount - 1


def _isLastPage(number, pageCount):
    return number == pageCount - 2


def _isOddPage(number):
    return number % 2 == 1


def _expandDoublePageSelection(selectedContentPages, finalContentPage):
    """Add the facing content page for each requested double-page spread."""
    expanded = set(selectedContentPages)
    for pageNumber in selectedContentPages:
        if pageNumber in (1, finalContentPage):
            continue
        facingPage = pageNumber - 1 if pageNumber % 2 else pageNumber + 1
        if 2 <= facingPage < finalContentPage:
            expanded.add(facingPage)
    return expanded
