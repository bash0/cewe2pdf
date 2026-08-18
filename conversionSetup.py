"""Prepare the input, configuration, and rendering resources for one conversion."""

# This module deliberately gathers the many resources required for one
# conversion into one named result.  Splitting the preparation function or its
# dataclass purely to satisfy Pylint's default size limits would obscure that
# relationship.  Broad catches are also intentional: the legacy configuration
# file is optional, and malformed album input needs a user-facing error.
# pylint: disable=bare-except,broad-exception-caught,too-many-instance-attributes,too-many-locals,too-many-statements

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
from conversionState import ConversionState
from extraLoggers import mustsee
from fontHandling import findAndRegisterFonts
from lineScales import LineScales
from mcfx import unpackMcfx
from windowsIntegration import findInstalledCeweFolder


@dataclass
class ConversionSetup:
    """Input and read-only resources resolved before the PDF canvas is created.

    Values here describe the album and its configured rendering environment.
    Data discovered while rendering belongs in :class:`ConversionState`
    instead, so it is clear which values are safe to share with all pages.
    """

    key_account_folder: str | None  # Account-specific CEWE data directory when one can be determined.

    configuration: configparser.ConfigParser            # Merged current-directory and album INI configuration.
    default_config_section: Any             # The DEFAULT INI section, passed to renderers needing an individual setting.

    background_locations: tuple[str, ...]   # Ordered directories searched for CEWE page-background images.
    clipart_files: dict[int, str]           # Extra clipart ID-to-file mappings configured in the INI file.
    clipart_paths: tuple[str, ...]          # Clipart XML/resource search paths resolved from the CEWE installation.
    passepartout_folders: tuple[str, ...]   # Ordered directories searched when building the passepartout index.

    mcf_xml_name: str           # Actual XML file to parse: the source MCF, or data.mcf unpacked from MCFX.
    mcf_base_folder: str        # Folder containing mcf_xml_name, used to resolve album image references.
    unpacked_folder: str | None # TemporaryDirectory returned when an MCFX archive was unpacked; otherwise None.
    album_base_folder: str      # Original album location, used to find its optional configuration file.

    fotobook: Any       # Root <fotobook> XML element used by the page-processing stage.
    album_title: str    # Human-readable album name, used as the PDF document title.

    available_fonts: Any        # Font faces successfully registered with ReportLab for this conversion.
    line_scales: LineScales     # Default and per-font line-spacing rules read from the INI configuration.

    image_resolution: int       # Target DPI for ordinary images.
    background_resolution: int  # Target DPI for page-background images.


