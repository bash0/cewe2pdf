import logging
from enum import Enum
import reportlab.lib.colors
import reportlab.lib.enums
import reportlab.lib.styles
from reportlab.lib.styles import ParagraphStyle
from ceweInfo import ProductStyle
from colorUtils import ReorderColorBytesMcf2Rl

mcf2rl = reportlab.lib.pagesizes.mm/10 # == 72/254, converts from mcf (unit=0.1mm) to reportlab (unit=inch/72)

# <pagenumbering bgcolor="#00000000" fontbold="0" fontfamily="Crafty Girls" fontitalics="0" fontsize="12" format="0"
#     margin="52" position="4" textcolor="#ff000000" textstring="Page %" verticalMargin="53">
#     <outline width="1"/>
# </pagenumbering>


class PageNumberPosition(Enum):
    LEFT = "left"
    RIGHT = "right"
    ORIGINAL = "original"

    @staticmethod
    def ToEnum(value: str):
        try:
            return PageNumberPosition(value)
        except ValueError:
            logging.error(f"'{value}' is not a valid PageNumberPosition")
            return PageNumberPosition.ORIGINAL


class PageNumberFormat(Enum):
    ARABIC = "0"
    ROMANLC = "1"
    ROMANUC = "2"
    ALPHALC = "3"
    ALPHAUC = "4"
    BINARY = "5"
    HEX = "6"

    @staticmethod
    def ToEnum(value: str):
        try:
            return PageNumberFormat(value)
        except ValueError:
            logging.error(f"'{value}' is not a valid PageNumberFormat")
            return PageNumberFormat.ARABIC


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
        self.format = PageNumberFormat.ToEnum(pageNumberElement.get('format','0'))
        self.horizontalMargin = int(pageNumberElement.get('margin','50')) * mcf2rl # * 0.1 mm
        self.verticalMargin = int(pageNumberElement.get('verticalMargin','50')) * mcf2rl # * 0.1 mm
        self.fontfamily = pageNumberElement.get('fontfamily','Liberation Sans')
        self.fontsize = int(pageNumberElement.get('fontsize','12'))
        self.fontbold = int(pageNumberElement.get('fontbold','0'))
        self.fontitalics = int(pageNumberElement.get('fontitalics','0'))
        self.textstring = pageNumberElement.get('textstring','%')
        self.textcolor = ReorderColorBytesMcf2Rl(pageNumberElement.get('textcolor','#ff000000'))
        self.bgcolor = ReorderColorBytesMcf2Rl(pageNumberElement.get('bgcolor','#00000000'))
        self.paragraphStyle = ParagraphStyle(None, None,
            alignment=reportlab.lib.enums.TA_CENTER,
            fontSize=self.fontsize,
            fontName=self.fontfamily,
            leading=self.fontsize,
            borderPadding=0,
            borderWidth=0,
            leftIndent=0,
            rightIndent=0,
            # backColor=self.bgcolor, # text bg not used since ColorFrame colours the whole bg
            textColor=self.textcolor)

    def getNumberString(self, pageNumber):
        if self.format == PageNumberFormat.ROMANLC:
            numberString = self.toRoman(pageNumber, lowerCase=True)
        elif self.format == PageNumberFormat.ROMANUC:
            numberString = self.toRoman(pageNumber)
        elif self.format == PageNumberFormat.ALPHALC:
            numberString = self.toAlphabetic(pageNumber, lowerCase=True)
        elif self.format == PageNumberFormat.ALPHAUC:
            numberString = self.toAlphabetic(pageNumber)
        elif self.format == PageNumberFormat.BINARY:
            numberString = self.toBinary(pageNumber)
        elif self.format == PageNumberFormat.HEX:
            numberString = self.toHexadecimal(pageNumber)
        else:
            numberString = str(pageNumber)
        return numberString

    def getNumberText(self, pageNumber) -> str:
        numberString = self.getNumberString(pageNumber)
        numberText = self.textstring.replace("%",numberString)
        return numberText

    def getParagraphString(self, pageNumber) -> str:
        numberText = self.getNumberText(pageNumber)
        boldstart = '<b>' if self.fontbold != 0 else ''
        boldend = '</b>' if self.fontbold != 0 else ''
        italicstart = '<i>' if self.fontitalics != 0 else ''
        italicend = '</i>' if self.fontitalics != 0 else ''
        paragraphstring = f'{boldstart}{italicstart}{numberText}{italicend}{boldend}'
        return paragraphstring

    def getParagraphText(self, pageNumber) -> str:
        paragraphstring = self.getParagraphString(pageNumber)
        paragraphText = f'<para>{paragraphstring}</para>'
        return paragraphText

    @staticmethod
    def toRoman(num, lowerCase=False) -> str:
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
    def toAlphabetic(num, lowerCase=False) -> str:
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


def horizontalPageNumberAdjustment(pnp, pageNumberingInfo, sideWidth, frameWidth, productStyle, oddpage):
    # We are calculating the horizontal adjustment needed within one side to achieve
    # outer edge placement. The adjustment because of the double page width for a double
    # sided album output is external to this code, as is the adjustment for centred
    # placement. That is, this code is ONLY for outer edge positioning.
    # The original outer placement is left on left pages, and right on right pages,
    # but in the case where we have converted the album to a single sided pdf (probably
    # the most usual case) then it is not unlikely that we would prefer all the pages
    # to have their outer edge number in the same place. There is a risk, of course,
    # that the repositioned number might clash with some element on the page, but that's
    # up to the user to check (and is why the default value is the original placement)

    if productStyle == ProductStyle.AlbumSingleSide:
        if pnp == PageNumberPosition.RIGHT:
            return sideWidth - pageNumberingInfo.horizontalMargin - frameWidth
        elif pnp == PageNumberPosition.LEFT:
            return pageNumberingInfo.horizontalMargin

    # all other cases drop through here to original outer edge page number position
    if oddpage:
        return sideWidth - pageNumberingInfo.horizontalMargin - frameWidth
    else:
        return pageNumberingInfo.horizontalMargin


def getPageNumberXy(pnp, pageNumberingInfo, pdf, frameWidth, frameHeight, productStyle, oddpage):
    pagesize = (pdf._pagesize[0],pdf._pagesize[1]) # pagesize in rl units
    sideHeight = pagesize[1]
    if productStyle == ProductStyle.AlbumDoubleSide:
        sideWidth = pagesize[0] / 2
        cx = sideWidth if oddpage else 0 # moving to right hand side for odd pages in double sided
    else:
        sideWidth = pagesize[0]
        cx = 0

    # finally can calculate the actual position
    if pageNumberingInfo.position == 1: # outer top
        cy = sideHeight - pageNumberingInfo.verticalMargin - frameHeight
        cx = cx + horizontalPageNumberAdjustment(pnp, pageNumberingInfo, sideWidth, frameWidth, productStyle, oddpage)
    elif pageNumberingInfo.position == 4: # outer bottom
        cy = pageNumberingInfo.verticalMargin
        cx = cx + horizontalPageNumberAdjustment(pnp, pageNumberingInfo, sideWidth, frameWidth, productStyle, oddpage)
    elif pageNumberingInfo.position == 2: # centre top
        cy = sideHeight - pageNumberingInfo.verticalMargin - frameHeight
        cx = cx + 0.5 * (sideWidth - frameWidth)
    elif pageNumberingInfo.position == 5: # centre bottom
        cy = pageNumberingInfo.verticalMargin
        cx = cx + 0.5 * (sideWidth - frameWidth)
    else:
        # can't actually happen because pageNumberingInfo checks the position
        return 0,0
    return cx,cy
