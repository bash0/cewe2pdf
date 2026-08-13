"""Page selection and page-level rendering flow for CEWE books."""

import logging
from math import floor
from typing import Callable

# A failed page must be logged and the remainder of the album rendered.
# pylint: disable=broad-exception-caught

from backgrounds import processBackground
from conversionState import ConversionState
from ceweInfo import AlbumInfo
from pageNumbering import addPageNumber
from pageTypes import PageProcessingType
from renderContext import RenderContext


def getPageElementForPageNumber(fotobook, pageNumber):
    """Return the MCF page element containing the requested normal page."""
    return fotobook.find(f"./page[@pagenr='{floor(2 * (pageNumber / 2))}']")


def parseInputPage(fotobook, ceweFolder, mcfBaseFolder, backgroundLocations, imageDirectory, pdf,
                   page, pageNumber, pageCount, pageType, productStyle, oddPage,
                   state: ConversionState, availableFonts, lastPage,
                   context: RenderContext, processElements: Callable):
    """Set up one output page, draw its background, then delegate its areas."""
    logging.info(f"Side {pageNumber} ({pageType}): parsing pagenr {page.get('pagenr')} of {pageCount}")

    bundleSize = page.find("./bundlesize")
    if bundleSize is not None:
        pageWidth = float(bundleSize.get('width'))
        pageHeight = float(bundleSize.get('height'))
        if AlbumInfo.isAlbumSingleSide(productStyle):
            pageWidth = pageWidth / 2
    else:
        # Assume A4 page size.
        pageWidth = 2100
        pageHeight = 2970
    pdf.setPageSize((context.mcf_to_reportlab * pageWidth,
                     context.mcf_to_reportlab * pageHeight))

    # The designElementIDs preceding the background element match it only for
    # an original, unfiltered stock background.
    backgroundTags = page.findall('background')
    processBackground(backgroundTags, state, ceweFolder,
                      backgroundLocations, productStyle, pageType, pdf,
                      pageHeight, pageWidth, context)

    if AlbumInfo.isAlbumSingleSide(productStyle) and \
            pageType == PageProcessingType.FrontInsideCoverBackground:
        # The front inside cover is processed again to draw its elements after
        # this initial background-only pass.
        return

    # All elements for each page pair are defined on the even page element.
    processElements(availableFonts, fotobook, imageDirectory, productStyle,
                    mcfBaseFolder, oddPage, page, pageNumber, pageType, pdf,
                    pageHeight, pageWidth, lastPage, context)


