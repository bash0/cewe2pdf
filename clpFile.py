#SPDX-License-Identifier:LGPL-3.0-only or GPL-3.0-only

# Copyright (c) 2020 by BarchSteel

from pathlib import Path
import os
import cairosvg
import PIL
from PIL.ExifTags import TAGS
from io import BytesIO

class ClpFile(object):
    def __init__(self, clpFileName:str =""):
        """Constructor with file name will open and read .CLP file"""
        self.svgData : bytes = bytes()   # the byte representation of the SVG file
        self.pngMemFile: BytesIO = BytesIO(bytes())     #this can be used to access the buffer like a file.

        if (clpFileName):
            self.readClp(clpFileName)

    def readClp(self, fileName) -> None:
        """Read a .CLP file and convert it to a .SVG file.
         
         reads the data into the internal buffer as SVG
        
         Remarks: The current implementation using immutable strings may not be best.
           But it should work for typical cliparts with a size of less then a few megabytes."""

        inFilePath = Path(fileName)
        #open and read the whole file to memory
        fileClp = open(inFilePath,"rt")
        contents = fileClp.read()
        fileClp.close()
    
        #check the header
        if (contents[0] != 'a'):
            raise Exception("A .cpl file should start with character 'a', but instead it was: {} ({})".format(contents[0], hex(ord(contents[0]))))
        #start after the header and remove all invalid characters
        invalidChars ='ghijklmnopqrstuvwxyz'
        hexData = contents[1:].translate({ord(i): None for i in invalidChars})

        #the string is hexadecimal representation of the real data. Let's convert it back.
        svgData = bytes.fromhex(hexData)
        self.svgData = svgData
    
        
    def saveToSVG(self, outfileName):
        """save internal SVG data to a file"""
        outFile = open(outfileName,"wb")
        outFile.write(self.svgData)
        outFile.close()

    def convertToPngInBuffer(self, width:int = None, height:int = None):
        """convert the SVG to a PNG file, but only in memory"""

        #We are using cairosvg, but this does not allow to scale the output image to the dimensions that we like.
        #we need to do a two-pass convertion, to get the desired result
        #1. Do the first conversion and see what the output size is
        #2. calculate the scaling in x-, and y-direction that is needed
        #3. use the maxium of these x-, and y-scaling and do a aspect-ratio-preserving scaleing of the image
        #4. do a raster-image scaling to skew the image to the final dimension. 
        #   This should only scale in x- or y-direction, as the other direction should alread be the desired one.

        #create a byte buffer that can be used like a file and use it as the output of svg2png.
        tmpMemFile = BytesIO()
        cairosvg.svg2png(bytestring=self.svgData, write_to=tmpMemFile)
        tmpMemFile.seek(0)
        tempImage = PIL.Image.open(tmpMemFile)
        origWidth = tempImage.width
        origHeight = tempImage.height
        scale_x = width/origWidth
        scale_y = height/origHeight
        scaleMax = max(scale_x, scale_y)
        tmpMemFile = BytesIO()
        cairosvg.svg2png(bytestring=self.svgData, write_to=tmpMemFile, scale=scaleMax)
        tmpMemFile.seek(0)
        tempImage = PIL.Image.open(tmpMemFile)
        scaledImage = tempImage.resize((width, height))
        scaledImage.save(self.pngMemFile, 'png')
        self.pngMemFile.seek(0)
        return self

    def savePNGfromBufferToFile(self, fileName) -> None:
        """ write the internal PNG buffer to a file """
        outFile = open(fileName,"wb")
        outFile.write(self.pngMemFile.read())
        outFile.close()
        self.pngMemFile.seek(0) # reset file pointer back to the start for other function calls

    def loadFromSVG(self, inputFileSVG:str):
        #read SVG file into memory        
        svgFile = open(inputFileSVG,"rb") #input file should be UTF-8 encoded
        self.svgData = svgFile.read()
        svgFile.close()
        return self

    @staticmethod
    def convertSVGtoCLP(inputFileSVG:str, outputFileCLP: str = '') -> None:
        """Converts a SVG file to a CLP file.
           If outputFileCLP is left empty, a file a the same base name but .clp extension is created."""
        inFilePath = Path(inputFileSVG)
        if (not outputFileCLP): #check for None and empty string
            outputFileCLP = Path(inFilePath.parent).joinpath(inFilePath.stem + ".clp")

        #read SVG into memory        
        svgFile = open(inFilePath,"rt")
        contents = svgFile.read()
        svgFile.close()

        #convert input string to its byte representation using utf-8 encoding.
        # and convert that to a hex string,
        tempCLPdata = contents.encode('utf-8').hex()

        #write CLP file by just adding the header
        outFile = open(outputFileCLP,"wb")
        outFile.write('a'.encode('ASCII'))
        outFile.write(tempCLPdata.encode('utf-8'))
        outFile.close()


#if __name__ == '__main__':
    # only executed when this file is run directly.

    #clpFile.convertSVGtoCLP("circle.svg")

    #myClp = clpFile()
    #myClp.readClp("circle.clp")
    #myClp.convertToPngInBuffer(200,30)
    #myClp.savePNGfromBufferToFile("test.png")

    ## create pdf
    #from reportlab.pdfgen import canvas
    #import reportlab.lib.pagesizes
    #from reportlab.lib.utils import ImageReader
    #from reportlab.pdfbase import pdfmetrics
    #from reportlab.lib import colors
    #pagesize = reportlab.lib.pagesizes.A4
    #pdf = canvas.Canvas("test" + '.pdf', pagesize=pagesize)
    #pdf.setFillColor(colors.gray)
    #pdf.rect(20,20, 200, 200, fill=1)
    #pdf.drawImage(ImageReader(myClp.pngMemFile), 72, 72, width= 20 * 1/25.4*72, height=2 * 1/25.4*72)
    #pdf.showPage()
    #pdf.save()