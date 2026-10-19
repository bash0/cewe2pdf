# copied and modified from https://github.com/Formartha/compare-pdf

import logging
import argparse
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

import pymupdf
import cv2
import numpy as np

class ShowDiffsStyle(Enum):
    Nothing = 1
    SideBySide = 2
    DiffImage = 3


@dataclass(frozen=True)
class PageTolerance:
    """A narrowly scoped allowance for expected rasterisation differences.

    ``max_channel_difference`` is the largest permitted absolute difference
    in any one RGB colour channel of any pixel (0--255).

    ``max_combined_rgb_difference`` is the largest permitted sum of the
    absolute red, green, and blue differences for any one pixel (0--765).
    A page is accepted only when all three limits are met.  Pages without an
    explicit tolerance remain exact pixel comparisons.
    """

    max_different_pixels: int
    max_channel_difference: int
    max_combined_rgb_difference: int
    reason: str

    def __post_init__(self):
        for name, value in (
                ('max_different_pixels', self.max_different_pixels),
                ('max_channel_difference', self.max_channel_difference),
                ('max_combined_rgb_difference', self.max_combined_rgb_difference)):
            if value < 0:
                raise ValueError(f'{name} must not be negative')
        if not self.reason:
            raise ValueError('A page tolerance must explain why it is needed')


