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

from ceweInfo import AlbumInfo
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


def _frontInsideCoverPage(fotobook):
    """Return the pagenr=0 element CEWE uses for the front inside cover."""
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

    def isBackCover(number):
        return number == (pageCount - 1)

    def isLastPage(number):
        return number == (pageCount - 2)

    def isOddPage(number):
        return (number % 2) == 1

    if not AlbumInfo.isAlbumProduct(productStyle):
        # The supported non-album product is CEWE Photo Pairs (MEM3).  It has
        # neither covers nor two-page bundles: each normal-page element is one
        # 6 x 6 cm card.  CEWE numbers cards from one, unlike the zero-based
        # output-page numbering used for album cover processing.
        for page in fotobook.findall("./page[@type='normalpage']"):
            pageNumber = int(page.get('pagenr'))
            if pageNumbers is not None and pageNumber not in pageNumbers:
                continue
            yield ResolvedPage(page, pageNumber, PageProcessingType.RegularPage,
                               isOddPage(pageNumber), False, pageNumber)
        return

    for number in range(pageCount):
        lastPage = isLastPage(number)

        # Normal MCF pages run from pagenr 1 to 26. A default album also
        # contains five pagenr 0 elements for covers and inside covers.
        if AlbumInfo.isAlbumProduct(productStyle) and (number == 0 or isBackCover(number)):
            page = _fullCoverPage(fotobook)
            if page is None:
                logging.warning("Cannot locate a cover page, is this really an album?")
                continue
            if AlbumInfo.isAlbumDoubleSide(productStyle) and isBackCover(number):
                # The final double-page output already includes the left side
                # of the cover, so CEWE's cover element must not be repeated.
                continue
            if pageNumbers is not None and number not in pageNumbers:
                continue
            yield ResolvedPage(page, number, PageProcessingType.Cover,
                               number == 0, lastPage, number)
            continue

        if AlbumInfo.isAlbumProduct(productStyle) and number == 1:
            # Draw the first normal page's background before the inside-cover
            # elements. This is requested by selecting output page zero.
            realFirstPages = fotobook.findall("./page[@pagenr='1'][@type='normalpage']")
            if realFirstPages and (pageNumbers is None or 0 in pageNumbers):
                yield ResolvedPage(realFirstPages[0], 1,
                                   PageProcessingType.FrontInsideCoverBackground,
                                   True, False, number)

            page = _frontInsideCoverPage(fotobook)
            if page is None:
                logging.error(f'Failed to locate initial emptypage when processing page {number}')
                continue
            if pageNumbers is None or 1 in pageNumbers:
                yield ResolvedPage(page, 1, PageProcessingType.FrontInsideCover,
                                   True, lastPage, number)
            continue

        if AlbumInfo.isAlbumProduct(productStyle) and lastPage:
            # The final ordinary page and the back inside cover are two
            # distinct rendering operations in the same position in the MCF.
            if pageNumbers is None or number in pageNumbers:
                yield ResolvedPage(getPageElementForPageNumber(fotobook, number), number,
                                   PageProcessingType.RegularPage, isOddPage(number),
                                   True, number, finish_page=False)

            page = _backInsideCoverPage(fotobook)
            if page is None:
                logging.error(f'Failed to locate final emptypage when processing last page {number}')
                continue
            backInsideCoverNumber = number + 1
            if pageNumbers is None or backInsideCoverNumber in pageNumbers:
                yield ResolvedPage(page, backInsideCoverNumber,
                                   PageProcessingType.BackInsideCover,
                                   isOddPage(backInsideCoverNumber), True, number)
            continue

        if pageNumbers is not None and number not in pageNumbers:
            continue
        yield ResolvedPage(getPageElementForPageNumber(fotobook, number), number,
                           PageProcessingType.RegularPage, isOddPage(number),
                           lastPage, number)
