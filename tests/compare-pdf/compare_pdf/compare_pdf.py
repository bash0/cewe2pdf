# copied and modified from https://github.com/Formartha/compare-pdf

import logging
import argparse
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

import fitz  # PyMuPDF library
import cv2
import numpy as np

class ShowDiffsStyle(Enum):
    Nothing = 1
    SideBySide = 2
    DiffImage = 3

class ComparePDF:
    def __init__(self, pdf_paths, showdiffs):
        self.pdf_paths = pdf_paths
        self.pdf_documents = [fitz.open(path) for path in pdf_paths]
        self.showdiffs = showdiffs
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
        else:
            # self.logger.info(f"Some images on Page {page_num} are not equal (Page {page_num} compared across files):")
            for i in range(len(images)):
                for j in range(i + 1, len(images)):
                    if not np.array_equal(images[i], images[j]):
                        self.logger.warning(
                            f"Page {page_num} image from {self.pdf_paths[i]} differs from image from {self.pdf_paths[j]}")
                    # Optionally show each page for debugging purposes, style determined by a command line option
                    if self.showdiffs == ShowDiffsStyle.SideBySide:
                        # The following lines display the two images side by side
                        imagePair = np.hstack((images[i], images[j]))
                        self._display_image(imagePair, page_num, 0)
                    elif self.showdiffs == ShowDiffsStyle.DiffImage:
                        # The following lines display the difference image, with the black pixels set to white
                        diffImage = cv2.absdiff(images[i], images[j])
                        diffImage[np.all(diffImage == (0, 0, 0), axis=-1)] = (255,255,255)
                        self._display_image(diffImage, page_num, 0)
        return equal


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
