from reportlab.lib.units import mm

from configUtils import getConfigurationBool

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

        # Here are some values which we might want to configure in a later edition
        indexFont = "Helvetica"
        indexFontSize = 12
        lineSpacing = 1.15
        topMarginMm = 10
        bottomMarginMm = 10
        leftMarginMm = 10
        rightMarginMm = 15

        # pdfPageSize = pdf._pagesize # internal to reportlab, could make it a method parameter
        # pageWidth = pdfPageSize[0]
        # pageHeight = pdfPageSize[1]
        # Reset the page size so that the index would print nicely on e.g. A4
        pageWidth = 210 * mm
        pageHeight = 291 * mm # A4 is 297. 291 is the size of the paper in a 30x30 album
        pdf.setPageSize((pageWidth, pageHeight))

        top_margin = topMarginMm * mm
        bottom_margin = bottomMarginMm * mm
        left_margin = leftMarginMm * mm
        right_margin = pageWidth - rightMarginMm * mm
        line_spacing = indexFontSize * lineSpacing # Adjust as needed for readability

        def pageSetup():
            pdf.setFont(indexFont, indexFontSize)  # Set a readable font
            ypos = pageHeight - top_margin  # Start from top margin
            return ypos

        y_position = pageSetup()

        for page, texts in sorted(self.indexEntries.items()):
            for text in texts:
                text_width = pdf.stringWidth(text, indexFont, indexFontSize)
                page_number_str = f"{page}"
                page_number_width = pdf.stringWidth(page_number_str, indexFont, indexFontSize)

                dot_spacing = right_margin - (left_margin + text_width + page_number_width)
                dots = '.' * int(dot_spacing / pdf.stringWidth('.', indexFont, indexFontSize))

                pdf.drawString(left_margin, y_position, text)
                pdf.drawString(left_margin + text_width, y_position, dots)
                pdf.drawString(right_margin - page_number_width, y_position, page_number_str)

                y_position -= line_spacing
                if y_position < top_margin:
                    pdf.showPage()
                    y_position = pageSetup()

        pdf.showPage()

    @staticmethod
    def AppendIndexText(existing_text, new_text):
        return existing_text + " " + new_text if existing_text else new_text
