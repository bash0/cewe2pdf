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

from versionInfo import getVersionInformationText

# Let a user identify an executable without loading image libraries or reading
# any album files.  argparse also knows about --version below for its help.
if __name__ == '__main__' and len(sys.argv) == 2 and sys.argv[1] == '--version':
    print(getVersionInformationText())
    sys.exit(0)

# These imports deliberately follow the lightweight --version exit above.  Do
# not move them before it: doing so would load image libraries merely to report
# a program version from a standalone executable.
# pylint: disable=wrong-import-position,wrong-import-order
import logging
import logging.config

import os.path
import os

import argparse  # to parse arguments

import reportlab.lib.pagesizes
# from reportlab.pdfbase.pdfmetrics import stringWidth as _stringWidth
# from reportlab.lib.styles import getSampleStyleSheet

import PIL

from packaging.version import parse as parse_version
from albumConversionSession import AlbumConversionSession
from pageElements import processElements
from windowsIntegration import (confirmInstallation, installWindowsIntegration,
                                isWindowsFrozenExecutable, showMessage,
                                uninstallWindowsIntegration)


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

# MCF coordinates are measured in 0.1 mm, while ReportLab uses points.
# Keep this conversion at the boundary: area-rendering modules receive it in
# RenderContext rather than each maintaining its own approximation.
mcf2rl = reportlab.lib.pagesizes.mm/10 # == 72/254, converts from mcf (unit=0.1mm) to reportlab (unit=inch/72)


def convertMcf(albumname, keepDoublePages: bool, pageNumbers=None, mcfxTmpDir=None,
               appDataDir=None, outputFileName=None, automaticWindows=False):
    """Convert one MCF or MCFX album while preserving the established API."""
    with AlbumConversionSession(
            albumname, keepDoublePages, pageNumbers, mcfxTmpDir, appDataDir,
            outputFileName, mcf2rl, image_quality, pil_antialias,
            automaticWindows) as session:
        return session.render(processElements)


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
    parser.add_argument('--version', action='version',
                        version=getVersionInformationText(),
                        help='Show version and build identification, then exit')
    parser.add_argument('--outFile', dest='outFile',
                        default=None,
                        help="The name of the output file, rather than the default <inputFile>.pdf")
    parser.add_argument('--install', action='store_true',
                        help='Windows executable: install an Explorer right-click command for MCF and MCFX files.')
    parser.add_argument('--uninstall', action='store_true',
                        help='Windows executable: remove the cewe2pdf Explorer right-click command.')
    # This is the command used by the Explorer menu.  It is intentionally not
    # advertised to normal command-line users because it enables Windows-only
    # defaults such as automatic CEWE discovery and system-font loading.
    parser.add_argument('--automatic', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('inputFile', type=str, nargs='?',
                        help='Just one mcf(x) input file must be specified')

    args = parser.parse_args()

    if args.install:
        if not isWindowsFrozenExecutable():
            parser.error('--install is available only from the Windows cewe2pdf executable.')
        try:
            installedPath = installWindowsIntegration()
        except OSError as exception:
            showMessage(f'Could not install cewe2pdf:\n{exception}', error=True)
            return False
        showMessage(
            f'cewe2pdf is installed at:\n{installedPath}\n\n'
            'Right-click an MCF or MCFX album and choose “Create PDF with cewe2pdf”.')
        return True

    if args.uninstall:
        if os.name != 'nt':
            parser.error('--uninstall is available only on Windows.')
        try:
            installedPath = uninstallWindowsIntegration()
        except OSError as exception:
            showMessage(f'Could not remove the cewe2pdf Explorer menu:\n{exception}', error=True)
            return False
        retainedText = f'\nThe executable remains at:\n{installedPath}' if installedPath else ''
        showMessage(f'The cewe2pdf Explorer menu was removed.{retainedText}')
        return True

    if args.automatic and os.name != 'nt':
        parser.error('--automatic is reserved for the Windows Explorer command.')

    if args.inputFile is None:
        if isWindowsFrozenExecutable():
            if confirmInstallation():
                try:
                    installedPath = installWindowsIntegration()
                except OSError as exception:
                    showMessage(f'Could not install cewe2pdf:\n{exception}', error=True)
                    return False
                showMessage(
                    f'cewe2pdf is installed at:\n{installedPath}\n\n'
                    'Right-click an MCF or MCFX album and choose “Create PDF with cewe2pdf”.')
                return True
            return False
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
    result = convertMcf(
        args.inputFile, args.keepDoublePages, pages, mcfxTmp, appData,
        outputFileName=outFile, automaticWindows=args.automatic)
    if args.automatic and result:
        outputName = outFile or os.path.abspath(args.inputFile + '.pdf')
        logName = os.path.abspath(args.inputFile + '.log')
        logText = f'\n\nConversion log:\n{logName}' if os.path.isfile(logName) else ''
        showMessage(f'Created PDF:\n{outputName}{logText}')
    return result


if __name__ == '__main__':
    # only executed when this file is run directly.
    # we need trick to have both: default and fixed formats.
    resultFlag = collectArgsAndConvert()
