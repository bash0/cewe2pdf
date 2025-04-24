from lxml import etree
import reportlab.lib.colors
import reportlab.lib.enums
import reportlab.lib.styles
from reportlab.lib.styles import ParagraphStyle

mcf2rl = reportlab.lib.pagesizes.mm/10 # == 72/254, converts from mcf (unit=0.1mm) to reportlab (unit=inch/72)

# <pagenumbering bgcolor="#00000000" fontbold="0" fontfamily="Crafty Girls" fontitalics="0" fontsize="12" format="0" margin="52" position="4" textcolor="#ff000000" textstring="Page %" verticalMargin="53">
#     <outline width="1"/>
# </pagenumbering>


class PageNumberingInfo:
    def __init__(self, pageNumberElement):
        """
        Constructor that initializes the page numbering info from the given lxml element.
        """
        # Extract relevant attributes or sub-elements from lxml_element
        self.position = int(pageNumberElement.get('position','1'))
        self.format = int(pageNumberElement.get('format','0'))
        self.horizontalMargin = int(pageNumberElement.get('margin','50')) * mcf2rl # * 0.1 mm
        self.verticalMargin = int(pageNumberElement.get('verticalMargin','50')) * mcf2rl # * 0.1 mm
        self.fontfamily = pageNumberElement.get('fontfamily','Liberation Sans')
        self.fontsize = int(pageNumberElement.get('fontsize','12'))
        self.fontbold = int(pageNumberElement.get('fontbold','0'))
        self.fontitalics = int(pageNumberElement.get('fontitalics','0'))
        self.textstring = pageNumberElement.get('textstring','%')
        self.textcolor = pageNumberElement.get('textcolor','#ff000000')
        self.bgcolor = pageNumberElement.get('bgcolor','#00000000')
        self.paragraphStyle = ParagraphStyle(None, None,
            alignment=reportlab.lib.enums.TA_CENTER,
            fontSize=self.fontsize,
            fontName=self.fontfamily,
            leading=self.fontsize,
            borderPadding=0,
            borderWidth=0,
            leftIndent=0,
            rightIndent=0,
            # backColor=backgroundColor, # text bg not used since ColorFrame colours the whole bg
            textColor=self.textcolor)





    def display_page_number(self, current_page):
        """
        Generate the formatted page number for the given page.
        :param current_page: Current page number.
        :return: Formatted page number as a string.
        """
        if self.format == "roman":
            return self.prefix + self.to_roman(current_page)
        elif self.format == "arabic":
            return self.prefix + str(current_page)
        else:
            return self.prefix + str(current_page)

    @staticmethod
    def to_roman(num):
        """
        Convert an integer to a Roman numeral.
        :param num: Integer to convert.
        :return: Roman numeral as a string.
        """
        roman_numerals = {
            1: "I", 4: "IV", 5: "V", 9: "IX",
            10: "X", 40: "XL", 50: "L", 90: "XC",
            100: "C", 400: "CD", 500: "D", 900: "CM", 1000: "M"
        }
        result = ""
        for value, numeral in sorted(roman_numerals.items(), reverse=True):
            while num >= value:
                result += numeral
                num -= value
        return result

# Example usage:
# xml_data = '<PageNumbering startingNumber="1" format="roman" prefix="Page "/>'
# lxml_element = etree.fromstring(xml_data)

# page_numbering = PageNumberingInfo(lxml_element)
# print(page_numbering.display_page_number(5))  # Output: "Page V"

