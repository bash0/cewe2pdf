import logging
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
        if self.position not in [1,2,4,5]:
            logging.error(f"Unrecognised pagenumbering position value {self.position}, reset to 1")
            self.position = 1
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


    @staticmethod
    def toRoman(num, lowerCase=False)->str:
        """
        Convert an integer to a Roman numeral.
        """
        roman_numerals = {
            1: "I", 4: "IV", 5: "V", 9: "IX",
            10: "X", 40: "XL", 50: "L", 90: "XC",
            100: "C", 400: "CD", 500: "D", 900: "CM", 1000: "M"
        }
        if num <= 0:
            raise ValueError("Number must be greater than zero")
        result = ""
        for value, numeral in sorted(roman_numerals.items(), reverse=True):
            while num >= value:
                result += numeral
                num -= value
        if lowerCase:
            result = result.lower()
        return result

    @staticmethod
    def toAlphabetic(num, lowerCase=False)->str:
        """
        Convert a number to an alphabetic sequence (A-Z, AA-ZZ, etc.).
        """
        if num <= 0:
            raise ValueError("Number must be greater than zero")
        result = ""
        while num > 0:
            num -= 1  # Adjust for 1-based indexing
            result = chr(num % 26 + ord('A')) + result
            num //= 26
        if lowerCase:
            result = result.lower()
        return result

    @staticmethod
    def toBinary(num):
        """
        Convert a number to its binary representation.
        """
        if num < 0:
            raise ValueError("Number must be non-negative")
        return bin(num)[2:]  # Removes the '0b' prefix

    @staticmethod
    def toHexadecimal(num, width=2):
        """
        Convert a number to its hexadecimal representation.
        """
        if num < 0:
            raise ValueError("Number must be non-negative")
        return hex(num)[2:].upper().zfill(width)  # Removes the '0x' prefix, converts to uppercase and pads
