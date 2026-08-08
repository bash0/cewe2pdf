"""Prepare the input, configuration, and rendering resources for one conversion."""

import configparser
import logging
import os
import os.path
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lxml import etree

from ceweInfo import CeweInfo
from clipArt import readClipArtConfigXML
from configUtils import getConfigurationInt
from extraLoggers import mustsee
from fontHandling import findAndRegisterFonts
from lineScales import LineScales
from mcfx import unpackMcfx
from pathutils import findFileInDirs


@dataclass
class ConversionSetup:
    """Input and resources resolved before the PDF canvas is created."""

    album_title: str
    mcf_xml_name: str
    unpacked_folder: str | None
    album_base_folder: str
    mcf_base_folder: str
    fotobook: Any
    configuration: configparser.ConfigParser | None
    default_config_section: Any
    cewe_folder: str
    key_account_folder: str | None
    background_locations: tuple[str, ...]
    passepartout_folders: tuple[str, ...]
    clipart_files: dict[int, str]
    clipart_paths: tuple[str, ...]
    image_resolution: int
    background_resolution: int
    available_fonts: Any


def prepareConversion(albumname, mcfxTmpDir, appDataDir) -> ConversionSetup: # noqa: C901
    """Read an album and resolve the configuration and resources it requires."""
    albumTitle, dummy = os.path.splitext(os.path.basename(albumname))

    # Check for the archive format introduced around CEWE 7.3.
    mcfxFormat = albumname.endswith('.mcfx')
    if mcfxFormat:
        albumPathObj = Path(albumname).resolve()
        unpackedFolder, mcfxmlname = unpackMcfx(albumPathObj, mcfxTmpDir)
    else:
        unpackedFolder = None
        mcfxmlname = albumname

    # The original album folder locates configuration; the MCF folder locates images.
    albumBaseFolder = str(Path(albumname).resolve().parent)
    mcfPathObj = Path(mcfxmlname).resolve()
    mcfBaseFolder = str(mcfPathObj.parent)

    # Read as binary so the XML parser retains the file's UTF-8 encoding.
    try:
        with open(mcfxmlname, 'rb') as mcffile:
            mcf = etree.parse(mcffile)
    except Exception as exception:
        invalidmsg = f'Cannot open mcf file {mcfxmlname}'
        if mcfxFormat:
            invalidmsg += f' (unpacked from {albumname})'
        logging.error(f'{invalidmsg}: {repr(exception)}')
        sys.exit(1)

    fotobook = mcf.getroot()
    CeweInfo.ensureAcceptableAlbumMcf(fotobook, albumname, mcfxmlname, mcfxFormat)

    clipartFiles = {}
    passepartoutFolders = tuple[str]()
    defaultConfigSection = None
    configuration = None
    imageResolution = 150
    backgroundResolution = 150

    # Prefer the legacy cewe_folder.txt file when it is present.  Otherwise,
    # read the current-directory INI first and the album INI second, so the
    # album-specific values override the current-directory defaults.
    try:
        configFolderFileName = findFileInDirs(
            'cewe_folder.txt',
            (albumBaseFolder, os.path.curdir, os.path.dirname(os.path.realpath(__file__))))
        with open(configFolderFileName, 'r') as ceweFile: # pylint: disable=unspecified-encoding
            ceweFolder = ceweFile.read().strip()
            CeweInfo.checkCeweFolder(ceweFolder)
            keyAccountNumber = CeweInfo.getKeyAccountNumber(ceweFolder)
            keyAccountFolder = CeweInfo.getKeyAccountDataFolder(keyAccountNumber)
            backgroundLocations = CeweInfo.getBaseBackgroundLocations(ceweFolder, keyAccountFolder)

    except: # noqa: E722
        logging.info('Trying cewe2pdf.ini from current directory and from the album directory.')
        configuration = configparser.ConfigParser()
        filesread = configuration.read(['cewe2pdf.ini', os.path.join(albumBaseFolder, 'cewe2pdf.ini')])
        if len(filesread) < 1:
            logging.error('You must create cewe_folder.txt or cewe2pdf.ini to specify the cewe_folder')
            sys.exit(1)

        mustsee.info(f'Using configuration files, in order: {str(filesread)}')
        defaultConfigSection = configuration['DEFAULT']
        if 'cewe_folder' not in defaultConfigSection:
            logging.error('You must create cewe_folder.txt or modify cewe2pdf.ini to define cewe_folder')
            sys.exit(1)

        ceweFolder = defaultConfigSection['cewe_folder'].strip()
        CeweInfo.checkCeweFolder(ceweFolder)
        keyAccountNumber = CeweInfo.getKeyAccountNumber(ceweFolder, defaultConfigSection)
        CeweInfo.SetEnvironmentVariables(ceweFolder, keyAccountNumber)
        keyAccountFolder = CeweInfo.getKeyAccountDataFolder(keyAccountNumber, defaultConfigSection)

        baseBackgroundLocations = CeweInfo.getBaseBackgroundLocations(ceweFolder, keyAccountFolder)
        extraBackgroundFolders = defaultConfigSection.get('extraBackgroundFolders', '').splitlines()
        backgroundLocations = baseBackgroundLocations + tuple(
            os.path.expandvars(folder) for folder in extraBackgroundFolders if folder)

        extraClipArts = defaultConfigSection.get('extraClipArts', '').splitlines()
        for extraClipArt in extraClipArts:
            if not extraClipArt:
                continue
            definition = os.path.expandvars(extraClipArt).split(',')
            if len(definition) == 2:
                clipartFiles[int(definition[0])] = definition[1].strip()

        configuredPassepartoutFolders = defaultConfigSection.get('passepartoutFolders', '').splitlines()
        configuredPassepartoutFolders.append(ceweFolder)
        passepartoutFolders = tuple(
            os.path.expandvars(folder) for folder in configuredPassepartoutFolders if folder)

        imageResolution = getConfigurationInt(defaultConfigSection, 'pdfImageResolution', '150', 100)
        backgroundResolution = getConfigurationInt(defaultConfigSection, 'pdfBackgroundResolution', '150', 100)

    mustsee.info(f'Using image resolution {imageResolution}, background resolution {backgroundResolution}')

    LineScales.setupDefaultLineScale(defaultConfigSection)
    if keyAccountFolder is not None:
        passepartoutFolders += CeweInfo.getCewePassepartoutFolders(ceweFolder, keyAccountFolder)

    availableFonts = findAndRegisterFonts(defaultConfigSection, appDataDir, albumBaseFolder, ceweFolder)
    LineScales.setupFontLineScales(defaultConfigSection)
    clipartPaths = readClipArtConfigXML(ceweFolder, keyAccountFolder, clipartFiles)

    return ConversionSetup(
        albumTitle, mcfxmlname, unpackedFolder, albumBaseFolder, mcfBaseFolder,
        fotobook, configuration, defaultConfigSection, ceweFolder, keyAccountFolder,
        backgroundLocations, passepartoutFolders, clipartFiles, clipartPaths,
        imageResolution, backgroundResolution, availableFonts)
