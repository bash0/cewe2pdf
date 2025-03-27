import glob
import logging
import os.path
import os
import sys
from enum import Enum

import reportlab.lib

from lxml import etree
from extraLoggers import mustsee


class ProductStyle(Enum):
    AlbumSingleSide = 1  # normal for albums, we divide the cewe 2 page bundle to single pages
    AlbumDoubleSide = 2  # any album when --keepdoublepages is set
    MemoryCard = 3 # memory card game


class AlbumInfo():
    def __init__(self):
        return

    # page sizes for various products. Probably not important since the bundlesize element
    # is used to set the page sizes along the way
    formats = {
        "ALB82": reportlab.lib.pagesizes.A4,
        "ALB98": reportlab.lib.pagesizes.A4, # unittest, L 20.5cm x 27.0cm
        "ALB32": (300 * reportlab.lib.pagesizes.mm, 300 * reportlab.lib.pagesizes.mm), # album XL, 30 x 30 cm
        "ALB17": (205 * reportlab.lib.pagesizes.mm, 205 * reportlab.lib.pagesizes.mm), # album kvadratisk, 20.5 x 20.5 cm
        "ALB69": (5400/100/2*reportlab.lib.units.cm, 3560/100*reportlab.lib.units.cm),
        # add other page sizes here
        "MEM3": (300 * reportlab.lib.pagesizes.mm, 300 * reportlab.lib.pagesizes.mm) # memory game cards 6x6cm
        }

    # product style. The CEWE album products (which is what we are normally expecting in this
    # code) are basically defined in two page bundles. We normally will want single side pdfs
    # so we let the style default to ProductStyle.AlbumSingleSide unless the product is found
    # in this table. If we want to keep the double side layout in the pdf, then the keepDoublePages
    # option will cause AlbumSingleSide to be changed to AlbumDoubleSide.
    # Other "non-album" styles which we handle appear in this table
    styles = {
        "MEM3": ProductStyle.MemoryCard # memory game cards 6x6cm
        }

    @staticmethod
    def isAlbumProduct(ps: ProductStyle):
        return ps in (ProductStyle.AlbumSingleSide, ProductStyle.AlbumDoubleSide)

    @staticmethod
    def isAlbumSingleSide(ps: ProductStyle):
        return ps == ProductStyle.AlbumSingleSide

    @staticmethod
    def isAlbumDoubleSide(ps: ProductStyle):
        return ps == ProductStyle.AlbumDoubleSide


