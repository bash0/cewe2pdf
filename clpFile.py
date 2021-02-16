# SPDX-License-Identifier:LGPL-3.0-only or GPL-3.0-only

# Copyright (c) 2020 by BarchSteel

from pathlib import Path
import os
import cairosvg
import PIL
from PIL import ImageOps
from PIL.ExifTags import TAGS
from io import BytesIO
import re

class ClpFile(object):
    def __init__(self, clpFileName:str = ""):
        """Constructor with file name will open and read .CLP file"""
        self.svgData: bytes = bytes()   # the byte representation of the SVG file
        self.pngMemFile: BytesIO = BytesIO(bytes())     # this can be used to access the buffer like a file.

        if clpFileName:
            self.readClp(clpFileName)

    def readClp(self, fileName) -> None:
        """Read a .CLP file and convert it to a .SVG file.

         reads the data into the internal buffer as SVG

         Remarks: The current implementation using immutable strings may not be best.
           But it should work for typical cliparts with a size of less then a few megabytes."""

        inFilePath = Path(fileName)
        # open and read the whole file to memory
        fileClp = open(inFilePath, "rt")
        contents = fileClp.read()
        fileClp.close()

        # check the header
        if contents[0] != 'a':
            raise Exception("A .cpl file should start with character 'a', but instead it was: {} ({})".format(contents[0], hex(ord(contents[0]))))
        # start after the header and remove all invalid characters
        invalidChars = 'ghijklmnopqrstuvwxyz'
        hexData = contents[1:].translate({ord(i): None for i in invalidChars})

        # the string is hexadecimal representation of the real data. Let's convert it back.
        svgData = bytes.fromhex(hexData)
        self.svgData = svgData

    def saveToSVG(self, outfileName):
        """save internal SVG data to a file"""
        outFile = open(outfileName, "wb")
        outFile.write(self.svgData)
        outFile.close()

    def convertToPngInBuffer(self, width:int = None, height:int = None, alpha:int = 128):
        """convert the SVG to a PNG file, but only in memory"""

        # create a byte buffer that can be used like a file and use it as the output of svg2png.
        scaledImage = self.rasterSvgData(width, height)

        if scaledImage.mode == "RGB":
            # create a mask the same size as the original. For all pixels which are
            # non zero ("not used") set the mask value to the required transparency
            # L = 8-bit gray-scale
            # Important: .convert('L') should not be used on RGBA images -> very bad quality. Not supported.
            alphamask = scaledImage.copy().convert('L').resize(scaledImage.size)
            pixels = alphamask.load()
            for i in range(alphamask.size[0]): # for every pixel:
                for j in range(alphamask.size[1]):
                    if (pixels[i, j] != 0):
                        pixels[i, j] = alpha
            scaledImage.putalpha(alphamask)

        scaledImage.save(self.pngMemFile, 'png')
        self.pngMemFile.seek(0)
        return self

    def rasterSvgData(self, width:int, height:int):

        # We are using cairosvg, but this does not allow to scale the output image to the dimensions that we like.
        # we need to do a two-pass convertion, to get the desired result
        # 1. Do the first conversion and see what the output size is
        # 2. calculate the scaling in x-, and y-direction that is needed
        # 3. use the maxium of these x-, and y-scaling and do a aspect-ratio-preserving scaling of the image
        #    convert the image again from svg to png with this max. scale factor
        # 4. do a raster-image scaling to skew the image to the final dimension.
        #    This should only scale in x- or y-direction, as the other direction should alread be the desired one.

        # create a byte buffer that can be used like a file and use it as the output of svg2png.
        tmpMemFile = BytesIO()
        # Step 1.
        cairosvg.svg2png(bytestring=self.svgData, write_to=tmpMemFile)
        tmpMemFile.seek(0)
        tempImage = PIL.Image.open(tmpMemFile)
        origWidth = tempImage.width
        origHeight = tempImage.height
        # Step 2.
        scale_x = width/origWidth
        scale_y = height/origHeight
        # Step 3.
        scaleMax = max(scale_x, scale_y)
        tmpMemFile = BytesIO()
        cairosvg.svg2png(bytestring=self.svgData, write_to=tmpMemFile, scale=scaleMax)
        # Step 4.
        tmpMemFile.seek(0)
        tempImage = PIL.Image.open(tmpMemFile)
        scaledImage = tempImage.resize((width, height))
        return scaledImage

    # def convertMaskToPngInBuffer(self, width:int = None, height:int = None):
    #     """convert a loaded mask (.clp, .SVG) to a in-memory PNG file
    #         Use this for the passepartout frames.
    #      """

    #     #create a byte buffer that can be used like a file and use it as the output of svg2png.
    #     maskImgPng:PIL.Image = self.rasterSvgData(width, height)

    #     maskImgPng.save(self.pngMemFile, 'png')
    #     self.pngMemFile.seek(0)
    #     return self

    def applyAsAlphaMaskToFoto(self, photo:PIL.Image):
        """" Use the currently loaded mask clipart to create a alpha mask on the input image."""
        # create the PNG as RBGA in internal buffer
        # create a byte buffer that can be used like a file and use it as the output of svg2png.
        maskImgPng:PIL.Image = self.rasterSvgData(photo.width, photo.height)

        # get the alpha channel
        #  if the .svg is fully filled by the mask, then only a black rectangle with RGA (=no background!) is returned.
        #  if the mask does not fully fill the mask, then an RGBA image is returned. In this case, use the alpha value directly.
        if maskImgPng.mode == "RGBA":
            alphaChannel = maskImgPng.getchannel("A")
        elif maskImgPng.mode == "RGB":
            # convert image to gray-scale and use that as alpha channel.
            # we need to invert, otherwise black whould be transparent.
            # normally the whole image is a black rectangle
            alphaChannel = maskImgPng.convert('L')
            alphaChannel = PIL.ImageOps.invert(alphaChannel)

        # apply it the input photo. They must have the same dimensions. But that is ensured by rasterSvgData
        if (photo.mode != "RGB") or (photo.mode != "RGBA"):
            photo = photo.convert("RGBA")
        photo.putalpha(alphaChannel)

        return photo

    def savePNGfromBufferToFile(self, fileName) -> None:
        """ write the internal PNG buffer to a file """
        outFile = open(fileName,"wb")
        outFile.write(self.pngMemFile.read())
        outFile.close()
        self.pngMemFile.seek(0) # reset file pointer back to the start for other function calls

    def loadFromSVG(self, inputFileSVG:str):
        # read SVG file into memory
        svgFile = open(inputFileSVG,"rb") # input file should be UTF-8 encoded
        self.svgData = svgFile.read()
        svgFile.close()
        return self

    def replaceColors(self, colorReplacementList):
        """ Replace colors in the clipart

        This does a simple text replacement of color strings in the clipart.

        colorReplacementList: list of tuples
            first element of tuple: original color
            second element: new color

        The color must be a string, and it must be exactly as it appears in the .SVG file as text.
        """

        # the colors are in the form of: style="fill:#112233", or style="opacity:0.40;fill:#112233"
        # Maybe a regex would be better, as not to replace arbitrary text

        for curReplacement in colorReplacementList:
            # print (curReplacement)
            oldColorString = 'fill:'+curReplacement[0]
            newColorString = 'fill:'+curReplacement[1]
            # a general replace would look like this:
            #     re.sub("(style=\".*?)(fill:\#[0-9a-fA-F]+)(.*?\")", r"\1"+XXX+r"\3", self.svgData)
            self.svgData = re.sub("(style=\".*?)("+oldColorString+")(.*?\")", r"\1"+newColorString+r"\3", self.svgData.decode()).encode(encoding="utf-8")
            # Old, simple, but buggy code: self.svgData = self.svgData.replace(oldColorString.encode(encoding="utf-8"),newColorString.encode(encoding="utf-8") )

        return self

    @staticmethod
    def convertSVGtoCLP(inputFileSVG:str, outputFileCLP: str = '') -> None:
        """Converts a SVG file to a CLP file.
           If outputFileCLP is left empty, a file a the same base name but .clp extension is created."""
        inFilePath = Path(inputFileSVG)
        if not outputFileCLP: # check for None and empty string
            outputFileCLP = Path(inFilePath.parent).joinpath(inFilePath.stem + ".clp")

        # read SVG into memory
        svgFile = open(inFilePath,"rt")
        contents = svgFile.read()
        svgFile.close()

        # convert input string to its byte representation using utf-8 encoding.
        # and convert that to a hex string,
        tempCLPdata = contents.encode('utf-8').hex()

        # write CLP file by just adding the header
        outFile = open(outputFileCLP,"wb")
        outFile.write('a'.encode('ASCII'))
        outFile.write(tempCLPdata.encode('utf-8'))
        outFile.close()


