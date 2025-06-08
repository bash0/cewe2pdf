import fitz  # PyMuPDF
import cv2
import numpy as np
import logging
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from PIL import Image

from configUtils import getConfigurationBool, getConfigurationFloat, getConfigurationInt

class Index():

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
        self.topMarginMm = getConfigurationInt(configSection, "topMargin", 10, 10)
        self.bottomMarginMm = getConfigurationInt(configSection, "bottomMargin", 10, 10)
        self.leftMarginMm = getConfigurationInt(configSection, "leftMargin", 10, 10)
        self.rightMarginMm = getConfigurationInt(configSection, "rightMargin", 15, 10)
        self.pageWidth = getConfigurationInt(configSection, "pageWidth", 210, 100)
        self.pageHeight = getConfigurationInt(configSection, "pageHeight", 291, 100)
            # A4 is 297. 291 is the size of the paper in a 30x30 album

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
        for page in self.indexEntries:
            for text in self.indexEntries[page]:
                print(f"{text} ... {page}")

    def GenerateIndexPage(self, pdf):
        if not self.indexing:
            return
        logging.info(f"Generating index page")
        page_width = self.pageWidth * mm
        page_height = self.pageHeight * mm
        pdf.setPageSize((page_width, page_height))

        top_margin = self.topMarginMm * mm
        bottom_margin = self.bottomMarginMm * mm
        left_margin = self.leftMarginMm * mm
        right_margin = page_width - self.rightMarginMm * mm
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
        # Initialize a pdf canvas for the index
        indexFileName = Index.GetIndexName(outputFileName)
        pdf = canvas.Canvas(indexFileName, pagesize=pagesize)
        pdf.setTitle(albumTitle + " index")
        # Create the pdf page containing the index
        self.GenerateIndexPage(pdf)
        try:
            pdf.save()
        except Exception as ex:
            logging.error(f'Could not save the index output file: {str(ex)}')
        return indexFileName

    @staticmethod
    def SaveIndexPng(indexPdfFileName):
        doc = fitz.open(indexPdfFileName)
        image = Index._convert_to_opencv(doc.load_page(0), dpi=150)
        transparent_image = Index.make_white_transparent(image)
        cropped_image = Index.crop_transparent_borders(transparent_image)
        indexPngFileName = indexPdfFileName.replace(".pdf",".png")
        # this should write with standard 300 dpi
        cv2.imwrite(indexPngFileName, cropped_image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        # another possible technique ... convert NumPy array to Pillow Image
        #   image = Image.fromarray(cropped_image)
        #   image.save(indexPngFileName, dpi=(300, 300))
        return indexPngFileName

    @staticmethod
    def make_white_transparent(image):
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
    def crop_transparent_borders(image_rgba):
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

    @staticmethod
    def MergeAlbumAndIndexPng(albumPdfFileName, pagenr, indexPngFileName):
        # Load the index png
        indexImage = Image.open(indexPngFileName)
        idx_width_px, idx_height_px = indexImage.size  # Get dimensions
        # Get DPI (default to 300 if not specified)
        dpi_x, dpi_y = indexImage.info.get("dpi", (300, 300))
        # Convert image size to PDF points
        idx_width_pt = idx_width_px * (72 / dpi_x)
        idx_height_pt = idx_height_px * (72 / dpi_y)

        # Load the album PDF
        albumDoc = fitz.open(albumPdfFileName)
        page = albumDoc[pagenr]
        page_width, page_height = page.rect.width, page.rect.height

        # Define margins in terms of page size
        margin_x = page_width * 0.1
        margin_y = page_height * 0.05

        # Max available size for the image (without exceeding margins)
        max_width_pt = page_width - 2 * margin_x
        max_height_pt = page_height - 2 * margin_y

        # Scale the image proportionally to fit within the available space
        scale_factor = min(max_width_pt / idx_width_pt, max_height_pt / idx_height_pt)
        scaled_width_pt = idx_width_pt * scale_factor
        scaled_height_pt = idx_height_pt * scale_factor

        # Compute position
        x0 = (page_width - scaled_width_pt) / 2 # centered horizontally
        y0 = margin_y # centering vertically: y0 = (page_height - scaled_height_pt) / 2
        rect = fitz.Rect(x0, y0, x0 + scaled_width_pt, y0 + scaled_height_pt)

        # Insert the scaled and centered image into the PDF
        page.insert_image(rect, filename=indexPngFileName, overlay=True)

        albumDoc.save(albumPdfFileName, incremental=True, encryption=0) # overwriting the original
        albumDoc.close()

    @staticmethod
    def MergeAlbumAndIndexPdf(albumPdfFileName, pagenr, indexPdfFileName):
        # Load the album PDF
        albumDoc = fitz.open(albumPdfFileName)
        indexDoc = fitz.open(indexPdfFileName)
        # Replace page in album, 0 indexed
        albumDoc.delete_page(pagenr)  # Remove the old page
        albumDoc.insert_pdf(indexDoc, from_page=0, to_page=0, start_at=pagenr)
        # Save the modified album PDF
        # to original ... doc.save("input.pdf", incremental=False, encryption=fitz.PDF_ENCRYPT_NONE)
        albumDoc.save(albumPdfFileName.replace(".pdf",".final.pdf"))
        albumDoc.close()

    @staticmethod
    def GetIndexName(outputFileName):
        return outputFileName.replace(".pdf",".idx.pdf")

    @staticmethod
    def AppendIndexText(existing_text, new_text):
        return existing_text + " " + new_text if existing_text else new_text