class CeweInfo():
    def __init__(self):
        return

    @staticmethod
    def getBaseClipartLocations(baseFolder):
        # create a tuple of places (folders) where background resources would be found by default
        baseClipartLocations = (
            os.path.join(baseFolder, 'Resources', 'photofun', 'decorations'),   # trailing comma is important to make a 1-element tuple
            # os.path.join(baseFolder, 'Resources', 'photofun', 'decorations', 'form_frames'),
            # os.path.join(baseFolder, 'Resources', 'photofun', 'decorations', 'frame_frames')
        )
        return baseClipartLocations

    @staticmethod
    def getBaseBackgroundLocations(basefolder, keyaccountFolder):
        # create a tuple of places (folders) where background resources would be found by default
        baseBackgroundLocations = (
            os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds'),
            os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'einfarbige'),
            os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'multicolor'),
            os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', 'spotcolor'),
        )

        # at some point the base cewe organisation of the backgrounds has been changed
        baseBackgroundLocations = baseBackgroundLocations + \
            tuple(glob.glob(os.path.join(basefolder, 'Resources', 'photofun', 'backgrounds', "*", "*/")))

        # and then the key account may have added some more backgrounds ...
        if keyaccountFolder is not None:
            baseBackgroundLocations = baseBackgroundLocations + \
                tuple(glob.glob(os.path.join(keyaccountFolder, "addons", "*", "backgrounds", "v1", "backgrounds/"))) + \
                tuple(glob.glob(os.path.join(keyaccountFolder, "addons", "*", "backgrounds", "v1/"))) + \
                tuple(glob.glob(os.path.join(keyaccountFolder, "photofun", "backgrounds", "*", "*/"))) # from 7.3.4 onwards, I think

        return baseBackgroundLocations

    @staticmethod
    def getCewePassepartoutFolders(cewe_folder, keyAccountFolder):
        return \
            tuple([os.path.join(keyAccountFolder, "addons")]) + \
            tuple([os.path.join(keyAccountFolder, "photofun", "decorations")]) + \
            tuple([os.path.join(cewe_folder, "Resources", "photofun", "decorations")])

    @staticmethod
    def SetEnvironmentVariables(cewe_folder, keyAccountNumber):
        # put values into the environment so that it can be substituted in later
        # config elements in the ini file, eg as ${CEWE_FOLDER}
        os.environ['CEWE_FOLDER'] = cewe_folder
        os.environ['KEYACCOUNT'] = keyAccountNumber

    @staticmethod
    def getOutputFileName(mcfname):
        return mcfname + '.pdf'

    @staticmethod
    def checkCeweFolder(cewe_folder):
        if os.path.exists(cewe_folder):
            mustsee.info(f"cewe_folder is {cewe_folder}")
        else:
            logging.error(f"cewe_folder {cewe_folder} not found. This must be a test run which doesn't need it!")

    @staticmethod
    def ensureAcceptableOutputFile(outputFileName):
        if os.path.exists(outputFileName):
            if os.path.isfile(outputFileName):
                if not os.access(outputFileName, os.W_OK):
                    logging.error(f"Existing output file '{outputFileName}' is not writable")
                    sys.exit(1)
                # this still won't have caught the case where the output file is opened for
                # exclusive access by another process (eg Acrobat does that). We plan to
                # overwrite the file anyway so we just check by opening it for writing and
                # then closing it again before we do our normal stuff
                try:
                    with open(outputFileName, 'w'): # encoding is irrelevant, so pylint: disable=unspecified-encoding
                        logging.info(f"Existing output file '{outputFileName}' can be written")
                except Exception as e: # pylint: disable=broad-exception-caught
                    logging.error(f"Existing output file '{outputFileName}' is writable, but not accessible {str(e)}")
                    sys.exit(1)
            else:
                logging.error(f"Existing output '{outputFileName}' is not a file")
                sys.exit(1)

    @staticmethod
    def ensureAcceptableAlbumMcf(fotobook, albumname, mcfxmlname, mcfxFormat):
        if fotobook.tag != 'fotobook':
            invalidmsg = f"Cannot process invalid mcf file (root tag is not 'fotobook'): {mcfxmlname}"
            if mcfxFormat:
                invalidmsg = invalidmsg + f" (unpacked from {albumname})"
            logging.error(invalidmsg)
            sys.exit(1)

        startdatecalendarium = fotobook.attrib['startdatecalendarium']
        if startdatecalendarium is not None and len(startdatecalendarium) > 0:
            invalidmsg = f"Cannot process calendar mcf files (yet!): {mcfxmlname}"
            if mcfxFormat:
                invalidmsg = invalidmsg + f" (unpacked from {albumname})"
            logging.error(invalidmsg)
            sys.exit(1)

    @staticmethod
    def getCeweFontsFolder(cewe_folder):
        return os.path.join(cewe_folder, 'Resources', 'photofun', 'fonts')

    @staticmethod
    def getCeweDecorationsFolder(cewe_folder):
        return os.path.join(cewe_folder, 'Resources', 'photofun', 'decorations')

    @staticmethod
    def getHpsDataFolder():
        # linux + macosx
        dotMcfFolder = os.path.expanduser("~/.mcf/hps/")
        if os.path.exists(dotMcfFolder):
            return dotMcfFolder

        # windows
        # from some time around september 2022 (07.02.05) the key account folder seems to have been moved
        # (or perhaps added to on a per user basis?) from ${PROGRAMDATA}/hps/ to ${LOCALAPPDATA}/CEWE/hps/
        winHpsFolder = os.path.expandvars("${LOCALAPPDATA}/CEWE/hps/")
        if os.path.exists(winHpsFolder):
            return winHpsFolder
        # check for the older location
        winHpsFolder = os.path.expandvars("${PROGRAMDATA}/hps/")
        if os.path.exists(winHpsFolder):
            logging.info(f'hps data folder found at old location {winHpsFolder}')
            return winHpsFolder

        return None

    @staticmethod
    def getKeyAccountDataFolder(keyAccountNumber, configSection=None):
        # for testing (in particular on checkin on github where no cewe product is installed)
        # we may want to have a specially constructed local key account data folder
        if configSection is not None:
            inihps = configSection.get('hpsFolder')
            if inihps is not None:
                inikadf = os.path.join(inihps, keyAccountNumber)
                if os.path.exists(inikadf):
                    logging.info(f'ini file overrides hps folder, key account folder set to {inikadf}')
                    return inikadf.strip()
                logging.error(f'ini file overrides hps folder, but key account folder {inikadf} does not exist. Using defaults')

        hpsFolder = CeweInfo.getHpsDataFolder()
        if hpsFolder is None:
            logging.warning('No installed hps data folder found')
            return None

        kadf = os.path.join(hpsFolder, keyAccountNumber)
        if os.path.exists(kadf):
            mustsee.info(f'Installed key account data folder at {kadf}')
            return kadf
        logging.error(f'Installed key account data folder {kadf} not found')
        return None

    @staticmethod
    def getKeyAccountFileName(cewe_folder):
        keyAccountFileName = os.path.join(cewe_folder, "Resources", "config", "keyaccount.xml")
        return keyAccountFileName

    @staticmethod
    def getKeyAccountNumber(cewe_folder, configSection=None):
        keyAccountFileName = CeweInfo.getKeyAccountFileName(cewe_folder)
        try:
            katree = etree.parse(keyAccountFileName)
            karoot = katree.getroot()
            ka = karoot.find('keyAccount').text # that's the official installed value
            # see if he has a .ini file override for the keyaccount
            if configSection is not None:
                inika = configSection.get('keyaccount')
                if inika is not None:
                    logging.info(f'ini file overrides keyaccount from {ka} to {inika}')
                    ka = inika
        except Exception: # pylint: disable=broad-exception-caught
            ka = "0"
            logging.error(f'Could not extract keyAccount tag in file: {keyAccountFileName}, using {ka}')
        return ka.strip()
