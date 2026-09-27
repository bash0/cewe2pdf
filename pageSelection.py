"""Interpret user requests for content pages and the outer cover."""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PageSelection:
    """Selected editable page numbers, with an optional outer-cover request.

    Page zero is deliberately not a page number here.  It was an old command
    line shorthand for the front cover, which could not express the matching
    back cover and obscured the distinction between CEWE records and visible
    pages.
    """

    page_numbers: frozenset[int] = frozenset()
    include_cover: bool = False

    @classmethod
    def from_legacy_numbers(cls, page_numbers: Iterable[int]):
        """Adapt the public API's historic integer-list argument.

        Existing callers which used zero for a cover gain the more useful new
        behaviour: both outer covers for a single-page album PDF, or the
        complete outer-cover spread for a double-page PDF.
        """
        content_pages = set()
        include_cover = False
        for number in page_numbers:
            if not isinstance(number, int):
                raise ValueError(f'Page number {number!r} is not an integer.')
            if number == 0:
                include_cover = True
            elif number > 0:
                content_pages.add(number)
            else:
                raise ValueError(f'Page number {number} must be positive.')
        return cls(frozenset(content_pages), include_cover)

    @classmethod
    def from_value(cls, selection):
        """Return a selection from the public API's accepted input forms."""
        if selection is None or isinstance(selection, cls):
            return selection
        return cls.from_legacy_numbers(selection)

    def describe(self):
        """Return a compact, human-readable representation of this selection."""
        items = ['cover'] if self.include_cover else []
        pageNumbers = sorted(self.page_numbers)
        rangeStart = rangeEnd = None
        for pageNumber in pageNumbers:
            if rangeStart is None:
                rangeStart = rangeEnd = pageNumber
            elif pageNumber == rangeEnd + 1:
                rangeEnd = pageNumber
            else:
                items.append(_describePageRange(rangeStart, rangeEnd))
                rangeStart = rangeEnd = pageNumber
        if rangeStart is not None:
            items.append(_describePageRange(rangeStart, rangeEnd))
        return ', '.join(items) or '(none)'


def _describePageRange(firstPage, lastPage):
    return str(firstPage) if firstPage == lastPage else f'{firstPage}-{lastPage}'


def parse_page_selection(expression: str) -> PageSelection:
    """Parse ``cover,1-12,15`` command-line syntax into a selection."""
    content_pages = set()
    include_cover = False
    expressions = expression.split(',')
    if not expression.strip() or any(not item.strip() for item in expressions):
        raise ValueError('Page selection must contain comma-separated page numbers, ranges, or cover.')

    for item in expressions:
        item = item.strip()
        if item.casefold() == 'cover':
            include_cover = True
            continue

        if '-' in item:
            range_parts = item.split('-')
            if len(range_parts) != 2:
                raise ValueError(f'Invalid page range: {item}')
            first_text, last_text = (part.strip() for part in range_parts)
            if not first_text.isdigit() or not last_text.isdigit():
                raise ValueError(f'Invalid page range: {item}')
            first_page, last_page = int(first_text), int(last_text)
            if first_page <= 0 or last_page <= 0:
                raise ValueError('Page numbers start at 1; use cover for the outer cover.')
            if last_page < first_page:
                raise ValueError(f'Invalid page range: {item}')
            content_pages.update(range(first_page, last_page + 1))
            continue

        if not item.isdigit():
            raise ValueError(f'Invalid page selection: {item}')
        page_number = int(item)
        if page_number <= 0:
            raise ValueError('Page numbers start at 1; use cover for the outer cover.')
        content_pages.add(page_number)

    return PageSelection(frozenset(content_pages), include_cover)
