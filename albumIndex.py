import logging
import re
# pylint: disable=no-member
import cv2 # the no_member warning is a false positive, cv2 is imported correctly and used in the code
import pymupdf
import numpy as np
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from PIL import Image

from configUtils import getConfigurationBool, getConfigurationFloat, getConfigurationInt

class AlbumIndex(): # pylint: disable=too-many-instance-attributes

    def __init__(self, configSection):
        self.indexEntries = {}
        if configSection is None:
            self.indexing = False
            return
        self.indexing = getConfigurationBool(configSection, "indexing", "False")
        self.indexEntryDefs = [] # font names and sizes used to recognise index terms
        lines = configSection.get('indexEntryFonts', '').splitlines()  # newline separated list
        indexDefs = filter(lambda bg: (len(bg) != 0), lines)
        for indexDef in indexDefs:
            members = indexDef.split(",")
            if len(members) == 2:
                font = members[0].strip()
                size = int(members[1].strip())
                self.indexEntryDefs.append((font, size))

        self.indexFont = configSection.get("indexFont", "Helvetica").strip()
        self.indexFontSize = getConfigurationInt(configSection, "indexFontSize", 12, 10)
        self.lineSpacing = getConfigurationFloat(configSection, "lineSpacing", 1.15, 1.1)
        self.pageWidth = getConfigurationInt(configSection, "pageWidth", 210, 100)
        self.pageHeight = getConfigurationInt(configSection, "pageHeight", 291, 100) # A4 is 297. 291 is the size of the paper in a 30x30 album
        self.indexMarkerRegex = configSection.get("indexMarkerRegex", "Contents").strip()
        # The margins here are for the placement of the index image on the index page
        mm2pt = 72/25.4
        self.mergeTopMarginPt = getConfigurationInt(configSection, "topMargin", 10, 0) * mm2pt
        self.mergeBottomMarginPt = getConfigurationInt(configSection, "bottomMargin", 10, 0) * mm2pt
        self.mergeLeftMarginPt = getConfigurationInt(configSection, "leftMargin", 10, 0) * mm2pt
        self.mergeRightMarginPt = getConfigurationInt(configSection, "rightMargin", 10, 0) * mm2pt
        # The margins on the generated index pdf are rarely configured since we currently
        # delete it after we have generated the png from it
        self.pdfTopMarginMm = getConfigurationInt(configSection, "pdfTopMargin", 1, 0)
        self.pdfBottomMarginMm = getConfigurationInt(configSection, "pdfBottomMargin", 1, 0)
        self.pdfLeftMarginMm = getConfigurationInt(configSection, "pdfLeftMargin", 1, 0)
        self.pdfRightMarginMm = getConfigurationInt(configSection, "pdfRightMargin", 1, 0)
        # which files do we want to keep
        self.deleteIndexPdf = getConfigurationBool(configSection, "deleteIndexPdf", "True")
        self.deleteIndexPng = getConfigurationBool(configSection, "deleteIndexPng", "False")

    def CheckForIndexEntry(self, font, fontsize):
        if not self.indexing:
            return False
        for indexEntry in self.indexEntryDefs:
            if font == indexEntry[0] and fontsize == indexEntry[1]:
                return True
        return False

    def AddIndexEntry(self, pageNumber, text):
        if not self.indexing:
            return
        if pageNumber in self.indexEntries:
            self.indexEntries[pageNumber].append(text)
        else:
            self.indexEntries[pageNumber] = [text]

    def ShowIndex(self):
        for page, entries in self.indexEntries.items():
            for text in entries:
                print(f"{text} ... {page}")

    def GenerateIndexPage(self, pdf):
        if not self.indexing:
            return
        logging.info("Generating index page")
        page_width = self.pageWidth * mm
        page_height = self.pageHeight * mm
        pdf.setPageSize((page_width, page_height))

        top_margin = self.pdfTopMarginMm * mm
        bottom_margin = self.pdfBottomMarginMm * mm
        left_margin = self.pdfLeftMarginMm * mm
        right_margin = page_width - self.pdfRightMarginMm * mm
        line_spacing = self.indexFontSize * self.lineSpacing # Adjust as needed for readability

        def pageSetup():
            pdf.setFont(self.indexFont, self.indexFontSize)  # Set a readable font
            ypos = page_height - top_margin - self.indexFontSize  # Start from top margin
            return ypos

        y_position = pageSetup()

        for page, texts in sorted(self.indexEntries.items()):
            for text in texts:
                text_width = pdf.stringWidth(text, self.indexFont, self.indexFontSize)
                page_number_str = f"{page}"
                page_number_width = pdf.stringWidth(page_number_str, self.indexFont, self.indexFontSize)

                dot_spacing = right_margin - (left_margin + text_width + page_number_width)
                dots = '.' * int(dot_spacing / pdf.stringWidth('.', self.indexFont, self.indexFontSize))

                pdf.drawString(left_margin, y_position, text)
                pdf.drawString(left_margin + text_width, y_position, dots)
                pdf.drawString(right_margin - page_number_width, y_position, page_number_str)

                y_position -= line_spacing
                if y_position < bottom_margin:
                    pdf.showPage()
                    y_position = pageSetup()

        pdf.showPage()

    def SaveIndexPdf(self, outputFileName, albumTitle, pagesize):
        if not self.indexing:
            return None
        # Initialize a pdf canvas for the index
        indexFileName = AlbumIndex.GetIndexName(outputFileName)
        pdf = canvas.Canvas(indexFileName, pagesize=pagesize)
        pdf.setTitle(albumTitle + " index")
        # Create the pdf page containing the index
        self.GenerateIndexPage(pdf)
        try:
            pdf.save()
        except Exception as ex: # pylint: disable=broad-exception-caught
            logging.error(f'Could not save the index output file: {str(ex)}')
        return indexFileName

    def SaveIndexPngs(self, indexPdfFileName):
        """Render every generated index-PDF page as an image for album merging."""
        if not self.indexing:
            return []
        doc = pymupdf.open(indexPdfFileName)
        pageCount = len(doc)
        indexPngFileNames = []
        for pageNumber in range(pageCount):
            image = AlbumIndex._convert_to_opencv(doc.load_page(pageNumber), dpi=150)
            finalImage = AlbumIndex._make_white_transparent(image)
            if pageCount == 1:
                # Preserve the historic name for ordinary one-page indexes.
                indexPngFileName = indexPdfFileName.replace('.pdf', '.png')
            else:
                indexPngFileName = indexPdfFileName.replace('.pdf',
                                                             f'.{pageNumber + 1}.png')
            cv2.imwrite(indexPngFileName, finalImage, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            indexPngFileNames.append(indexPngFileName)
        doc.close()
        return indexPngFileNames

    def SaveIndexPng(self, indexPdfFileName):
        """Backward-compatible single-image accessor for external callers."""
        indexPngFileNames = self.SaveIndexPngs(indexPdfFileName)
        return indexPngFileNames[0] if indexPngFileNames else None

    @staticmethod
    def _make_white_transparent(image):
        # Convert to BGRA (with alpha channel)
        image_rgba = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
        # Set white pixels to transparent
        white_mask = (image_rgba[:, :, :3] == [255, 255, 255]).all(axis=2)
        image_rgba[white_mask, 3] = 0  # Set alpha channel to 0 for transparent pixels
        return image_rgba

    @staticmethod
    def _convert_to_opencv(pdf_page, dpi=72):
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

    @staticmethod
    def _crop_transparent_borders(image_rgba):
        # Find all pixels where alpha > 0 (i.e. not fully transparent)
        alpha_channel = image_rgba[:, :, 3]
        non_transparent_coords = np.argwhere(alpha_channel > 0)
        if non_transparent_coords.size == 0:
            return image_rgba  # Image is fully transparent
        # Bounding box
        top_left = non_transparent_coords.min(axis=0)
        bottom_right = non_transparent_coords.max(axis=0) + 1  # add 1 for inclusive slicing
        # Crop
        cropped_image = image_rgba[top_left[0]:bottom_right[0], top_left[1]:bottom_right[1]]
        return cropped_image

    def _findIndexMarkerPages(self, albumDoc):
        """Return every album page carrying the configured invisible index marker."""
        pattern = re.compile(self.indexMarkerRegex)
        markerPages = []
        for page in albumDoc:
            for block in page.get_text('blocks'):
                text = block[4]
                if any(pattern.search(line.strip()) for line in text.split('\n')):
                    markerPages.append(page)
                    break
        return markerPages

    @staticmethod
    def _removePreviouslyMergedIndexImage(albumDoc, page, indexImageWidth):
        """Remove an earlier likely-index image so repeat conversions remain idempotent."""
        removedImage = False
        for imageInfo in page.get_images(full=True):
            xref = imageInfo[0]
            extractedImage = albumDoc.extract_image(xref)
            if extractedImage['ext'].lower() != 'png':
                continue
            imageArray = np.frombuffer(extractedImage['image'], dtype=np.uint8)
            image = cv2.imdecode(imageArray, cv2.IMREAD_COLOR)
            whiteRatio = np.sum((image == [255, 255, 255]).all(axis=2)) / image.shape[0] / image.shape[1]
            # CEWE loses the alpha channel when an index image is reimported,
            # leaving its once-transparent region white. Matching width covers
            # the less common case where it has subsequently been cropped.
            if whiteRatio > 0.8 or imageInfo[2] == indexImageWidth:
                page.delete_image(xref)
                removedImage = True
        return removedImage

    def _mergeIndexImage(self, albumDoc, page, indexPngFileName): # pylint: disable=too-many-locals
        """Scale one transparent index image into one already-reserved album page."""
        indexImage = Image.open(indexPngFileName)
        indexWidthPx, indexHeightPx = indexImage.size
        dpiX, dpiY = indexImage.info.get('dpi', (300, 300))
        indexImage.close()
        indexWidthPt = indexWidthPx * (72 / dpiX)
        indexHeightPt = indexHeightPx * (72 / dpiY)
        self._removePreviouslyMergedIndexImage(albumDoc, page, indexWidthPx)

        pageWidth, pageHeight = page.rect.width, page.rect.height
        maxWidthPt = pageWidth - self.mergeLeftMarginPt - self.mergeRightMarginPt
        maxHeightPt = pageHeight - self.mergeBottomMarginPt - self.mergeTopMarginPt
        scaleFactor = min(maxWidthPt / indexWidthPt, maxHeightPt / indexHeightPt)
        scaledWidthPt = indexWidthPt * scaleFactor
        scaledHeightPt = indexHeightPt * scaleFactor
        x0 = (pageWidth - scaledWidthPt) / 2
        y0 = self.mergeTopMarginPt
        rect = pymupdf.Rect(x0, y0, x0 + scaledWidthPt, y0 + scaledHeightPt)
        page.insert_image(rect, filename=indexPngFileName, overlay=True)

    def MergeAlbumAndIndexPngs(self, albumPdfFileName, indexPngFileNames):
        """Merge every index image onto the matching reserved album page in order."""
        if not self.indexing:
            return
        if not indexPngFileNames:
            return
        albumDoc = pymupdf.open(albumPdfFileName)
        markerPages = self._findIndexMarkerPages(albumDoc)
        if not markerPages:
            logging.warning('Cannot find an album page matching the index marker regex.')
            albumDoc.close()
            return
        if len(markerPages) < len(indexPngFileNames):
            logging.error(
                f'Generated {len(indexPngFileNames)} index pages but found only '
                f'{len(markerPages)} reserved index pages matching {self.indexMarkerRegex!r}.')
        if len(markerPages) > len(indexPngFileNames):
            logging.warning(
                f'Found {len(markerPages)} reserved index pages but generated only '
                f'{len(indexPngFileNames)} index pages; unused marker pages are unchanged.')
        for page, indexPngFileName in zip(markerPages, indexPngFileNames):
            self._mergeIndexImage(albumDoc, page, indexPngFileName)

        albumDoc.save(albumPdfFileName, incremental=True, encryption=0)
        albumDoc.close()

    def MergeAlbumAndIndexPng(self, albumPdfFileName, indexPngFileName):
        """Backward-compatible single-page merge API."""
        self.MergeAlbumAndIndexPngs(albumPdfFileName, [indexPngFileName])

    @staticmethod
    def MergeAlbumAndIndexPdf(albumPdfFileName, pagenr, indexPdfFileName):
        # Load the album PDF
        albumDoc = pymupdf.open(albumPdfFileName)
        indexDoc = pymupdf.open(indexPdfFileName)
        # Replace page in album, 0 indexed
        albumDoc.delete_page(pagenr)  # Remove the old page
        albumDoc.insert_pdf(indexDoc, from_page=0, to_page=0, start_at=pagenr)
        # Save the modified album PDF
        # to original ... doc.save("input.pdf", incremental=False, encryption=pymupdf.PDF_ENCRYPT_NONE)
        albumDoc.save(albumPdfFileName.replace(".pdf",".final.pdf"))
        albumDoc.close()

    @staticmethod
    def GetIndexName(outputFileName):
        return outputFileName.replace(".pdf",".idx.pdf")

    @staticmethod
    def AppendIndexText(existing_text, new_text):
        return existing_text + " " + new_text if existing_text else new_text
