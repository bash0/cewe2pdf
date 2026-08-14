"""Page selection and page-level rendering flow for CEWE books."""

import logging
from typing import Callable

# A failed page must be logged and the remainder of the album rendered.
# pylint: disable=broad-exception-caught

from backgrounds import processBackground
from conversionState import ConversionState
from ceweInfo import AlbumInfo
from cewePageResolver import ResolvedPage, resolvePages
from pageNumbering import addPageNumber
from pageTypes import PageProcessingType
from renderContext import RenderContext


def parseInputPage(fotobook, mcfBaseFolder, backgroundLocations, imageDirectory, pdf,
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
    processBackground(backgroundTags, state,
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


def processPages(fotobook, mcfBaseFolder, imageDirectory, productStyle, pdf, pageCount,
                 pageNumbers, availableFonts, backgroundLocations,
                 state: ConversionState, context: RenderContext,
                 pageNumberingInfo, processElements: Callable):
    """Render the requested album pages, including covers and inside covers."""

    for resolvedPage in resolvePages(fotobook, productStyle, pageCount, pageNumbers):
        try:
            _renderResolvedPage(resolvedPage, fotobook, mcfBaseFolder,
                                backgroundLocations, imageDirectory, productStyle, pdf,
                                pageCount, state, availableFonts, context,
                                pageNumberingInfo, processElements)

        except Exception as pageException:
            logging.exception("Exception")
            logging.error(f'error on page {resolvedPage.source_number}: {pageException.args[0]}')


def _renderResolvedPage(resolvedPage: ResolvedPage, fotobook, mcfBaseFolder,
                        backgroundLocations, imageDirectory, productStyle, pdf, pageCount,
                        state: ConversionState, availableFonts, context: RenderContext,
                        pageNumberingInfo, processElements: Callable):
    """Render one page which has already been classified by CEWE rules."""
    parseInputPage(fotobook, mcfBaseFolder, backgroundLocations,
                   imageDirectory, pdf, resolvedPage.element, resolvedPage.page_number,
                   pageCount, resolvedPage.page_type, productStyle,
                   resolvedPage.odd_page, state, availableFonts,
                   resolvedPage.last_page, context, processElements)

    if resolvedPage.page_type == PageProcessingType.FrontInsideCoverBackground:
        # This is a preparatory background draw for the first inside cover.
        # It shares the canvas with the following FrontInsideCover request and
        # must not add a page number or call showPage().
        return

    if not resolvedPage.finish_page:
        # CEWE places the final ordinary page and its back inside cover on the
        # same PDF canvas.  The following resolved page will finish it.
        addPageNumber(pageNumberingInfo, pdf, resolvedPage.page_number,
                      productStyle, resolvedPage.odd_page, context)
        return

    if AlbumInfo.isAlbumProduct(productStyle) and resolvedPage.page_type in [
            PageProcessingType.FrontInsideCover, PageProcessingType.RegularPage]:
        addPageNumber(pageNumberingInfo, pdf, resolvedPage.page_number,
                      productStyle, resolvedPage.odd_page, context)

    if not AlbumInfo.isAlbumProduct(productStyle):
        pdf.showPage()
    elif AlbumInfo.isAlbumSingleSide(productStyle):
        pdf.showPage()
    elif resolvedPage.odd_page or (
            resolvedPage.page_type == PageProcessingType.Cover and
            resolvedPage.source_number != pageCount - 1):
        pdf.showPage()
