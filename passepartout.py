# SPDX-License-Identifier:LGPL-3.0-only or GPL-3.0-only

# In this file it is permitted to catch exceptions on a broad basis since there
# are many things that can go wrong with file handling and parsing:
#    pylint: disable=bare-except,broad-except
# We're not quite at the level of documenting all the classes and functions yet :-)
#    pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

# Copyright (c) 2020 by BarchSteel

from pathlib import Path
import os
import os.path
# import cairosvg
# import PIL
import logging
# from PIL.ExifTags import TAGS
# from io import BytesIO
# from clpFile import ClpFile
from typing import List # Set, Dict, Tuple, Optional
from typing import NamedTuple
from lxml import etree

configlogger = logging.getLogger("cewe2pdf.config")

class Passepartout():
    def __init__(self):
        return

    class decorationXmlInfo(NamedTuple):
        srcXmlFile: str
        designElementId: int
        decoration_id: str
        decoration_type: str
        designElementType: str
        maskFile: str
        clipartFile: str
        fotoarea_height: float
        fotoarea_width: float
        fotoarea_x: float
        fotoarea_y: float

    @staticmethod
    def extractInfoFromXml(xmlFileName: str, passepartoutid: int):
        for xmlInfo in Passepartout.extractAllInfosFromXml(xmlFileName):
            if xmlInfo.designElementId == passepartoutid:
                return xmlInfo
        return None

    @staticmethod
    def extractAllInfosFromXml(xmlFileName: str):
        # read information from xml file about passepartout

        try:
            with open(xmlFileName, 'rb') as clipArtXml:
                xmlInfo = etree.parse(clipArtXml)
        except IOError as ioe:
            logging.error(f"I/O error({ioe.errno}): {ioe.strerror}")
            return None
        except Exception as e: # handle other exceptions such as attribute errors
            logging.error(f"Error: {e}")
            return None

        for decoration in xmlInfo.findall('decoration'):
            decoration_id = decoration.get('id')
            decoration_type = decoration.get('type')
            # decoration_type is often "fading", so typeElement is then looking for <fading .../>
            typeElement = decoration.find(decoration_type)
            if typeElement is None:
                continue
            # assume these IDs are always integers.
            designElementId = decoration.get('designElementId')
            if designElementId is None:
                designElementId = typeElement.get('designElementId')
                if designElementId is None:
                    continue
            designElementId = int(designElementId)

            designElementType = typeElement.get('designElementType')
            maskFile = typeElement.get('file')
            clipartElement = typeElement.find('clipart')
            if clipartElement is not None:
                clipartFile = clipartElement.get('file')
            else:
                clipartFile = None
            fotoareaElement = typeElement.find('fotoarea')
            if fotoareaElement is not None:
                fotoarea_height = float(fotoareaElement.get('height'))
                fotoarea_width = float(fotoareaElement.get('width'))
                fotoarea_x = float(fotoareaElement.get('x'))
                fotoarea_y = float(fotoareaElement.get('y'))
            else:
                fotoarea_height = None
                fotoarea_width = None
                fotoarea_x = None
                fotoarea_y = None

            yield Passepartout.decorationXmlInfo(xmlFileName, designElementId, decoration_id, decoration_type,
                            designElementType, maskFile, clipartFile,
                            fotoarea_height, fotoarea_width, fotoarea_x, fotoarea_y)
        return None

    @staticmethod
    def buildElementIdIndex(directoryList: List[str]) -> dict:
        # go through directories and search for .xml files and build a dictionary of
        #  designElementId to .xml file

        # a dictionary for passepartout element IDs to file name
        passepartoutIdDict = {}

        if directoryList is None:
            configlogger.error("No directories passed to Passepartout.buildElementIdIndex!")
            return passepartoutIdDict

        if isinstance(directoryList, tuple):
            directoryList = list(directoryList)

        if not isinstance(directoryList, list):
            directoryList = [directoryList]

        configlogger.info("Refreshing decoration designElementId index.")

        # generate list of .xml files
        xmlFileList = []
        ext = ".xml"
        for path in directoryList:
            for dirpath, dirnames, filenames in os.walk(path): # dirnames pylint: disable=unused-variable
                for filename in (f for f in filenames if f.endswith(ext)):
                    xmlFileList.append(os.path.join(dirpath, filename))
                    # print(os.path.join(dirpath, filename))
        configlogger.info(f"Found {len(xmlFileList):d} XML files.")

        # load each .xml file and extract the information
        for curXmlFile in xmlFileList:
            # print("Parsing passepartout: {}".format(curXmlFile))
            for xmlInfo in Passepartout.extractAllInfosFromXml(curXmlFile):
                if xmlInfo is None:
                    continue  # this .xml file is not for a passepartout, or something went wrong
                if xmlInfo.designElementType == 'passepartout':
                    # print("Adding passepartout to dict: {}".format(curXmlFile))
                    passepartoutIdDict[xmlInfo.designElementId] = curXmlFile

        return passepartoutIdDict

    @staticmethod
    def getPassepartoutFileFullName(xmlInfo:decorationXmlInfo, fileName:str) -> str:
        if fileName is None:
            return None
        pathObj = Path(xmlInfo.srcXmlFile)
        # should not be needed: pathObj = pathObj.resolve()    # convert it to an absolute path
        basePath = pathObj.parent
        fullPath = basePath.joinpath(fileName)
        return str(fullPath)

    @staticmethod
    def getClipartFullName(xmlInfo:decorationXmlInfo) -> str:
        return Passepartout.getPassepartoutFileFullName(xmlInfo, xmlInfo.clipartFile)

    @staticmethod
    def getMaskFullName(xmlInfo:decorationXmlInfo) -> str:
        return Passepartout.getPassepartoutFileFullName(xmlInfo, xmlInfo.maskFile)


if __name__ == '__main__':
    # only executed when this file is run directly.
    myDict = Passepartout.buildElementIdIndex(
        [r"C:\ProgramData\hps\1320",
         "C:/Program Files/dm/dm-Fotowelt/Resources/photofun/decorations"])
    testId = 125186
    testXmlInfo = Passepartout.extractInfoFromXml(myDict[testId], testId)
    print(testId)
    print(testXmlInfo)
    print(Passepartout.getClipartFullName(testXmlInfo))