def prepareConversion(albumname, mcfxTmpDir, appDataDir, state: ConversionState,
                      automaticWindows: bool = False) -> ConversionSetup: # noqa: C901
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
    ceweFolder = None
    keyAccountFolder = None
    backgroundLocations = tuple[str]()
    imageResolution = 150
    backgroundResolution = 150

    # Read the current-directory INI first and the album INI second, so the
    # album-specific values override the current-directory defaults. Neither
    # configuration source is required: without a CEWE installation we can
    # still render album-contained photos and ordinary text using local fonts.
    #
    # cewe_folder.txt was the original one-value configuration mechanism. Do
    # not read it: its implicit precedence made configuration hard to reason
    # about. Warn once per distinct file so an existing user can migrate it.
    legacyConfigPaths = {
        os.path.abspath(os.path.join(folder, 'cewe_folder.txt'))
        for folder in (albumBaseFolder, os.path.curdir, os.path.dirname(os.path.realpath(__file__)))
    }
    for legacyConfigPath in legacyConfigPaths:
        if os.path.isfile(legacyConfigPath):
            logging.warning(
                f'Ignoring legacy CEWE configuration file: {legacyConfigPath}. '
                'Move its CEWE folder setting to cewe2pdf.ini.')

    logging.info('Trying cewe2pdf.ini from current directory and from the album directory.')
    configuration = configparser.ConfigParser()
    filesread = configuration.read(['cewe2pdf.ini', os.path.join(albumBaseFolder, 'cewe2pdf.ini')])
    defaultConfigSection = configuration['DEFAULT']
    if automaticWindows:
        # Explorer's context menu is designed for non-programmers: do not
        # require manual INI editing. Local system fonts are also useful in
        # this self-contained mode.
        defaultConfigSection['loadSystemFonts'] = 'True'
    if filesread:
        mustsee.info(f'Using configuration files, in order: {str(filesread)}')
    elif automaticWindows:
        # Explorer mode can discover CEWE from the MCF/MCFX association,
        # so the absence of an INI file is expected rather than a warning.
        mustsee.info(
            'No CEWE configuration found; trying automatic CEWE installation discovery.')
    else:
        mustsee.warning(
            'No CEWE configuration or installation found: continuing with local fonts and '
            'album-contained resources only. CEWE backgrounds, delivered clipart and '
            'passepartouts will be unavailable.')

    configuredCeweFolder = defaultConfigSection.get('cewe_folder', '').strip()
    # An album-side INI can explicitly identify the CEWE folder. In Explorer
    # mode a valid configured folder still wins: the album owner knows best.
    # If it is absent or no longer exists, try to discover the installed CEWE
    # application instead.
    if automaticWindows and (not configuredCeweFolder or
                             not os.path.isdir(configuredCeweFolder)):
        if configuredCeweFolder:
            logging.warning(
                f"Configured CEWE folder does not exist: {configuredCeweFolder}; "
                'trying automatic CEWE installation discovery instead.')
        configuredCeweFolder = findInstalledCeweFolder() or ''
        if configuredCeweFolder:
            mustsee.info(f'Automatically located CEWE folder: {configuredCeweFolder}')
        else:
            mustsee.warning(
                'Could not automatically locate the CEWE installation: '
                'continuing without CEWE resources.')
    if configuredCeweFolder:
        if os.path.isdir(configuredCeweFolder):
            ceweFolder = configuredCeweFolder
            CeweInfo.checkCeweFolder(ceweFolder)
            keyAccountNumber = CeweInfo.getKeyAccountNumber(ceweFolder, defaultConfigSection)
            CeweInfo.SetEnvironmentVariables(ceweFolder, keyAccountNumber)
            keyAccountFolder = CeweInfo.getKeyAccountDataFolder(keyAccountNumber, defaultConfigSection)
            backgroundLocations = CeweInfo.getBaseBackgroundLocations(ceweFolder, keyAccountFolder)
        else:
            logging.warning(
                f"Configured CEWE folder does not exist: {configuredCeweFolder}; "
                'continuing without CEWE resources.')
    else:
        logging.warning(
            "CEWE folder deliberately left unspecified: "
            'continuing without CEWE resources.')

    extraBackgroundFolders = defaultConfigSection.get('extraBackgroundFolders', '').splitlines()
    backgroundLocations += tuple(
        os.path.expandvars(folder) for folder in extraBackgroundFolders if folder)

    extraClipArts = defaultConfigSection.get('extraClipArts', '').splitlines()
    for extraClipArt in extraClipArts:
        if not extraClipArt:
            continue
        definition = os.path.expandvars(extraClipArt).split(',')
        if len(definition) == 2:
            clipartFiles[int(definition[0])] = definition[1].strip()

    configuredPassepartoutFolders = defaultConfigSection.get('passepartoutFolders', '').splitlines()
    if ceweFolder:
        configuredPassepartoutFolders.append(ceweFolder)
    passepartoutFolders = tuple(
        os.path.expandvars(folder) for folder in configuredPassepartoutFolders if folder)

    imageResolution = getConfigurationInt(defaultConfigSection, 'pdfImageResolution', '150', 100)
    backgroundResolution = getConfigurationInt(defaultConfigSection, 'pdfBackgroundResolution', '150', 100)

    mustsee.info(f'Using image resolution {imageResolution}, background resolution {backgroundResolution}')

    lineScales = LineScales(defaultConfigSection)
    if ceweFolder and keyAccountFolder is not None:
        passepartoutFolders += CeweInfo.getCewePassepartoutFolders(ceweFolder, keyAccountFolder)

    availableFonts = findAndRegisterFonts(defaultConfigSection, appDataDir, albumBaseFolder, ceweFolder, state)
    # Extra clipart file mappings work independently of the CEWE installation.
    # With no CEWE root this returns an empty delivered catalogue; a later
    # clipart lookup then uses its normal "not found" warning.
    clipartPaths = readClipArtConfigXML(ceweFolder, keyAccountFolder, clipartFiles)

    # Use names here rather than relying on ConversionSetup's declaration
    # order.  The dataclass is intentionally grouped for readability above,
    # and its fields should be freely rearrangeable without changing values.
    return ConversionSetup(
        key_account_folder=keyAccountFolder,
        configuration=configuration,
        default_config_section=defaultConfigSection,
        background_locations=backgroundLocations,
        clipart_files=clipartFiles,
        clipart_paths=clipartPaths,
        passepartout_folders=passepartoutFolders,
        mcf_xml_name=mcfxmlname,
        mcf_base_folder=mcfBaseFolder,
        unpacked_folder=unpackedFolder,
        album_base_folder=albumBaseFolder,
        fotobook=fotobook,
        album_title=albumTitle,
        available_fonts=availableFonts,
        line_scales=lineScales,
        image_resolution=imageResolution,
        background_resolution=backgroundResolution)