class ComparePDF:
    def __init__(self, pdf_paths, showdiffs, page_tolerances: Mapping[int, PageTolerance] | None = None):
        """Compare PDF files rendered at a fixed resolution.

        ``page_tolerances`` is an optional mapping of one-based page numbers
        to narrowly scoped :class:`PageTolerance` instances.  It is intended
        for known platform-dependent rasterisation differences; exact pixel
        comparison remains the default.
        """
        # PyMuPDF accepts ``pathlib.Path`` objects, but the diagnostic strings
        # below are joined. Normalise once at this public boundary so callers
        # can use either strings or Path objects consistently.
        self.pdf_paths = [os.fspath(path) for path in pdf_paths]
        self.pdf_documents = [pymupdf.open(path) for path in self.pdf_paths]
        self.showdiffs = showdiffs
        self.page_tolerances = dict(page_tolerances or {})
        if any(page_number < 1 for page_number in self.page_tolerances):
            raise ValueError('Page tolerance page numbers are one-based')
        self.logger = logging.getLogger('cewe2pdf.test')

    def __del__(self):
        # Destructor to clean up resources
        self.cleanup()

    def cleanup(self):
        for doc in self.pdf_documents:
            doc.close()
        self.pdf_documents = []
        self.pdf_paths = []

    def compare(self)-> bool:
        if len(self.pdf_paths) < 2:
            self.logger.error("At least two PDF files are required for comparison")
            return False

        self.logger.info(f"Comparing PDF files: {', '.join(self.pdf_paths)}")

        compareAllResult = True # until proven otherwise
        images_per_page = None
        with ThreadPoolExecutor() as executor:
            images_per_page = executor.map(self._get_page_images, range(min(doc.page_count for doc in self.pdf_documents)))

        for page_num, images in enumerate(images_per_page, start=1):
            compareOneResult = self._compare_images(images, page_num)
            compareAllResult = compareAllResult and compareOneResult

        self.logger.info("PDF comparison completed")
        return compareAllResult


    def _get_page_images(self, page_num):
        return [self._convert_to_opencv(doc.load_page(page_num), dpi=150) for doc in self.pdf_documents]


    def _convert_to_opencv(self, pdf_page, dpi=72):
        pix = pdf_page.get_pixmap(alpha=False, dpi=dpi)
        img = np.frombuffer(pix.samples, np.uint8).reshape((pix.height, pix.width, pix.n))

        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)  # Convert RGBA to BGR
        elif pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)  # Convert RGB to BGR
        elif pix.n == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)  # Convert grayscale to BGR
        elif pix.n == 2:
            # Handle indexed color image
            indexed_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)  # Convert indexed color to BGR
            img = indexed_img

        return img


    def _display_image(self, image, page_num, mswait):
        windowName = f'Page {page_num}'
        cv2.namedWindow(windowName,cv2.WINDOW_NORMAL)
        sizeFactor = 0.4 # width and height adjustment to sensible window size for shown image
        windowWidth = int(image.shape[1]*sizeFactor)
        windowHeight = int(image.shape[0]*sizeFactor)
        cv2.resizeWindow(windowName, windowWidth, windowHeight)
        cv2.imshow(windowName, image)
        cv2.waitKey(mswait)  # set to 0 to actually see the images
        cv2.destroyAllWindows()


    def _compare_images(self, images, page_num) -> bool:
        equal = all(np.array_equal(images[0], img) for img in images)
        if equal:
            self.logger.info(f"All images on Page {page_num} are equal")
            return True

        comparison_result = True
        tolerance = self.page_tolerances.get(page_num)

        # self.logger.info(f"Some images on Page {page_num} are not equal (Page {page_num} compared across files):")
        for i in range(len(images)):
            for j in range(i + 1, len(images)):
                if np.array_equal(images[i], images[j]):
                    continue

                diff_image = cv2.absdiff(images[i], images[j])
                different_pixel_mask = np.any(diff_image != 0, axis=2)
                different_pixels = np.count_nonzero(different_pixel_mask)
                total_pixels = different_pixel_mask.size
                different_percent = 100 * different_pixels / total_pixels
                max_channel_difference = int(np.max(diff_image))
                max_combined_rgb_difference = int(np.max(
                    np.sum(diff_image, axis=2, dtype=np.uint16)))
                diagnostics = (
                    f"{different_pixels:,} px, {different_percent:.4f}%; "
                    f"maximum per-channel difference {max_channel_difference}; "
                    f"maximum combined RGB difference {max_combined_rgb_difference}")

                within_tolerance = tolerance is not None and (
                    different_pixels <= tolerance.max_different_pixels
                    and max_channel_difference <= tolerance.max_channel_difference
                    and max_combined_rgb_difference <= tolerance.max_combined_rgb_difference)
                if within_tolerance:
                    self.logger.info(
                        "Page %s image difference accepted within tolerance "
                        "(%s). Reason: %s",
                        page_num, diagnostics, tolerance.reason)
                else:
                    comparison_result = False
                    tolerance_note = ''
                    if tolerance is not None:
                        tolerance_note = f"; exceeds page tolerance: {tolerance.reason}"
                    self.logger.warning(
                        "Page %s image in %s differs (%s) from image %s%s",
                        page_num, self.pdf_paths[i], diagnostics,
                        self.pdf_paths[j], tolerance_note)

                # Optionally show each page for debugging purposes, style determined by a command line option
                if self.showdiffs == ShowDiffsStyle.SideBySide:
                    # The following lines display the two images side by side
                    image_pair = np.hstack((images[i], images[j]))
                    self._display_image(image_pair, page_num, 0)
                elif self.showdiffs == ShowDiffsStyle.DiffImage:
                    # The following lines display the difference image, with the black pixels set to white
                    diff_image[np.all(diff_image == (0, 0, 0), axis=-1)] = (255, 255, 255)
                    self._display_image(diff_image, page_num, 0)
        return comparison_result


def main():
    parser = argparse.ArgumentParser(description='Compare PDF files visually')
    parser.add_argument('--pdf', action='append', required=True, help='Path to the PDF file')
    parser.add_argument('--showdiffs', choices=['nothing', 'diffimage', 'sidebyside'], action='store', required=False,
                        help='Show different pages in windows as they are found, eiher diffimage or sidebyside')
    args = parser.parse_args()
    if not args.showdiffs:
        showdiffs = ShowDiffsStyle.Nothing
    else:
        if args.showdiffs == 'diffimage':
            showdiffs = ShowDiffsStyle.DiffImage
        elif args.showdiffs == 'sidebyside':
            showdiffs = ShowDiffsStyle.SideBySide
        else:
            showdiffs = ShowDiffsStyle.Nothing

    compare = ComparePDF(args.pdf,showdiffs)
    result = compare.compare()
    return result


if __name__ == "__main__":
    finalResult = 0 if main() else -1
    print(f"Final result was {finalResult}")
