import glob
import logging
import os.path
import os
import sys
from enum import Enum

import reportlab.lib.pagesizes
from reportlab.lib.units import mm

from lxml import etree
from infrastructure.extraLoggers import mustsee


class PdfProductStyle(Enum):
    AlbumSingleSide = 1  # normal for albums, we divide the cewe 2 page bundle to single pages
    AlbumDoubleSide = 2  # any album when --keepdoublepages is set
    MemoryCard = 3 # CEWE Photo Pairs memory-card game (product code MEM3)
    Calendar = 4 # CEWE wall calendars


class ProductInfo():
    def __init__(self):
        return

    # Fallback page sizes for product records without a ``bundlesize`` element.
    # A normal MCF supplies its actual page dimensions on every page, so these
    # product identifiers are not the source of truth for rendering.
    ceweFormats = {
        # These are internal-page dimensions.  Cover bundles are slightly
        # larger to allow for binding bleed.
        "ALB14": (205 * reportlab.lib.pagesizes.mm, 270 * reportlab.lib.pagesizes.mm),
        "ALB15": (205 * reportlab.lib.pagesizes.mm, 270 * reportlab.lib.pagesizes.mm),
        "ALB17": (205 * reportlab.lib.pagesizes.mm, 205 * reportlab.lib.pagesizes.mm),
        "ALB32": (300 * reportlab.lib.pagesizes.mm, 300 * reportlab.lib.pagesizes.mm),
        "ALB42": (382 * reportlab.lib.pagesizes.mm, 290 * reportlab.lib.pagesizes.mm),
        "ALB69": (270 * reportlab.lib.pagesizes.mm, 356 * reportlab.lib.pagesizes.mm),
        "ALB82": (205 * reportlab.lib.pagesizes.mm, 270 * reportlab.lib.pagesizes.mm),
        "ALB98": (205 * reportlab.lib.pagesizes.mm, 270 * reportlab.lib.pagesizes.mm),
        "ALB131": (148 * reportlab.lib.pagesizes.mm, 148 * reportlab.lib.pagesizes.mm),
        # add other page sizes here
        # MEM3 is CEWE Photo Pairs: one 6 x 6 cm card per MCF normal-page.
        # Its bundlesize normally supplies the same dimensions at render time;
        # this fallback matters only when that element is absent.
        "MEM3": (60 * reportlab.lib.pagesizes.mm, 60 * reportlab.lib.pagesizes.mm),
        "CAL9": reportlab.lib.pagesizes.A4,
        "CAL35": reportlab.lib.pagesizes.landscape(reportlab.lib.pagesizes.A4),
        "CAL99": (210 * reportlab.lib.pagesizes.mm, 210 * reportlab.lib.pagesizes.mm),
        "CAL55": reportlab.lib.pagesizes.landscape(reportlab.lib.pagesizes.A5)
        }

    # Product-ID fallbacks for MCFs whose page structure is incomplete or from
    # an older editor.  ``pdfStyleFromMcf`` normally derives Calendar directly
    # from calendar pages/areas, and also uses the CAL prefix as its calendar
    # fallback. Albums remain the default two-page product. MEM3 is retained
    # here because its independent-card structure has not yet been
    # generalised to all independent-page products.
    pdfStyles = {
        "MEM3": PdfProductStyle.MemoryCard # CEWE Photo Pairs: 6 x 6 cm memory cards
        }

    @staticmethod
    def pdfStyleFromMcf(fotobook):
        """Choose the PDF rendering style from MCF structure and ID fallbacks.

        The PDF style includes CEWE-spread handling, so an ordinary CEWE album
        becomes a single-sided PDF by default.  Calendar pages have a distinct
        structure: the cover is marked as a
        calendar cover and the monthly pages contain calendar areas.  That is
        more reliable than maintaining a list of retailer-specific calendar
        product identifiers.  The existing identifier table remains a
        compatibility fallback for incomplete or older MCFs.
        """
        productName = fotobook.get('productname', '')
        hasCalendarCover = any(
            (page.get('type') or '').casefold() == 'calendarcoverfront'
            for page in fotobook.findall('./page'))
        hasCalendarArea = any(
            (area.get('areatype') or '').casefold() == 'calendariumarea'
            for area in fotobook.findall('.//area'))
        if hasCalendarCover or hasCalendarArea:
            if not productName.upper().startswith('CAL'):
                mustsee.warning(
                    'Calendar structure detected for product %r, which does not '
                    'use a CAL product identifier; using calendar page rules.',
                    productName or '(missing)')
            return PdfProductStyle.Calendar
        if productName.upper().startswith('CAL'):
            mustsee.warning(
                'Product %r uses a CAL product identifier but has no calendar '
                'cover or calendar area; using the product-ID fallback.',
                productName)
            return PdfProductStyle.Calendar

        if productName.upper().startswith('ALB'):
            pageTypes = {
                (page.get('type') or '').casefold()
                for page in fotobook.findall('./page')}
            # CEWE's spine page is structural metadata.  The visible spine
            # artwork is stored in the composite fullcover page instead.
            expectedAlbumTypes = {'fullcover', 'spine', 'emptypage'}
            missingTypes = expectedAlbumTypes - pageTypes
            if missingTypes:
                mustsee.warning(
                    'Album product %r lacks expected %s page records; using '
                    'the generic album page rules.', productName,
                    ', '.join(sorted(missingTypes)))
        if productName in ProductInfo.pdfStyles:
            return ProductInfo.pdfStyles[productName]
        return PdfProductStyle.AlbumSingleSide

    @staticmethod
    def reportMcfProduct(fotobook, productStyle: PdfProductStyle):
        """Report the MCF product and its PDF page-size diagnostics.

        Product IDs are descriptive metadata, not the normal source of page
        dimensions or product style.  A known entry can nevertheless warn
        about a seriously unexpected bundle, which is useful evidence when
        CEWE changes an MCF format.
        """
        productName = fotobook.get('productname', '')
        knownProduct = (
            productName in ProductInfo.ceweFormats
            or productName in ProductInfo.pdfStyles)
        bundlesBySize = {}
        sizesByPageType = {}
        for page in fotobook.findall('./page'):
            bundleSize = page.find('./bundlesize')
            if bundleSize is None:
                continue
            bundle = (float(bundleSize.get('width')),
                      float(bundleSize.get('height')))
            pageType = (page.get('type') or '(missing)').casefold()
            bundlesBySize.setdefault(bundle, set()).add(pageType)
            sizesByPageType.setdefault(pageType, set()).add(bundle)
        if not bundlesBySize:
            mustsee.warning(
                'Product %s (%s) has no bundle size; using the fallback page '
                'dimensions.', productName or '(missing)',
                'known' if knownProduct else 'unknown')
            return

        pageWidthDivisor = 2 if ProductInfo.isAlbumSingleSide(productStyle) else 1
        for pageType, pageBundles in sorted(sizesByPageType.items()):
            if len(pageBundles) > 1:
                sizes = ', '.join(
                    f'{width / pageWidthDivisor / 10:.1f} × {height / 10:.1f} mm'
                    for width, height in sorted(pageBundles))
                mustsee.warning(
                    'Product %s uses multiple bundle sizes for %s pages: %s.',
                    productName or '(missing)', pageType, sizes)

        expectedSize = ProductInfo.ceweFormats.get(productName)
        expectedWidth = expectedHeight = None
        if expectedSize is not None:
            expectedWidth = expectedSize[0] / mm * 10
            expectedHeight = expectedSize[1] / mm * 10
            # ceweFormats holds one PDF-page width.  The normal album path
            # already halves the CEWE spread below; only --keepdoublepages
            # needs the expected width expanded to a spread.
            if ProductInfo.isAlbumDoubleSide(productStyle):
                expectedWidth *= 2

        bundleDescriptions = []
        sizeMismatch = False
        for (bundleWidth, bundleHeight), pageTypes in sorted(bundlesBySize.items()):
            pdfPageWidth = bundleWidth / pageWidthDivisor
            description = (
                f'{pdfPageWidth / 10:.1f} × {bundleHeight / 10:.1f} mm '
                f'({", ".join(sorted(pageTypes))}')
            if expectedSize is not None:
                widthDifference = (
                    (pdfPageWidth - expectedWidth) / expectedWidth * 100)
                heightDifference = (
                    (bundleHeight - expectedHeight) / expectedHeight * 100)
                if widthDifference or heightDifference:
                    description += (
                        f'; {widthDifference:+.2f}% width, '
                        f'{heightDifference:+.2f}% height')
                if abs(widthDifference) > 10 or abs(heightDifference) > 10:
                    sizeMismatch = True
            bundleDescriptions.append(description + ')')
        mustsee.info(
            'Product %s (%s; %s): %s.', productName or '(missing)',
            'known' if knownProduct else 'unknown', productStyle.name,
            '; '.join(bundleDescriptions))
        if sizeMismatch:
            mustsee.warning(
                'Product %s has a page bundle outside the 10%% tolerance for '
                'its known %.1f × %.1f mm format.', productName,
                expectedWidth / 10, expectedHeight / 10)

    @staticmethod
    def isAlbumProduct(ps: PdfProductStyle):
        return ps in (PdfProductStyle.AlbumSingleSide, PdfProductStyle.AlbumDoubleSide)

    @staticmethod
    def isAlbumSingleSide(ps: PdfProductStyle):
        return ps == PdfProductStyle.AlbumSingleSide

    @staticmethod
    def isAlbumDoubleSide(ps: PdfProductStyle):
        return ps == PdfProductStyle.AlbumDoubleSide


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
