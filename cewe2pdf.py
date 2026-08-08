#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# In this file it is permitted to catch exceptions on a broad basis since there
# are many things that can go wrong with file handling and xml parsing:
#    pylint: disable=bare-except,broad-except
# We're not quite at the level of documenting all the classes and functions yet :-)
#    pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring
# It'll be a while before we refactor this file, but when we do then these should be reenabled again!
#    pylint: disable=too-many-lines,too-many-statements,too-many-arguments,too-many-locals
#    pylint: disable=too-many-nested-blocks,too-many-branches
# logging strings, we don't log enough to worry about lazy evaluation
#    pylint: enable=logging-format-interpolation,logging-not-lazy

'''
Create pdf files from CEWE .mcf photo books (cewe-fotobuch)
version 0.11 (Dec 2019)

This script reads CEWE .mcf and .mcfx files using the lxml library
and compiles a pdf file using the reportlab python pdf library.
Execute from same path as .mcf file!

Only basic elements such as images and text are supported.
The feature support is neither complete nor fully correct.
Results may be wrong, incomplete or not produced at all.
This script doesn't work according to the original format
specification but according to estimated meaning.
Feel free to improve!

The script was tested to run with A4 books from CEWE
tested
dm-Fotowelt: compatibilityVersion="6.4.2" programversion="7.0.1" programversionBuild="20191025"

documentations:
-reportlab: www.reportlab.com/software/opensource/
-lxml: http://lxml.de/tutorial.html
-PIL: http://effbot.org/imagingbook/image.htm

--

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


# extend the search path so Cairo will find its dlls.
# only needed when the program is frozen (i.e. compiled).
import sys

import logging
import logging.config

import os.path
import os

import gc

import argparse  # to parse arguments
import configparser  # to read config file, see https://docs.python.org/3/library/configparser.html

from math import floor

from pathlib import Path
import reportlab.lib.pagesizes
from reportlab.pdfgen import canvas
# from reportlab.pdfbase.pdfmetrics import stringWidth as _stringWidth
# from reportlab.lib.styles import getSampleStyleSheet

import PIL

from packaging.version import parse as parse_version
from lxml import etree

from ceweInfo import CeweInfo, AlbumInfo, ProductStyle
from borders import processDecorationBorders
from clipArt import readClipArtConfigXML
from clipartareas import processAreaClipartTag
from configUtils import getConfigurationBool, getConfigurationInt
from extraLoggers import mustsee, VerifyMessageCounts, printMessageCountSummaries
from fontHandling import findAndRegisterFonts
from imageareas import processAreaImageTag
from lineScales import LineScales
from mcfx import unpackMcfx
from pageNumbering import PageNumberingInfo
from pageTypes import PageProcessingType
from pages import getPageElementForPageNumber, processPages
from pathutils import findFileInDirs
from renderContext import RenderContext
from textareas import processAreaTextTag
from index import Index
from shadows import processDecorationShadow


# work around a breaking change in pil 10.0.0, see
#   https://stackoverflow.com/questions/76616042/attributeerror-module-pil-image-has-no-attribute-antialias
if parse_version(PIL.__version__) >= parse_version('9.1.0'):
    # PIL.Image.LANCZOS was claimed closer to the old ANTIALIAS than PIL.Image.Resampling.LANCZOS
    # although you can find text which claims the latter is best (and also that the two LANCZOS
    # definitions are in fact identical!)
    pil_antialias = PIL.Image.LANCZOS  # pylint: disable=no-member
else:
    pil_antialias = PIL.Image.ANTIALIAS  # pylint: disable=no-member

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Running in a PyInstaller bundle, ref https://pyinstaller.org/en/stable/runtime-information.html#run-time-information
    # Add the local directory to the PATH. This is needed for compiled (i.e. frozen)
    #  programs on Windows to find dlls (cairo dlls, in particular).
    realpath = os.path.realpath(sys.argv[0])
    exename = os.path.basename(realpath)
    dllpath = os.path.dirname(realpath)
    print(f"Frozen python {exename} running from {dllpath}")
    if dllpath not in os.environ["PATH"]:
        print(f"Adding {dllpath} to PATH")
        if not os.environ["PATH"].endswith(os.pathsep):
            os.environ["PATH"] += os.pathsep
        os.environ["PATH"] += dllpath

# make it possible for PIL.Image to open .heic files if the album editor stores them directly
# ref https://github.com/bash0/cewe2pdf/issues/130
try:
    from pillow_heif import register_heif_opener # the absence of heif handling is handled so pylint: disable=import-error
    register_heif_opener()
except ModuleNotFoundError as heifex:
    logging.warning(f"{heifex.msg}: direct use of .heic images is not available without pillow_heif available")

# ### settings ####
image_res = 150  # dpi  The resolution of normal images will be reduced to this value, if it is higher.
bg_res = 150  # dpi The resolution of background images will be reduced to this value, if it is higher.
image_quality = 86  # 0=worst, 100=best. This is the JPEG quality option.
# ##########

# .mcf units are 0.1 mm
# Tabs seem to be in 8mm pitch
tab_pitch = 80

mcf2rl = reportlab.lib.pagesizes.mm/10 # == 72/254, converts from mcf (unit=0.1mm) to reportlab (unit=inch/72)

tempFileList = []  # we need to remove all the temporary files at the end

# reportlab defaults
# pdf_styles = getSampleStyleSheet()
# pdf_styleN = pdf_styles['Normal']

albumIndex = None # set after we have got the configuration information
clipartDict = dict[int, str]()    # a dictionary for clipart element IDs to file name
clipartPathList = tuple[str]()
defaultConfigSection = None


# Note that transCx, transCy are the center of the area
def processElements(additional_fonts, fotobook, imagedir,
                    productstyle, mcfBaseFolder, oddpage, page, pageNumber, pagetype, pdf, pageH, pageW,
                    lastpage, context: RenderContext):
    if AlbumInfo.isAlbumDoubleSide(productstyle) and pagetype == PageProcessingType.RegularPage and not oddpage and not lastpage:
        # if we are in double-page mode, all the images are drawn by the odd pages.
        return

    # the mcf file really comes in "bundles" of two pages, so for odd pages we switch back to
    # the page element for the preceding even page to get the elements
    if AlbumInfo.isAlbumProduct(productstyle) and pagetype == PageProcessingType.RegularPage and oddpage:
        page = getPageElementForPageNumber(fotobook, 2*floor(pageNumber/2))

    for area in page.findall('area'):
        areaPos = area.find('position')
        areaLeft = float(areaPos.get('left').replace(',', '.'))
        if pagetype != PageProcessingType.FrontInsideCoverBackground or len(area.findall('imagebackground')) == 0:
            if oddpage and AlbumInfo.isAlbumSingleSide(productstyle):
                # shift double-page content from other page
                areaLeft -= pageW
        areaTop = float(areaPos.get('top').replace(',', '.'))
        areaWidth = float(areaPos.get('width').replace(',', '.'))
        areaHeight = float(areaPos.get('height').replace(',', '.'))
        areaRot = float(areaPos.get('rotation'))

        # check if the image is on current page at all, and if not then skip processing it
        if AlbumInfo.isAlbumSingleSide(productstyle) and pagetype in [PageProcessingType.RegularPage, PageProcessingType.Cover]:
            if oddpage:
                # the right edge of image is beyond the left page border
                if (areaLeft+areaWidth) < 0:
                    continue
            else:
                if areaLeft > pageW:  # the left image edge is beyond the right page border.
                    continue

        # center positions
        cx = areaLeft + 0.5 * areaWidth
        cy = pageH - (areaTop + 0.5 * areaHeight)

        transCx = mcf2rl * cx
        transCy = mcf2rl * cy

        # process images
        for imageTag in area.findall('imagebackground') + area.findall('image'):
            processAreaImageTag(imageTag, area, areaHeight, areaRot, areaWidth, imagedir, productstyle,
                                mcfBaseFolder, pagetype, pdf, pageW, transCx, transCy, context,
                                processDecorationShadow, processDecorationBorders)

        # process text
        for textTag in area.findall('text'):
            processAreaTextTag(textTag, additional_fonts, area, areaWidth, areaHeight, areaRot, pdf, transCx, transCy,
                               pageNumber, context)

        # Clip-Art
        # In the clipartarea there are two similar elements, the <designElementIDs> and the <clipart>.
        # We are using the <clipart> element here
        if area.get('areatype') == 'clipartarea':
            # within clipartarea tags we need the decoration for alpha and border information
            decoration = area.find('decoration')
            for clipartElement in area.findall('clipart'):
                processAreaClipartTag(clipartElement, areaHeight, areaRot, areaWidth, pdf, transCx, transCy,
                                      decoration, context,
                                      lambda decoration, height, width, canvas:
                                      processDecorationBorders(decoration, height, width, canvas, context))
    return

def convertMcf(albumname, keepDoublePages: bool, pageNumbers=None, mcfxTmpDir=None, appDataDir=None, outputFileName=None): # noqa: C901 (too complex)
    global clipartDict  # pylint: disable=global-statement
    global clipartPathList  # pylint: disable=global-statement
    global image_res  # pylint: disable=global-statement
    global bg_res  # pylint: disable=global-statement
    global defaultConfigSection  # pylint: disable=global-statement
    global albumIndex  # pylint: disable=global-statement

    clipartDict = {}    # a dictionary for clipart element IDs to file name
    clipartPathList = tuple()
    passepartoutFolders = tuple[str]()
    pageNumberingInfo = None

    albumTitle, dummy = os.path.splitext(os.path.basename(albumname))

    # check for new format (version 7.3.?, ca 2023, issue https://github.com/bash0/cewe2pdf/issues/119)
    mcfxFormat = albumname.endswith(".mcfx")
    if mcfxFormat:
        albumPathObj = Path(albumname).resolve()
        unpackedFolder, mcfxmlname = unpackMcfx(albumPathObj, mcfxTmpDir)
    else:
        unpackedFolder = None
        mcfxmlname = albumname

    # we'll need the album folder to find config files
    albumBaseFolder = str(Path(albumname).resolve().parent)

    # we'll need the mcf folder to find mcf relative image file names
    mcfPathObj = Path(mcfxmlname).resolve()
    mcfBaseFolder = str(mcfPathObj.parent)

    # parse the input mcf xml file
    # read file as binary, so UTF-8 encoding is preserved for xml-parser
    try:
        with open(mcfxmlname, 'rb') as mcffile:
            mcf = etree.parse(mcffile)
    except Exception as e:
        invalidmsg = f"Cannot open mcf file {mcfxmlname}"
        if mcfxFormat:
            invalidmsg = invalidmsg + f" (unpacked from {albumname})"
        invalidmsg = invalidmsg + f": {repr(e)}"
        logging.error(invalidmsg)
        sys.exit(1)

    fotobook = mcf.getroot()
    CeweInfo.ensureAcceptableAlbumMcf(fotobook, albumname, mcfxmlname, mcfxFormat)

    # check output file is acceptable before we do any processing, which is
    # preferable to processing for a long time and *then* discovering that
    # the file is not writable
    if outputFileName is None:
        outputFileName = CeweInfo.getOutputFileName(albumname)
    CeweInfo.ensureAcceptableOutputFile(outputFileName)

    # a null default configuration section means that some capabilities will be missing!
    defaultConfigSection = None
    # find cewe folder using the original cewe_folder.txt file
    try:
        configFolderFileName = findFileInDirs('cewe_folder.txt', (albumBaseFolder, os.path.curdir, os.path.dirname(os.path.realpath(__file__))))
        with open(configFolderFileName, 'r') as cewe_file:  # this works on all relevant platforms so pylint: disable=unspecified-encoding
            cewe_folder = cewe_file.read().strip()
            CeweInfo.checkCeweFolder(cewe_folder)
            keyAccountNumber = CeweInfo.getKeyAccountNumber(cewe_folder)
            keyAccountFolder = CeweInfo.getKeyAccountDataFolder(keyAccountNumber)
            backgroundLocations = CeweInfo.getBaseBackgroundLocations(cewe_folder, keyAccountFolder)

    except: # noqa: E722
        # arrives here if the original cewe_folder.txt file is missing, which we really expect it to be these days.
        logging.info('Trying cewe2pdf.ini from current directory and from the album directory.')
        configuration = configparser.ConfigParser()
        # Try to read the .ini first from the current directory, and second from the directory where the .mcf file is.
        # Order of the files is important, because config entires are
        #  overwritten when they appear in the later config files.
        # We want the config file in the .mcf directory to be the most important file.
        filesread = configuration.read(['cewe2pdf.ini', os.path.join(albumBaseFolder, 'cewe2pdf.ini')])
        if len(filesread) < 1:
            logging.error('You must create cewe_folder.txt or cewe2pdf.ini to specify the cewe_folder')
            sys.exit(1)
        else:
            # Give the user feedback which config-file is used, in case there is a problem.
            mustsee.info(f'Using configuration files, in order: {str(filesread)}')
            defaultConfigSection = configuration['DEFAULT']
            # find cewe folder from ini file
            if 'cewe_folder' not in defaultConfigSection:
                logging.error('You must create cewe_folder.txt or modify cewe2pdf.ini to define cewe_folder')
                sys.exit(1)

            cewe_folder = defaultConfigSection['cewe_folder'].strip()
            CeweInfo.checkCeweFolder(cewe_folder)

            keyAccountNumber = CeweInfo.getKeyAccountNumber(cewe_folder, defaultConfigSection)

            # set the cewe folder and key account number into the environment for later use in the config files
            CeweInfo.SetEnvironmentVariables(cewe_folder, keyAccountNumber)

            keyAccountFolder = CeweInfo.getKeyAccountDataFolder(keyAccountNumber, defaultConfigSection)

            baseBackgroundLocations = CeweInfo.getBaseBackgroundLocations(cewe_folder, keyAccountFolder)

            # add any extra background folders, substituting environment variables
            xbg = defaultConfigSection.get('extraBackgroundFolders', '').splitlines()  # newline separated list of folders
            fxbg = list(filter(lambda bg: (len(bg) != 0), xbg)) # filter out empty entries
            f2xbg = tuple(map(lambda bg: os.path.expandvars(bg), fxbg)) # expand environment vars pylint: disable=unnecessary-lambda
            backgroundLocations = baseBackgroundLocations + f2xbg

            # adds extra clipart ids, with absolute file references
            xca = defaultConfigSection.get('extraClipArts', '').splitlines()  # newline separated list of id, filename pairs
            fxca = list(filter(lambda ca: (len(ca) != 0), xca)) # filter out empty entries
            f2xca = tuple(map(lambda ca: os.path.expandvars(ca), fxca)) # expand environment vars pylint: disable=unnecessary-lambda
            for ca in f2xca:
                definition = ca.split(',')
                if len(definition) == 2:
                    clipartId = int(definition[0])
                    file = definition[1].strip()
                    clipartDict[clipartId] = file

            # read passepartout folders and substitute environment variables
            pptout_rawFolder = defaultConfigSection.get('passepartoutFolders', '').splitlines()  # newline separated list of folders
            pptout_rawFolder.append(cewe_folder)    # add the base folder
            pptout_filtered1 = list(filter(lambda bg: (len(bg) != 0), pptout_rawFolder)) # filter out empty entries
            pptout_filtered2 = tuple(map(lambda bg: os.path.expandvars(bg), pptout_filtered1)) # expand environment vars pylint: disable=unnecessary-lambda
            passepartoutFolders = pptout_filtered2

            # read resolution options
            image_res = getConfigurationInt(defaultConfigSection, 'pdfImageResolution', '150', 100)
            bg_res = getConfigurationInt(defaultConfigSection, 'pdfBackgroundResolution', '150', 100)

    mustsee.info(f'Using image resolution {image_res}, background resolution {bg_res}')

    # See if there is a configured default line scale overriding the coded default.
    # This global default line scale may be reconfigured per font, after font registration
    # is complete, into the fontLineScales mapping
    LineScales.setupDefaultLineScale(defaultConfigSection)

    if keyAccountFolder is not None:
        passepartoutFolders = passepartoutFolders + CeweInfo.getCewePassepartoutFolders(cewe_folder, keyAccountFolder)

    bg_notFoundDirList = set([]) # keep a list of background folders that are not found, to prevent multiple errors for the same cause.

    try:
        albumIndex = Index(configuration['INDEX'])
    except KeyError:
        albumIndex = Index(None)

    # Load fonts
    availableFonts = findAndRegisterFonts(defaultConfigSection, appDataDir, albumBaseFolder, cewe_folder)

    # Read any configured non-standard line scales for specified fonts, creating a map of font name to line scale
    LineScales.setupFontLineScales(defaultConfigSection)

    # extract basic album properties
    articleConfigElement = fotobook.find('articleConfig')
    if articleConfigElement is None:
        logging.error(f'{albumname} is an old version. Open it in the album editor and save before retrying the pdf conversion. Exiting.')
        sys.exit(1)

    pageCount = int(articleConfigElement.get('normalpages')) + 2
    # The normalpages attribute in the mcf is the number of "usable" inside pages, excluding the front and back covers and the blank inside
    #  cover pages. Add 2 so that pagecount represents the actual number of printed pdf pages we expect in the normal single sided
    #  pdf print (a basic album is 26 inside pages, plus front and back cover, i.e. 28). If we use keepDoublePages, then we'll
    #  actually be producing 2 more (the inside covers) but halving the number of final output pdf pages, making 15 double pages.
    # There is also a totalpages attribute in the mcf, but in my files it is 5 more than the normalpages value. Why not 4 more? I
    #  guess that may be because it is a count of the <page> elements and not actually related to the number of printed pages.
    imageFolder = fotobook.get('imagedir')

    # generate a list of available clip-arts
    clipartPathList = readClipArtConfigXML(cewe_folder, keyAccountFolder, clipartDict)
    renderContext = RenderContext(mcf2rl, image_res, image_quality, bg_res, pil_antialias,
                                  defaultConfigSection, clipartDict, clipartPathList,
                                  None, passepartoutFolders, tempFileList)

    # find the correct size for the album format (if we know!) and set the product style
    pagesize = reportlab.lib.pagesizes.A4
    productstyle = ProductStyle.AlbumSingleSide
    productname = fotobook.get('productname')
    if productname in AlbumInfo.formats: # IMO this is clearest so pylint: disable=consider-using-get
        pagesize = AlbumInfo.formats[productname]
    if productname in AlbumInfo.styles: # IMO this is clearest so pylint: disable=consider-using-get
        productstyle = AlbumInfo.styles[productname]
    if keepDoublePages:
        if productstyle == ProductStyle.AlbumSingleSide:
            productstyle = ProductStyle.AlbumDoubleSide
        elif productstyle == ProductStyle.MemoryCard:
            logging.warning('keepdoublepages option is irrelevant and ignored for a memory card product')

    # initialize a pdf canvas
    pdf = canvas.Canvas(outputFileName, pagesize=pagesize)
    pdf.setTitle(albumTitle)

    pageNumberElement = fotobook.find('pagenumbering')
    if pageNumberElement is not None:
        pnpos = int(pageNumberElement.get('position'))
        if pnpos != 0: # 0 implies no numbering
            # make a page number description object to use later
            pageNumberingInfo = PageNumberingInfo(pageNumberElement, pdf, availableFonts)
    renderContext.page_numbering_info = pageNumberingInfo
    renderContext.album_index = albumIndex

    # generate all the requested pages
    processPages(fotobook, mcfBaseFolder, imageFolder, productstyle, pdf, pageCount, pageNumbers,
        cewe_folder, availableFonts, backgroundLocations, bg_notFoundDirList, renderContext,
        processElements)

    # save final output pdf
    try:
        pdf.save()
    except Exception as ex:
        logging.error(f'Could not save the output file: {str(ex)}')

    pdf = []

    if albumIndex.indexing:
        # At this point we have an index of items (selected on the basis of their font characteristics)
        #   albumIndex.ShowIndex()
        indexPdfFileName = albumIndex.SaveIndexPdf(outputFileName, albumTitle, pagesize)
        indexPngFileName = albumIndex.SaveIndexPng(indexPdfFileName)
        albumIndex.MergeAlbumAndIndexPng(outputFileName, indexPngFileName)
        # most usual is to delete the index pdf, but leave the index png which could be added
        # to the original with the cewe editor, and then you get it in the printed edition as well
        if albumIndex.deleteIndexPdf and os.path.exists(indexPdfFileName):
            os.remove(indexPdfFileName)
        if albumIndex.deleteIndexPng and os.path.exists(indexPngFileName):
            os.remove(indexPngFileName)

    # force the release of objects which might be holding on to picture file references
    # so that they will not prevent the removal of the files as we clean up and exit
    objectscollected = gc.collect()
    logging.info(f'GC collected objects : {objectscollected}')

    printMessageCountSummaries()

    if productstyle == ProductStyle.MemoryCard:
        print()
        print("Use Adobe Acrobat to print the memory cards. Set custom pages per sheet, 4 wide x 6 down")
        print(" and print two copies!")

    VerifyMessageCounts(defaultConfigSection)

    cleanUpTempFiles(tempFileList, unpackedFolder)

    return True

def collectArgsAndConvert():
    class CustomArgFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass

    epilogText = "Example:\n   python cewe2pdf.py"
    exampleFile = r"c:\path\to\my\files\my_nice_fotobook.mcf"
    parser = argparse.ArgumentParser(description='Convert a photo-book from .mcf/.mcfx file format to .pdf',
                                     epilog=f"{epilogText} {exampleFile}\n \n",
                                     formatter_class=CustomArgFormatter)
    parser.add_argument('--keepDoublePages', dest='keepDoublePages', action='store_const',
                        const=True, default=False,
                        help='Each page in the .pdf will be a double-sided page, instead of a normal single page.')
    parser.add_argument('--pages', dest='pages', action='store',
        default=None,
        help='Page numbers to render, e.g. 1,2,4-9 (default: None, which of course processes all the pages). '
            'These refer to the inside page numbers as you see them in the album editor - the first user editable inside page is number 1. '
            'If you want the front cover, then ask for page 0. Asking for the back cover explicitly will not work!')
    parser.add_argument('--tmp-dir', dest='mcfxTmp', action='store',
                        default=None,
                        help='Directory for .mcfx file extraction')
    parser.add_argument('--appdata-dir', dest='appData',
                        default=None,
                        help='Directory for persistent app data, eg ttf fonts converted from otf fonts')
    parser.add_argument('--outFile', dest='outFile',
                        default=None,
                        help="The name of the output file, rather than the default <inputFile>.pdf")
    parser.add_argument('inputFile', type=str, nargs='?',
                        help='Just one mcf(x) input file must be specified')

    args = parser.parse_args()

    if args.inputFile is None:
        # from July 2024 you must specify a file name. Check if there are any obvious candidates
        # which we could use in an example text
        fnames = [i for i in os.listdir(os.curdir) if os.path.isfile(i) and (i.endswith('.mcf') or i.endswith('.mcfx'))]
        if len(fnames) >= 1:
            # There is one or more mcf(x) file! Show him how to specify the first such file as an example.
            exampleFile = os.path.join(os.getcwd(), fnames[0])
            if ' ' in exampleFile:
                exampleFile = f'\"{exampleFile}\"'
            parser.epilog = f"{epilogText} {exampleFile}\n \n"
        parser.parse_args(['-h'])
        sys.exit(1)

    pages = None
    if args.pages is not None:
        pages = []
        for expr in args.pages.split(','):
            expr = expr.strip()
            if expr.isnumeric():
                pages.append(int(expr)) # simple number "23"
            elif expr.find('-') > -1:
                # page range: 23-42
                fromTo = expr.split('-', 2)
                if not fromTo[0].isnumeric() or not fromTo[1].isnumeric():
                    logging.error(f'Invalid page range: {expr}')
                    sys.exit(1)
                pageFrom = int(fromTo[0])
                pageTo = int(fromTo[1])
                if pageTo < pageFrom:
                    logging.error(f'Invalid page range: {expr}')
                    sys.exit(1)
                pages = pages + list(range(pageFrom, pageTo + 1))
            else:
                logging.error(f'Invalid page number: {expr}')
                sys.exit(1)

    mcfxTmp = None
    if args.mcfxTmp is not None:
        mcfxTmp = os.path.abspath(args.mcfxTmp)

    appData = None
    if args.appData is not None:
        appData = os.path.abspath(args.appData)

    outFile = None
    if args.outFile is not None:
        outFile = os.path.abspath(args.outFile)

    # convert the file
    return convertMcf(args.inputFile, args.keepDoublePages, pages, mcfxTmp, appData, outputFileName=outFile)


def cleanUpTempFiles(fileList, unpackedFolder):
    for tmpFileName in fileList:
        if os.path.exists(tmpFileName):
            os.remove(tmpFileName)
    if unpackedFolder is not None:
        unpackedFolder.cleanup()


if __name__ == '__main__':
    # only executed when this file is run directly.
    # we need trick to have both: default and fixed formats.
    resultFlag = collectArgsAndConvert()
