import glob
import logging
import os.path
import os

from pathlib import Path
from lxml import etree

from ceweInfo import CeweInfo
from clpFile import ClpFile  # for clipart .CLP and .SVG files
from extraLoggers import configlogger
from pathutils import findFileInDirs


def loadClipart(fileName, clipartPathList) -> ClpFile:
    """Tries to load a clipart file. Either from .CLP or .SVG file
    returns a clpFile object"""
    newClpFile = ClpFile("")

    if os.path.isabs(fileName):
        filePath = Path(fileName)
        if not filePath.exists():
            filePath = filePath.parent.joinpath(filePath.stem+".clp")
            if not filePath.exists():
                logging.error(f"Missing .clp: {fileName}")
                return ClpFile("")   # return an empty ClpFile
    else:
        pathObj = Path(fileName)
        # the name can actually be "correct", but its stem may not be in the clipartPathList. This will
        # happen at least for passepartout clip masks when we're using a local test hps structure rather
        # than an installed cewe_folder. For that reason we add the file's own folder to the clipartPathList
        # before searching for a clp or svg file matching the stem
        baseFileName = pathObj.stem
        fileFolder = pathObj.parent
        try:
            filePath = findFileInDirs([baseFileName+'.clp', baseFileName+'.svg'], (fileFolder,) + clipartPathList)
            filePath = Path(filePath)
        except Exception as ex: # pylint: disable=broad-exception-caught
            logging.error(f" {baseFileName}, {ex}")
            return ClpFile("")   # return an empty ClpFile

    if filePath.suffix == '.clp':
        newClpFile.readClp(filePath)
    else:
        newClpFile.loadFromSVG(filePath)

    return newClpFile

def getClipConfig(Element):
    colorreplacements = []
    flipX = False
    flipY = False
    for clipconfig in Element.findall('ClipartConfiguration'):
        for clipcolors in clipconfig.findall('colors'):
            for clipcolor in clipcolors.findall('color'):
                source = '#'+clipcolor.get('source').upper()[1:7]
                target = '#'+clipcolor.get('target').upper()[1:7]
                replacement = (source, target)
                colorreplacements.append(replacement)
        mirror = clipconfig.get('mirror')
        if mirror is not None:
            # cewe developers have a different understanding of x and y :)
            if mirror in ('y', 'both'):
                flipX = True
            if mirror in ('x', 'both'):
                flipY = True
    return colorreplacements, flipX, flipY


def readClipArtConfigXML(baseFolder, keyaccountFolder, clipartDict):
    """Parse the configuration XML file and generate a dictionary of designElementId to fileName
    currently only cliparts_default.xml is supported !"""
    clipartPathList = CeweInfo.getBaseClipartLocations(baseFolder) # append instead of overwrite global variable
    xmlConfigFileName = 'cliparts_default.xml'
    try:
        xmlFileName = findFileInDirs(xmlConfigFileName, clipartPathList)
        loadClipartConfigXML(xmlFileName, clipartDict)
        configlogger.info(f'{xmlFileName} listed {len(clipartDict)} cliparts')
    except: # noqa: E722 # pylint: disable=bare-except
        configlogger.info(f'Could not locate and load the clipart definition file: {xmlConfigFileName}')
        configlogger.info('Trying a search for cliparts instead')
        # cliparts_default.xml went missing in 7.3.4 so we have to go looking for all the individual xml
        # files, which still seem to be there and have the same format as cliparts_default.xml, and see
        # if we can build our internal dictionary from them.
        decorations = CeweInfo.getCeweDecorationsFolder(baseFolder)
        configlogger.info(f'clipart xml path: {decorations}')
        for (root, dirs, files) in os.walk(decorations): # walk returns a 3-tuple so pylint: disable=unused-variable
            for decorationfile in files:
                if decorationfile.endswith(".xml"):
                    loadClipartConfigXML(os.path.join(root, decorationfile), clipartDict)
        numberClipartsLocated = len(clipartDict)
        if numberClipartsLocated > 0:
            configlogger.info(f'{numberClipartsLocated} clipart xmls found')
        else:
            configlogger.error('No clipart xmls found, no delivered cliparts will be available.')

    if keyaccountFolder is None:
        # In "production" this is definitely an error, although for unit tests (in particular when
        # run on the checkin build where CEWE is not installed and there is definitely no downloaded
        # stuff from the installation) it isn't really an error because there is a local folder
        # tests/Resources/photofun/decorations with the clipart files needed for the tests.
        configlogger.error("No downloaded clipart folder found")
        return clipartPathList

    # from (at least) 7.3.4 the addon cliparts might be in more than one structure, so ... first the older layout
    addonclipartxmls = os.path.join(keyaccountFolder, "addons", "*", "cliparts", "v1", "decorations", "*.xml")
    for file in glob.glob(addonclipartxmls):
        loadClipartConfigXML(file, clipartDict)

    # then the newer layout
    currentClipartCount = len(clipartDict)
    localDecorations = os.path.join(keyaccountFolder, 'photofun', 'decorations')
    xmlfiles = glob.glob(os.path.join(localDecorations, "*", "*", "*.xml"))
    configlogger.info(f'local clipart xml path: {localDecorations}')
    for xmlfile in xmlfiles:
        loadClipartConfigXML(xmlfile, clipartDict)
    numberClipartsLocated = len(clipartDict) - currentClipartCount
    if numberClipartsLocated > 0:
        configlogger.info(f'{numberClipartsLocated} local clipart xmls found')

    if len(clipartDict) == 0:
        configlogger.error('No cliparts found')

    return clipartPathList


def loadClipartConfigXML(xmlFileName, clipartDict):
    try:
        with open(xmlFileName, 'rb') as clipArtXml:
            xmlInfo = etree.parse(clipArtXml)
        for decoration in xmlInfo.findall('decoration'):
            clipartElement = decoration.find('clipart')
            # we might be reading a decoration definition that is not clipart, just ignore those
            if clipartElement is None:
                continue
            fileName = os.path.join(os.path.dirname(xmlFileName), clipartElement.get('file'))
            designElementId = int(clipartElement.get('designElementId'))    # assume these IDs are always integers.
            clipartDict[designElementId] = fileName
    except Exception as clpOpenEx: # pylint: disable=broad-exception-caught
        logging.error(f"Cannot open clipart file {xmlFileName}: {repr(clpOpenEx)}")
