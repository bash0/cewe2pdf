import logging
from reportlab.lib.units import mm

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
        # pdfPageSize = pdf._pagesize # internal to reportlab, could make it a method parameter
        # pageWidth = pdfPageSize[0]
        # pageHeight = pdfPageSize[1]
        # Reset the page size so that the index would print nicely on e.g. A4
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

    @staticmethod
    def AppendIndexText(existing_text, new_text):
        return existing_text + " " + new_text if existing_text else new_text
