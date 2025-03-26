import logging
import os.path
import os

from pathlib import Path

from clpFile import ClpFile  # for clipart .CLP and .SVG files
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