# if __name__ == '__main__':
    # only executed when this file is run directly.

    # myClp = ClpFile(r"C:\Program Files\dm\dm-Fotowelt\Resources\photofun\decorations\summerholiday_frames\12195-DECO-SILVER-GD\12195-DECO-SILVER-GD-mask.clp")
    # outImg = myClp.applyAsAlphaMaskToFoto(PIL.Image.open(r"tests\unittest_fotobook_mcf-Dateien\img.png"))
    # outImg.save(r"test.png")

    # clpFile.convertSVGtoCLP("circle.svg")

    # myClp = clpFile()
    # myClp.readClp("circle.clp")
    # myClp.convertToPngInBuffer(200,30)
    # myClp.savePNGfromBufferToFile("test.png")

    # # create pdf
    # from reportlab.pdfgen import canvas
    # import reportlab.lib.pagesizes
    # from reportlab.lib.utils import ImageReader
    # from reportlab.pdfbase import pdfmetrics
    # from reportlab.lib import colors
    # pagesize = reportlab.lib.pagesizes.A4
    # pdf = canvas.Canvas("test" + '.pdf', pagesize=pagesize)
    # pdf.setFillColor(colors.gray)
    # pdf.rect(20,20, 200, 200, fill=1)
    # pdf.drawImage(ImageReader(myClp.pngMemFile), 72, 72, width= 20 * 1/25.4*72, height=2 * 1/25.4*72)
    # pdf.showPage()
    # pdf.save()
