"""Create PDF-reader labels from CEWE's logical output-page structure."""

from dataclasses import dataclass

from ceweInfo import ProductInfo
from pageTypes import PageProcessingType


@dataclass(frozen=True)
class PdfPageLabel:
    """One label for a physical output PDF page.

    ``style='D'`` is a conventional decimal PDF page label. An empty style
    makes ``prefix`` the complete label, which is useful for covers and PDF
    spreads such as ``2-3``.
    """

    prefix: str = ''
    style: str = ''
    first_page_number: int = 1


def labelForRenderedPage(resolvedPage, productStyle):
    """Return the reader-facing label for one page about to be emitted."""
    if (resolvedPage.page_type == PageProcessingType.Cover
            or resolvedPage.page_number == 0):
        return PdfPageLabel(prefix='Cover')

    if not ProductInfo.isAlbumProduct(productStyle):
        return _numberedLabel(resolvedPage.page_number)

    if (ProductInfo.isAlbumSingleSide(productStyle)
            or resolvedPage.page_type == PageProcessingType.BackInsideCover
            or resolvedPage.page_number == 1):
        return _numberedLabel(resolvedPage.source_number)
    return PdfPageLabel(prefix=(
        f'{resolvedPage.page_number - 1}-{resolvedPage.page_number}'))


def pageLabelDefinitions(pageLabels):
    """Return the compact PyMuPDF page-label dictionary sequence.

    A decimal run needs one definition only. A gap caused by ``--pages`` or
    an explicitly labelled cover/spread begins a new run.
    """
    definitions = []
    previousLabel = None
    for outputPageNumber, label in enumerate(pageLabels):
        if not _continuesPreviousLabel(label, previousLabel):
            definitions.append({
                'startpage': outputPageNumber,
                'prefix': label.prefix,
                'style': label.style,
                'firstpagenum': label.first_page_number,
            })
        previousLabel = label
    return definitions


def _numberedLabel(pageNumber):
    return PdfPageLabel(style='D', first_page_number=pageNumber)


def _continuesPreviousLabel(label, previousLabel):
    """Whether a PDF reader can infer this label from the preceding range."""
    return (previousLabel is not None
            and label.style == 'D'
            and label.prefix == previousLabel.prefix
            and previousLabel.style == 'D'
            and label.first_page_number == previousLabel.first_page_number + 1)
