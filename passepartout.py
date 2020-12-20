# SPDX-License-Identifier:LGPL-3.0-only or GPL-3.0-only

# Copyright (c) 2020 by BarchSteel

from pathlib import Path
import os
import os.path
import cairosvg
import PIL
from PIL.ExifTags import TAGS
from io import BytesIO
from clpFile import ClpFile
from typing import List, Set, Dict, Tuple, Optional
from lxml import etree
from typing import NamedTuple


class Passepartout(object):
    def __init__(self):
        return

    class decorationXmlInfo(NamedTuple):
        designElementId: int
        decoration_id: int
        decoration_type: str
        designElementType: str
        maskFile: str
        clipartFile: str
        fotoarea_height: float
        fotoarea_width: float
        fotoarea_x: float
        fotoarea_y: float

    @staticmethod
    def extractInfoFromXml(xmlFileName:  str):
        # read information from xml file about passepartout

        clipArtXml = open(xmlFileName, 'rb')
        xmlInfo = etree.parse(xmlFileName)
        clipArtXml.close()

        for decoration in xmlInfo.findall('decoration'):
            # assume these IDs are always integers.
            designElementId = decoration.get('designElementId')
            if designElementId is None:
                continue
            decoration_id = decoration.get('id')
            decoration_type = decoration.get('type')
            # decoration_type is often "fading", so typeElement is then looking for <fading .../>
            typeElement = decoration.find(decoration_type)
            designElementType = typeElement.get('designElementType')
            maskFile = typeElement.get('file')
            clipartElement = typeElement.find('clipart')
            clipartFile = clipartElement.get('file')
            fotoareaElement = typeElement.find('fotoarea')
            fotoarea_height = fotoareaElement.get('height')
            fotoarea_width = fotoareaElement.get('width')
            fotoarea_x = fotoareaElement.get('x')
            fotoarea_y = fotoareaElement.get('y')

            return Passepartout.decorationXmlInfo(designElementId, decoration_id, decoration_type, designElementType, maskFile, clipartFile,
                                                  fotoarea_height, fotoarea_width, fotoarea_x, fotoarea_y)
        return None

    @staticmethod
    def buildElementIdIndex(directoryList:  List[str]) -> dict:
        # go through directories and search for .xml files and build a dictionary of
        #  designElementId to .xml file

        # a dictionary for passepartout element IDs to file name
        passepartoutIdDict = dict()

        if isinstance(directoryList, tuple):
            directoryList = list(directoryList)

        if not isinstance(directoryList, list):
            directoryList = [directoryList]

        print("Refreshing decoration designElementId index.")

        # generate list of .xml files
        xmlFileList = []
        ext = ".xml"
        for path in directoryList:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in (f for f in filenames if f.endswith(ext)):
                    xmlFileList.append(os.path.join(dirpath, filename))
                    #print(os.path.join(dirpath, filename))
        print("Found {:d} XML files.".format(len(xmlFileList)))

        # load each .xml file and extract the information
        for curXmlFile in xmlFileList:
            xmlInfo = Passepartout.extractInfoFromXml(curXmlFile)
            if xmlInfo is None:
                continue  # this .xml file is not for a passepartout, or something went wrong
            if (xmlInfo.designElementType == 'passepartout'):
                print("Found passepartout: {}".format(curXmlFile))
                passepartoutIdDict[xmlInfo.designElementId] = curXmlFile

        return passepartoutIdDict


if __name__ == '__main__':
    # only executed when this file is run directly.
    Passepartout.buildElementIdIndex(
        [r"C:\ProgramData\hps\1320",
         "C:/Program Files/dm/dm-Fotowelt/Resources/photofun/decorations"])
