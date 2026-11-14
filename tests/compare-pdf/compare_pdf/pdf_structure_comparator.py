
import logging
import pymupdf

from itertools import combinations
from typing import Mapping


class PDFStructureComparator:
    """Compare the structural contents of multiple open PDF documents.

    The documents are owned by the caller. This class does not open or
    close them.

    Geometry comparisons use a tolerance of 0.01 PDF points.
    """

    GEOMETRY_TOLERANCE = 0.01

    def __init__(self, pdf_documents, pdf_paths, logger=None):
        self.pdf_documents = pdf_documents
        self.pdf_paths = pdf_paths
        self.logger = logger or logging.getLogger('cewe2pdf.test')

    def compare(self) -> bool:
        """Run all currently implemented structural comparisons."""

        result = True

        result = self.compare_page_counts() and result
        result = self.compare_bookmarks() and result
        result = self.compare_internal_links() and result
        result = self.compare_external_links() and result

        return result

    def compare_page_counts(self) -> bool:
        """Check that all PDFs contain the same number of pages."""

        result = True

        for i, j in combinations(range(len(self.pdf_documents)), 2):
            count1 = self.pdf_documents[i].page_count
            count2 = self.pdf_documents[j].page_count

            if count1 != count2:
                result = False
                self.logger.warning(
                    "PDF page count differs: %s has %s pages; "
                    "%s has %s pages",
                    self.pdf_paths[i], count1,
                    self.pdf_paths[j], count2)
            else:
                self.logger.info(
                    "PDF page counts agree (%s pages): %s and %s",
                    count1, self.pdf_paths[i], self.pdf_paths[j])

        return result

    def compare_bookmarks(self) -> bool:
        """Compare bookmark titles, hierarchy and destinations."""

        result = True

        # Retrieve each table of contents just once.
        try:
            toc_list = [
                doc.get_toc(simple=False)
                for doc in self.pdf_documents
            ]
        except Exception:
            self.logger.exception("Unable to retrieve PDF bookmarks")
            return False

        for i, j in combinations(range(len(toc_list)), 2):
            toc1 = toc_list[i]
            toc2 = toc_list[j]

            path1 = self.pdf_paths[i]
            path2 = self.pdf_paths[j]

            if len(toc1) != len(toc2):
                result = False
                self.logger.warning(
                    "Bookmark count differs: %s has %s bookmarks; "
                    "%s has %s bookmarks",
                    path1, len(toc1), path2, len(toc2))

            for index in range(max(len(toc1), len(toc2))):
                if index >= len(toc1):
                    result = False
                    self.logger.warning(
                        "Extra bookmark in %s at position %s: %s",
                        path2, index + 1, toc2[index][1])
                    continue

                if index >= len(toc2):
                    result = False
                    self.logger.warning(
                        "Missing bookmark in %s at position %s: %s",
                        path2, index + 1, toc1[index][1])
                    continue

                bookmark1 = self._normalise_bookmark(toc1[index])
                bookmark2 = self._normalise_bookmark(toc2[index])

                differences = self._compare_bookmark(
                    bookmark1, bookmark2)

                if differences:
                    result = False
                    self.logger.warning(
                        "Bookmark %s differs between %s and %s: %s",
                        index + 1, path1, path2,
                        "; ".join(differences))

        if result:
            self.logger.info("PDF bookmarks agree across all files")

        return result

    
    def compare_internal_links(self):
        """Compare internal links in every pair of PDF documents."""
        result = True

        for (doc1, path1), (doc2, path2) in combinations(
            zip(self.pdf_documents, self.pdf_paths), 2
        ):
            links1 = self._get_internal_links(doc1)
            links2 = self._get_internal_links(doc2)

            # for page_number, (page_links1, page_links2) in enumerate(
            #     zip(links1, links2), start=1
            # ):
            for page_index in range(max(len(links1), len(links2))):
                page_links1 = links1[page_index] if page_index < len(links1) else []
                page_links2 = links2[page_index] if page_index < len(links2) else []
                page_number = page_index + 1

                unmatched = list(page_links2)

                for link1 in page_links1:
                    match = next(
                        (
                            index
                            for index, link2 in enumerate(unmatched)
                            if self._internal_links_equal(link1, link2)
                        ),
                        None,
                    )

                    if match is None:
                        self.logger.warning(
                            "Internal link missing or different on page %d "
                            "in %s: %s",
                            page_number,
                            path2,
                            link1,
                        )
                        result = False
                    else:
                        unmatched.pop(match)

                for link2 in unmatched:
                    self.logger.warning(
                        "Extra internal link on page %d in %s: %s",
                        page_number,
                        path2,
                        link2,
                    )
                    result = False

        if result:
            self.logger.info("PDF internal links agree across all files")

        return result

    def _get_internal_links(self, document):
        """Return normalised internal links, grouped by source page."""
        pages = []

        for page_number in range(document.page_count):
            page = document.load_page(page_number)
            page_links = []

            for link in page.get_links():
                if link.get("kind") != pymupdf.LINK_GOTO:
                    continue

                rect = link.get("from")
                destination = link.get("to")

                page_links.append({
                    "page": link.get("page"),
                    "rect": tuple(rect) if rect is not None else None,
                    "position": (
                        tuple(destination)
                        if destination is not None
                        else None
                    ),
                    "zoom": link.get("zoom"),
                })

            pages.append(page_links)

        return pages

    def _internal_links_equal(self, link1, link2):
        """Return True when two normalised internal links are equivalent."""
        if link1["page"] != link2["page"]:
            return False

        if not self._coordinates_equal(link1["rect"], link2["rect"]):
            return False

        if not self._coordinates_equal(
            link1["position"], link2["position"]
        ):
            return False

        return self._numbers_equal(link1["zoom"], link2["zoom"])

    def _coordinates_equal(self, values1, values2):
        """Compare coordinate sequences using the geometry tolerance."""
        if values1 is None or values2 is None:
            return values1 is None and values2 is None

        if len(values1) != len(values2):
            return False

        return all(
            abs(a - b) <= self.GEOMETRY_TOLERANCE
            for a, b in zip(values1, values2)
        )

    def _numbers_equal(self, value1, value2):
        """Compare optional numeric values."""
        if value1 is None or value2 is None:
            return value1 is None and value2 is None

        return abs(value1 - value2) <= self.GEOMETRY_TOLERANCE


    @staticmethod
    def _normalise_bookmark(entry):
        """Convert a PyMuPDF TOC entry into comparable components.

        With simple=False, PyMuPDF returns:
            [level, title, page, destination_dictionary]
        """

        level, title, page = entry[:3]
        destination = entry[3] if len(entry) > 3 else None

        return {
            'level': level,
            'title': title,
            'page': page,
            'position': PDFStructureComparator._get_position(destination),
            'zoom': (
                destination.get('zoom')
                if isinstance(destination, Mapping)
                else None
            ),
        }

    @staticmethod
    def _get_position(destination):
        """Extract the destination point as an (x, y) tuple."""

        if not isinstance(destination, Mapping):
            return None

        point = destination.get('to')

        if point is None:
            return None

        try:
            if hasattr(point, 'x') and hasattr(point, 'y'):
                return float(point.x), float(point.y)

            return float(point[0]), float(point[1])

        except (TypeError, ValueError, IndexError, KeyError):
            return None

    def _compare_bookmark(self, first, second):
        """Return a list describing differences between two bookmarks."""

        differences = []

        for field, description in (
            ('title', 'title'),
            ('level', 'hierarchy level'),
            ('page', 'destination page'),
        ):
            if first[field] != second[field]:
                differences.append(
                    f"{description}: {first[field]!r} vs {second[field]!r}")

        first_position = first['position']
        second_position = second['position']

        if first_position is None or second_position is None:
            if first_position != second_position:
                differences.append(
                    f"destination position: "
                    f"{first_position!r} vs {second_position!r}")
        else:
            for axis, value1, value2 in zip(
                    ('x', 'y'), first_position, second_position):
                if abs(value1 - value2) > self.GEOMETRY_TOLERANCE:
                    differences.append(
                        f"destination {axis}: {value1:.4f} vs {value2:.4f}")

        zoom1 = first['zoom']
        zoom2 = second['zoom']

        if zoom1 is None or zoom2 is None:
            if zoom1 != zoom2:
                differences.append(
                    f"zoom: {zoom1!r} vs {zoom2!r}")
        elif abs(float(zoom1) - float(zoom2)) > self.GEOMETRY_TOLERANCE:
            differences.append(
                f"zoom: {zoom1!r} vs {zoom2!r}")

        return differences

    
    def compare_external_links(self):
        """Compare external URI links in every pair of PDF documents."""
        result = True

        for (doc1, path1), (doc2, path2) in combinations(
            zip(self.pdf_documents, self.pdf_paths), 2
        ):
            links1 = self._get_external_links(doc1)
            links2 = self._get_external_links(doc2)

            # for page_number, (page_links1, page_links2) in enumerate(
            #     zip(links1, links2), start=1
            # ):
            for page_index in range(max(len(links1), len(links2))):
                page_links1 = links1[page_index] if page_index < len(links1) else []
                page_links2 = links2[page_index] if page_index < len(links2) else []
                page_number = page_index + 1

                unmatched = list(page_links2)

                for link1 in page_links1:
                    match = next(
                        (
                            index
                            for index, link2 in enumerate(unmatched)
                            if self._external_links_equal(link1, link2)
                        ),
                        None,
                    )

                    if match is None:
                        self.logger.warning(
                            "External link missing or different on page %d "
                            "in %s: %s",
                            page_number,
                            path2,
                            link1,
                        )
                        result = False
                    else:
                        unmatched.pop(match)

                for link2 in unmatched:
                    self.logger.warning(
                        "Extra external link on page %d in %s: %s",
                        page_number,
                        path2,
                        link2,
                    )
                    result = False

        if result:
            self.logger.info("PDF external links agree across all files")

        return result

    def _get_external_links(self, document):
        """Return normalised external URI links, grouped by source page."""
        pages = []

        for page_number in range(document.page_count):
            page = document.load_page(page_number)
            page_links = []

            for link in page.get_links():
                if link.get("kind") != pymupdf.LINK_URI:
                    continue

                rect = link.get("from")

                page_links.append({
                    "kind": link.get("kind"),
                    "rect": tuple(rect) if rect is not None else None,
                    "uri": link.get("uri"),
                })

            pages.append(page_links)

        return pages

    def _external_links_equal(self, link1, link2):
        """Return True when two external URI links are equivalent."""
        if link1["kind"] != link2["kind"]:
            return False

        if link1["uri"] != link2["uri"]:
            return False

        return self._coordinates_equal(link1["rect"], link2["rect"])