def processPages(fotobook, mcfBaseFolder, imageDirectory, productStyle, pdf, pageCount,  # noqa: C901
                 pageNumbers, ceweFolder, availableFonts, backgroundLocations,
                 state: ConversionState, context: RenderContext,
                 pageNumberingInfo, processElements: Callable):
    """Render the requested album pages, including covers and inside covers."""

    def isBackCover(number):
        return number == (pageCount - 1)

    def isLastPage(number):
        return number == (pageCount - 2)

    def isOddPage(number):
        return (number % 2) == 1

    for number in range(pageCount):
        try:
            pageType = PageProcessingType.Undetermined
            lastPage = isLastPage(number)

            # Normal MCF pages run from pagenr 1 to 26. A default album also
            # contains five pagenr 0 elements for covers and inside covers.
            if AlbumInfo.isAlbumProduct(productStyle) and (number == 0 or isBackCover(number)):
                fullCoverPages = [candidate for candidate in
                    fotobook.findall("./page[@pagenr='0'][@type='FULLCOVER']")
                    + fotobook.findall("./page[@pagenr='0'][@type='fullcover']")
                    if candidate.find("./area") is not None]
                if len(fullCoverPages) == 1:
                    page = fullCoverPages[0]
                    oddPage = number == 0
                    pageType = PageProcessingType.Cover
                    pageNumber = number
                    # In double-page layout, the last page is already the
                    # left side of the cover, so do not render it again.
                    if AlbumInfo.isAlbumDoubleSide(productStyle) and isBackCover(pageNumber):
                        page = None
                else:
                    logging.warning("Cannot locate a cover page, is this really an album?")
                    page = None

            elif AlbumInfo.isAlbumProduct(productStyle) and number == 1:
                pageNumber = 1
                oddPage = True
                # The empty page with areas represents the first inside cover.
                pages = [candidate for candidate in
                    fotobook.findall("./page[@pagenr='0'][@type='EMPTY']")
                    + fotobook.findall("./page[@pagenr='0'][@type='emptypage']")
                    if candidate.find("./area") is not None or
                    candidate.find("./background[@alignment='1']") is not None]
                if len(pages) >= 1:
                    page = pages[0]
                else:
                    logging.error(f'Failed to locate initial emptypage when processing page {number}')
                    page = None

                realFirstPages = fotobook.findall("./page[@pagenr='1'][@type='normalpage']")
                if len(realFirstPages) > 0 and (pageNumbers is None or 0 in pageNumbers):
                    # Draw the background first so it cannot obscure other elements.
                    pageType = PageProcessingType.FrontInsideCoverBackground
                    lastPage = False
                    parseInputPage(fotobook, ceweFolder, mcfBaseFolder, backgroundLocations,
                                   imageDirectory, pdf, realFirstPages[0], pageNumber, pageCount,
                                   pageType, productStyle, oddPage, state,
                                   availableFonts, lastPage, context, processElements)
                pageType = PageProcessingType.FrontInsideCover

            elif AlbumInfo.isAlbumProduct(productStyle) and lastPage:
                pageNumber = number
                if pageNumbers is None or pageNumber in pageNumbers:
                    oddPage = isOddPage(pageNumber)
                    page = getPageElementForPageNumber(fotobook, number)
                    pageType = PageProcessingType.RegularPage
                    parseInputPage(fotobook, ceweFolder, mcfBaseFolder, backgroundLocations,
                                   imageDirectory, pdf, page, pageNumber, pageCount, pageType,
                                   productStyle, oddPage, state,
                                   availableFonts, lastPage, context, processElements)
                    addPageNumber(pageNumberingInfo, pdf, pageNumber,
                                  productStyle, oddPage, context)

                # A page 0 without areas defines the back inside-cover background.
                pages = [candidate for candidate in
                    fotobook.findall("./page[@pagenr='0'][@type='EMPTY']")
                    + fotobook.findall("./page[@pagenr='0'][@type='emptypage']")
                    if candidate.find("./area") is None or
                    candidate.find("./background[@alignment='3']") is not None]
                if len(pages) >= 1:
                    page = pages[0]
                    pageNumber = number + 1
                    oddPage = isOddPage(pageNumber)
                    pageType = PageProcessingType.BackInsideCover
                else:
                    logging.error(f'Failed to locate final emptypage when processing last page {number}')
                    page = None

            else:
                pageNumber = number
                oddPage = isOddPage(pageNumber)
                page = getPageElementForPageNumber(fotobook, number)
                pageType = PageProcessingType.RegularPage

            if pageNumbers is not None and pageNumber not in pageNumbers:
                continue

            if page is not None:
                if pageType == PageProcessingType.Undetermined:
                    logging.error(f'Unable to deduce page type for page {pageNumber}')
                    continue
                parseInputPage(fotobook, ceweFolder, mcfBaseFolder, backgroundLocations,
                               imageDirectory, pdf, page, pageNumber, pageCount, pageType,
                               productStyle, oddPage, state,
                               availableFonts, lastPage, context, processElements)

                if AlbumInfo.isAlbumProduct(productStyle) and pageType in [
                        PageProcessingType.FrontInsideCover,
                        PageProcessingType.RegularPage]:
                    addPageNumber(pageNumberingInfo, pdf, pageNumber,
                                  productStyle, oddPage, context)

                if not AlbumInfo.isAlbumProduct(productStyle):
                    pdf.showPage()
                elif AlbumInfo.isAlbumSingleSide(productStyle):
                    pdf.showPage()
                elif oddPage or (pageType == PageProcessingType.Cover and not isBackCover(number)):
                    pdf.showPage()

        except Exception as pageException:
            logging.exception("Exception")
            logging.error(f'error on page {number}: {pageException.args[0]}')
