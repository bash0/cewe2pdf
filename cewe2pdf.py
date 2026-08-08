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
import html
import re # to merge duplicate style tags

import gc

import argparse  # to parse arguments
import configparser  # to read config file, see https://docs.python.org/3/library/configparser.html

from io import BytesIO
from math import floor

from pathlib import Path
from typing import Any

import reportlab.lib.colors
import reportlab.lib.pagesizes
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.pdfmetrics import stringWidth as _stringWidth
from reportlab.platypus import Table
from reportlab.lib.styles import ParagraphStyle
# from reportlab.lib.styles import getSampleStyleSheet

import PIL

from packaging.version import parse as parse_version
from lxml import etree

from ceweInfo import CeweInfo, AlbumInfo, ProductStyle
from borders import processDecorationBorders
from clipArt import readClipArtConfigXML
from clipartareas import processAreaClipartTag
from colorFrame import ColorFrame
from colorUtils import ReorderColorBytesMcf2Rl
from corners import applyCornerMask, buildCornerPath, getCornersInfo, hasImplementedCorners
from configUtils import getConfigurationBool, getConfigurationInt
from extraLoggers import mustsee, VerifyMessageCounts, printMessageCountSummaries
from fontHandling import getAvailableFont, findAndRegisterFonts
from imageareas import processAreaImageTag
from lineScales import LineScales
from mcfx import unpackMcfx
from pageNumbering import PageNumberingInfo
from pageTypes import PageProcessingType
from pages import getPageElementForPageNumber, processPages
from pathutils import findFileInDirs
from renderContext import RenderContext
from text import AppendItemTextInStyle, AppendSpanEnd, AppendSpanStart, AppendText
from text import CollectFontInfo, CollectItemFontFamily, CreateParagraphStyle, Dequote, LeadingForExplicitLineHeight
from textoutlines import TextEffectsParagraph, getTextOutline
from textspacing import getLetterSpacing
from index import Index
from textart import handleTextArt
from shadows import processDecorationShadow, warnAndIgnoreEnabledDecorationShadow


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


# This is only used for the <background .../> tags. The stock backgrounds use this element.
# Note that transCx, transCy are the center of the area
def processAreaTextTag(textTag, additional_fonts, area, areaWidth, areaHeight, areaRot, pdf, transCx, transCy,
                       pgno, context: RenderContext): # noqa: C901 (too complex)
    # note: it would be better to use proper html processing here

    def extract_text_sections(fragment, sep=" / "):
        from lxml.html import fromstring # local import avoids conflict pylint: disable=import-outside-toplevel
        tree = fromstring(fragment)
        # Collect each text node as a separate chunk, thus abandoning all the "markup" and
        # hopefully making it easier for the user to recognise the text from his album
        chunks = [t.strip() for t in tree.itertext() if t.strip()]
        return sep.join(chunks)

    def WarnHeightProblem(recentParagraphText, originalFrameHeight, expandedFrameHeight, finalTotalHeight):
        originalFrameHeightMm = originalFrameHeight / reportlab.lib.pagesizes.mm
        expandedFrameHeightMm = expandedFrameHeight / reportlab.lib.pagesizes.mm
        finalTotalHeightMm = finalTotalHeight / reportlab.lib.pagesizes.mm
        heightIncreasePercent = 100 * (expandedFrameHeight - originalFrameHeight) / originalFrameHeight
        logging.warning(
            f"""Text would not fit inside its {originalFrameHeightMm:.2f} mm frame after shrinking the font to {scaleFactor:.1%}.
                Most recent paragraph text: {extract_text_sections(recentParagraphText)}
                The frame height has been increased to {expandedFrameHeightMm:.2f} mm ({heightIncreasePercent:.1f}%) for this run.
                Text in the unshrunk font needs {finalTotalHeightMm:.2f} mm.""")

    # Process each opening tag, merging duplicate style attributes
    def merge_duplicate_styles(match):
        """Merge duplicate style attributes in a single tag."""
        full_tag = match.group(0)  # e.g., '<li style="..." style="...">'

        # Find all style="..." attributes in this specific tag
        style_pattern = r'style="([^"]*)"'
        styles: list[Any] = re.findall(style_pattern, full_tag)

        if len(styles) <= 1:
            # No duplicates, return unchanged
            return full_tag

        # Log warning about duplicate styles with context
        # Extract tag name for context
        tag_name_match: re.Match[str] | None = re.match(r'<(\w+)', full_tag)
        tag_name: str | Any = tag_name_match.group(1) if tag_name_match else 'unknown'

        # Get position of this tag in the original text to show nearby text content
        tag_pos = textTag.text.find(full_tag)
        if tag_pos >= 0:
            # Find some actual text content near this tag (not HTML tags)
            # Look ahead after this tag for text content
            search_start = tag_pos + len(full_tag)
            search_end = min(len(textTag.text), search_start + 200)
            nearby = textTag.text[search_start:search_end]
            # Extract text between tags
            text_content = re.sub(r'<[^>]*>', '', nearby)[:20].strip()
            context = f"near text: '{text_content}'" if text_content else "at start/end"
        else:
            context = ""

        logging.warning(f"Merging duplicate 'style' attributes in <{tag_name}> tag ({len(styles)} instances) {context}")
        logging.warning(f"  Styles: {styles}")

        # Merge all style values
        merged_parts = []
        for s in styles:
            s = s.strip()
            if s:
                # Ensure ends with semicolon for proper CSS
                if not s.endswith(';'):
                    s += ';'
                merged_parts.append(s)
        merged_style = ' '.join(merged_parts).strip()

        # Replace: keep first style="..." and remove all subsequent ones
        # First, remove ALL style attributes
        tag_without_styles = re.sub(style_pattern, '', full_tag)

        # Then add the merged style back as the first attribute
        # Find position after tag name to insert style
        tag_name_match: re.Match[str] | None = re.match(r'(<\w+)(\s|>)', tag_without_styles)
        if tag_name_match:
            prefix: str | Any = tag_name_match.group(1)  # e.g., '<li'
            rest = tag_without_styles[len(prefix):]  # everything after tag name
            return f'{prefix} style="{merged_style}"{rest}'

        # Fallback: shouldn't reach here, but return original if parsing fails
        return full_tag

    # Preprocess text to fix CEWE bugs: merge duplicate style attributes
    # CEWE sometimes generates invalid XML like: <li style="..." style="...">
    # We need to merge these into a single style attribute
    text_content = re.sub(r'<\w+[^>]*>', merge_duplicate_styles, textTag.text)

    # Validate that we haven't lost any actual text content
    # Strip all style then HTML tags and compare character counts
    orig_no_style = re.sub(r'<style[^>]*>.*?</style>', '', textTag.text, flags=re.DOTALL)
    original_text_only = re.sub(r'<[^>]+>', '', orig_no_style)
    processed_text_only_no_style = re.sub(r'<style[^>]*>.*?</style>', '', text_content, flags=re.DOTALL)
    processed_text_only = re.sub(r'<[^>]+>', '', processed_text_only_no_style)

    if len(original_text_only) != len(processed_text_only):
        logging.error("=" * 80)
        logging.error("PREPROCESSING VALIDATION FAILED: Text content length changed!")
        logging.error(f"Original text-only length: {len(original_text_only)}")
        logging.error(f"Processed text-only length: {len(processed_text_only)}")
        logging.error(f"Difference: {len(processed_text_only) - len(original_text_only)} characters")
        logging.error("-" * 80)
        logging.error("Original text-only content:")
        logging.error(original_text_only)
        logging.error("-" * 80)
        logging.error("Processed text-only content:")
        logging.error(processed_text_only)
        logging.error("=" * 80)
        raise ValueError("Text preprocessing corrupted content - text length mismatch")

    try:
        htmlxml = etree.XML(text_content)
        # Log what we successfully parsed
        body = htmlxml.find('.//body')
        if body is not None:
            # Log all direct children of body to see structure
            body_children = list(body)
        else:
            logging.warning("No <body> tag found in parsed HTML!")
    except etree.XMLSyntaxError as e:
        # Log detailed error information for debugging XML parsing issues
        logging.error("=" * 80)
        logging.error("XML PARSING ERROR in text area")
        logging.error(f"Error: {e}")
        logging.error(f"Original text content ({len(textTag.text)} characters):")
        logging.error(textTag.text)
        logging.error("-" * 80)
        logging.error(f"Preprocessed text content ({len(text_content)} characters):")
        logging.error(text_content)
        logging.error("-" * 80)

        # Try to highlight the problematic portion based on column number
        if hasattr(e, 'position') and e.position: # pylint: disable=unsubscriptable-object
            col = e.position[1] if len(e.position) > 1 else None
        else:
            # Try to extract column from error message (e.g., "column 3838")
            match = re.search(r'column (\d+)', str(e))
            col = int(match.group(1)) if match else None

        if col is not None:
            # Show context around the error (30 chars before and after)
            start = max(0, col - 30)
            end = min(len(text_content), col + 30)
            context = text_content[start:end]
            marker_pos = min(30, col - start)

            logging.error(f"Context around column {col} in preprocessed text:")
            logging.error(f"  {context}")
            logging.error(f"  {' ' * marker_pos}^ (error position)")

        logging.error("=" * 80)
        # Re-throw the error for now
        raise

    body = htmlxml.find('.//body')
    bstyle = dict([kv.split(':') for kv in body.get('style').lstrip(' ').rstrip(';').split('; ')])
    try:
        bodyfs = floor(float(bstyle['font-size'].strip("pt")))
    except: # noqa: E722
        bodyfs = 12
    family = bstyle['font-family'].strip("'")
    bodyfont = getAvailableFont(family, pdf, additional_fonts)

    try:
        bweight = int(Dequote(bstyle['font-weight']))
    except: # noqa: E722
        bweight = 400

    # from about CEWE 8.0, approx late 2025, the textFormat element has become important
    textFormatElement = textTag.find('textFormat')
    textOutline = getTextOutline(textTag, mcf2rl)
    letterSpacing = getLetterSpacing(textFormatElement, mcf2rl)
    indentMargin = -1.0

    # issue https://github.com/bash0/cewe2pdf/issues/58 - margins are not being used
    # assume (based on empirical evidence!) that there is just one table, and collect
    # the margin values. This "table" code will no longer be used in an mcf created with the
    # CEWE 8.0 software, because the margin values have been moved to the textFormat element, but
    # it is still needed for MCFs created with CEWE 7.0 and earlier, so we keep it in place.
    tabletmarg = tablebmarg = tablelmarg = tablermarg = 0
    table = htmlxml.find('.//body/table')
    if table is not None:
        tableStyleAttrib = table.get('style')
        if tableStyleAttrib is not None:
            tablestyle = dict([kv.split(':') for kv in
                table.get('style').lstrip(' ').rstrip(';').split('; ')])
            try:
                tabletmarg = floor(float(tablestyle['margin-top'].strip("px")))
                tablebmarg = floor(float(tablestyle['margin-bottom'].strip("px")))
                tablelmarg = floor(float(tablestyle['margin-left'].strip("px")))
                tablermarg = floor(float(tablestyle['margin-right'].strip("px")))
            except: # noqa: E722
                logging.warning(f"Ignoring invalid table margin settings {tableStyleAttrib}")
    else:
        # if there is no table, then we look for margin settings on the textFormat. Actually it looks
        # like margin settings can appear on paragraphs and spans as well, but we haven't seen values
        # other than 0 in the MCFs we have looked at, so we will ignore that issue for now.
        # And right now I don't see how VerticalIndentMargin is used, so we don't use it
        if textFormatElement is not None:
            indentMarginAttribute = textFormatElement.get('IndentMargin')
            if indentMarginAttribute is not None:
                try:
                    indentMargin = floor(float(indentMarginAttribute))
                    tabletmarg = tablebmarg = tablelmarg = tablermarg = indentMargin
                except: # noqa: E722
                    logging.warning(f"Invalid IndentMargin attribute {indentMarginAttribute}")

    leftPad = mcf2rl * tablelmarg
    rightPad = mcf2rl * tablermarg
    bottomPad = mcf2rl * tablebmarg
    topPad = mcf2rl * tabletmarg

    # Parse textFormat element for vertical centering alignment
    verticallyCenter = verticallyBottom = False
    if textFormatElement is not None:
        # Read alignment attribute to check for ALIGNVCENTER
        alignmentAttrib = textFormatElement.get('Alignment')
        if alignmentAttrib is not None:
            if 'ALIGNVCENTER' in alignmentAttrib:
                verticallyCenter = True
            elif 'ALIGNBOTTOM' in alignmentAttrib:
                verticallyBottom = True

    logging.debug(f"Text area: center=({transCx},{transCy}), dimensions={areaWidth}x{areaHeight}, topPad={topPad},"
        " bottomPad={bottomPad}, verticallyCenter={verticallyCenter}, tabletmarg={tabletmarg}, tablebmarg={tablebmarg}")

    # if this is text art, then we do the whole thing differently.
    cwtextart = area.findall('decoration/cwtextart')
    if len(cwtextart) > 0:
        processTextArt(area, areaWidth, areaHeight, areaRot, pdf, transCx, transCy, body, leftPad, topPad,
                       cwtextart, context)
        return

    pdf.translate(transCx, transCy)
    pdf.rotate(-areaRot)

    # When vertical centering is enabled in an MCF, we ignore the margins. The text should be
    # centered in the full area, not offset by these margins. The actual centering is performed
    # later after we know the actual text height.
    if verticallyCenter:
        logging.debug(f"Vertical centering enabled: ignoring topPad={topPad}, bottomPad={bottomPad}, indentMargin={indentMargin}")
        topPad = 0.0
        bottomPad = 0.0
        indentMargin = 0.0

    # we don't do shadowing on texts, but we could at least warn about that...
    for decorationTag in area.findall('decoration'):
        warnAndIgnoreEnabledDecorationShadow(decorationTag, context)

    # Get the background color. It is stored in an extra element.
    backgroundColor = None
    backgroundColorAttrib = area.get('backgroundcolor')
    if backgroundColorAttrib is not None:
        backgroundColor = ReorderColorBytesMcf2Rl(backgroundColorAttrib)

    # See the comment below in processTextCore about text wrapping issues. This seems to be
    # caused by cewe2pdf rendering fonts with a slightly thicker stroke than CEWE's Qt renderer.
    # It is unclear why that is. However a workaround here is that we can compensate, only when
    # needed, by applying a 0.99^n scale factor to the font rendering. We do that up to n=3 times.
    # Generally it resolves the wrapping issue with n=1.

    maxShrinkCount = 3
    iterationsToShrinkFontWhenNecessary = maxShrinkCount
    scaleFactor = 1.0
    indexEntryText = None
    firstFinalTotalHeight = 0.0
    originalFrameHeight = mcf2rl * areaHeight

    # The code used to use a global variable to store the flowables. This leads to problems where a
    # flowable in one text area can, in extreme circumstances, appear in another. So, we use a local variable.
    pdf_flowableList = []
    pdf_styleN = None

    while True:
        # Reset it each time we go round this loop. Normally we only call processTextCore once.
        # But, if we encounter the text wrapping issue, we will try again.
        pdf_flowableList = []
        # set default para style in case there are no spans to set it.
        pdf_styleN = CreateParagraphStyle(reportlab.lib.colors.black, bodyfont, bodyfs, scaleFactor)
        pdf_styleN.textOutline = textOutline
        pdf_styleN.letterSpacing = letterSpacing
        textWrapProblem, indexEntryText, finalTotalHeight, frameBottomLeft_x, frameBottomLeft_y, frameHeight, frameWidth, recentText = \
            processTextCore(pdf_flowableList, pdf_styleN, None, additional_fonts, areaHeight, areaWidth,
                body, bodyfont, bodyfs, bottomPad, bstyle, bweight, family, leftPad, pdf, rightPad, topPad, scaleFactor)
        if not textWrapProblem or iterationsToShrinkFontWhenNecessary == 0:
            if not textWrapProblem:
                if scaleFactor < 1.0:
                    logging.info(f'Shrunk text to {scaleFactor:.0%} to fit frame: {extract_text_sections(recentText)}')
            else:
                # We exhausted all attempts to shrink font to fit
                WarnHeightProblem(recentText, originalFrameHeight, frameHeight, firstFinalTotalHeight)
            break
        if iterationsToShrinkFontWhenNecessary == maxShrinkCount:
            # first time, keep the ideal final total height
            firstFinalTotalHeight = finalTotalHeight
        iterationsToShrinkFontWhenNecessary -= 1
        scaleAdjustment = 0.99 # Constant.
        scaleFactor *= scaleAdjustment
        logging.debug(f'Trying to shrink font by {scaleFactor} to fit the frame without wrapping issues')

    # Just add one index entry
    if indexEntryText:
        albumIndex.AddIndexEntry(pgno, indexEntryText)

    # Apply vertical centering if ALIGNVCENTER is specified. We previously set topPad and bottomPad
    # to zero. Now we have the actual text height, we can calculate the required padding to center
    # the text vertically in the area.  With these subtle calculations we can get (almost) pixel
    # perfect centering for normal fonts, and decent centering of "weird" fonts.
    if verticallyCenter and finalTotalHeight < (mcf2rl * areaHeight):
        # Original area height from XML
        originalFrameHeight = mcf2rl * areaHeight
        # Use exact text height for the frame
        # frameHeight = finalTotalHeight
        # Calculate offset to center this smaller frame in the original area
        emptySpace = originalFrameHeight - finalTotalHeight
        a, d = pdfmetrics.getAscentDescent(pdf_styleN.fontName, pdf_styleN.fontSize * scaleFactor)
        logging.debug(f"Font={pdf_styleN.fontName}, size={pdf_styleN.fontSize}, scaleFactor={scaleFactor:.2f}, metrics: a={a:.2f}, d={d:.2f}")
        if (a is not None and finalTotalHeight < 2*(a-d)):
            # We have a single line of text. To vertically center it, we need to re-lay it out with zero leading.
            # This seems to be the only way to get it exactly right (which is both visually preferable and something
            # that CEWE does very well). Leading is extra space designed to ensure multiple lines of text don't overlap.
            # We only have a single line, so any leading is unhelpful and messes up the centering.

            # Occasional fonts - in particular "CEWE Head" produce incorrect results for ascent and descent.
            # The ascent is larger than the fontSize. Practical experimentation shows that this seems to be
            # driven by large amounts of unaccounted for padding/leading applied on top and bottom. In this case our only
            # solution is to divide the apparent empty space equally between top and bottom. This may not
            # be pixel perfect, but it is the best we can do without more precise font information.
            weirdFont = a > pdf_styleN.fontSize

            pdf_flowableList = [] # Throw away previous layout
            # set default para style in case there are no spans to set it.
            pdf_styleN = CreateParagraphStyle(reportlab.lib.colors.black, bodyfont, bodyfs, scaleFactor)
            pdf_styleN.textOutline = textOutline
            pdf_styleN.letterSpacing = letterSpacing
            # use forceLeading=1.0 to force minimal leading.  Even with 1.0 there is generally a bit of spare points of space
            # above the text. This is because fonts are laid out using "Em squares", which are larger than the actual glyphs.
            # So we still need to do some padding adjustment below.
            textWrapProblem, indexEntryText, finalTotalHeight, frameBottomLeft_x, frameBottomLeft_y, frameHeight, frameWidth, recentText = \
                processTextCore(pdf_flowableList, pdf_styleN, 1.0, additional_fonts, areaHeight, areaWidth, body, bodyfont, bodyfs,
                bottomPad, bstyle, bweight, family, leftPad, pdf, rightPad, topPad, scaleFactor)

            # Recalculate for the new height.
            emptySpace = originalFrameHeight - finalTotalHeight
            logging.debug(f"Recalc: originalFrameHeight={originalFrameHeight:.2f}, finalTotalHeight={finalTotalHeight:.2f}, emptySpace={emptySpace:.2f}")
            if weirdFont:
                topPad = emptySpace/2.0
                # Now calculate bottomPad so that total height is correct
                bottomPad = emptySpace - topPad
                logging.debug(f"Weird font, so splitting emptySpace={emptySpace:.2f} equally")
            else:
                heightWithLeading = 1.0 * pdf_styleN.fontSize * scaleFactor
                # Note that d is negative.
                # fontH = a-d
                # Assume leading is 100% above.
                justTheLeading = heightWithLeading - a
                perceivedTextH = a  # we ignore descent for perceived height
                perceivedSpace = originalFrameHeight - perceivedTextH
                topPad = perceivedSpace/2.0 - justTheLeading
                # Now calculate bottomPad so that total height is correct
                bottomPad = emptySpace - topPad
                logging.debug(f"Top: {topPad:.2f}, justTheLeading {justTheLeading:.2f}, text {a:.2f}, desc {-d:.2f} & bottom {bottomPad:.2f} = "
                    "TOTAL {(topPad+justTheLeading+a+bottomPad):.2f} vs frameH {originalFrameHeight:.2f}")
                logging.debug(f"Single line spacing decision for vertical centering: justTheLeading={justTheLeading:.2f}, "
                    "emptySpace={emptySpace:.2f}, perceivedSpace={perceivedSpace:.2f}, perceivedTextH={perceivedTextH:.2f}, "
                    "bottomPad={bottomPad:.2f}, topPad={topPad:.2f}")

            # Note that bottomPad + topPad = perceivedSpace + d
            # So rearranging, bottomPad + topPad + a - d = perceivedSpace + a
            # (to validate our arithmetic)
        else:
            # Looks like 2 or more lines of text. Perceptual center is nearly symmetric; the
            # difference is much less significant than for single lines of text.
            verticalCenterOffset = emptySpace / 2.0
            # Technically these should both be equal, but visual perception is better
            # if we adjust them by 1.0 point in opposite directions
            bottomPad = verticalCenterOffset + 1.0
            topPad = verticalCenterOffset - 1.0
            logging.debug(f"Multi-line spacing decision for vertical centering: emptySpace={emptySpace},"
                " bottomPad={bottomPad}, topPad={topPad}, verticalCenterOffset={verticalCenterOffset:.2f}")

        logging.debug(original_text_only)
        logging.debug(f"VERTICAL CENTERING: originalFrameHeight={originalFrameHeight:.2f}, finalTotalHeight={finalTotalHeight:.2f}, "
            "emptySpace={emptySpace:.2f}")

    if verticallyBottom and finalTotalHeight < (mcf2rl * areaHeight):
        # Original area height from XML
        originalFrameHeight = mcf2rl * areaHeight
        emptySpace = originalFrameHeight - finalTotalHeight
        bottomPad = 0.0
        topPad = emptySpace
        logging.debug(f"VERTICAL BOTTOM: originalFrameHeight={originalFrameHeight:.2f}, finalTotalHeight={finalTotalHeight:.2f}, "
            "emptySpace={emptySpace:.2f}, bottomPad={bottomPad:.2f}, topPad={topPad:.2f}")

    # Now we know the padding (either because it was set long ago, or because we just calculated it for vertical placement)
    newFrame = ColorFrame(frameBottomLeft_x, frameBottomLeft_y,
        frameWidth, frameHeight,
        leftPadding=leftPad, bottomPadding=bottomPad,
        rightPadding=rightPad, topPadding=topPad,
        showBoundary=0,  # for debugging useful to set 1
        background=backgroundColor
        )

    # This call should produce an exception, if any of the flowables do not fit inside the frame.
    # But there seems to be a bug, and no exception is triggered.
    # We took care of this by making the frame so large, that it always can fit the flowables.
    # maybe should switch to res=newFrame.split(flowable, pdf) and check the result manually.
    newFrame.addFromList(pdf_flowableList, pdf)

    for decorationTag in area.findall('decoration'):
        processDecorationBorders(decorationTag, areaHeight, areaWidth, pdf, context)

    pdf.rotate(areaRot)
    pdf.translate(-transCx, -transCy)


def processTextArt(area, areaWidth, areaHeight, areaRot, pdf, transCx, transCy, body, leftPad, topPad,
                   cwtextart, context: RenderContext):
    pdf.translate(transCx, transCy)
    pdf.rotate(-areaRot)
    for decorationTag in area.findall('decoration'):
        processDecorationBorders(decorationTag, areaHeight, areaWidth, pdf, context)
    bodyhtml = etree.tostring(body, pretty_print=True, encoding="unicode")
    radius = topPad - leftPad # is this really what they use for the radius?
    handleTextArt(pdf, radius, bodyhtml, cwtextart)
    pdf.rotate(areaRot)
    pdf.translate(-transCx, -transCy)


def processTextParas(pdf_flowableList, forceLeading, paragraphText: str, additional_fonts, body,
        bodyfont: str | Any, bodyfs: int, bstyle: dict[Any, Any], bweight: int,
        family, indexEntryText: Any | None, pdf, pdf_styleN, fontScaleFactor: float,
        unprocessed_children: set[Any]) -> tuple[Any, str]:
    htmlparas = body.findall(".//p")

    for p in htmlparas:
        # Mark this paragraph as processed
        unprocessed_children.discard(p)
        maxfs = 0  # cannot use the bodyfs as a default, there may not actually be any text at body size
        if p.get('align') == 'center':
            pdf_styleN.alignment = reportlab.lib.enums.TA_CENTER
        elif p.get('align') == 'right':
            pdf_styleN.alignment = reportlab.lib.enums.TA_RIGHT
        elif p.get('align') == 'justify':
            pdf_styleN.alignment = reportlab.lib.enums.TA_JUSTIFY
        else:
            pdf_styleN.alignment = reportlab.lib.enums.TA_LEFT

        # there will be a paragraph style with various attributes, most of which we do not handle.
        # But this is where the line spacing is defined, with the line-height attribute
        pLineHeight = 1.0 # normal line spacing by default
        hasExplicitLineHeight = False
        pStyleAttribute = p.get('style')
        if pStyleAttribute is not None:
            pStyle = dict([kv.split(':') for kv in
                p.get('style').lstrip(' ').rstrip(';').split('; ')])
            if 'line-height' in pStyle.keys():
                try:
                    pLineHeight = floor(float(pStyle['line-height'].strip("%")))/100.0
                    hasExplicitLineHeight = True
                except: # noqa: E722
                    logging.warning(f"Ignoring invalid paragraph line-height setting {pStyleAttribute}")
        finalLeadingFactor = LineScales.lineScaleForFont(bodyfont) * pLineHeight
        # 100% is CEWE's normal layout and retains the established ReportLab
        # auto-leading behaviour.  For a user-selected percentage, however,
        # auto-leading would partly replace the requested leading with font
        # metrics, so use the calculated value unchanged.
        useExplicitLineHeight = hasExplicitLineHeight and pLineHeight != 1.0
        autoLeading = "off" if useExplicitLineHeight else "max"

        def paragraphLeading(usefs):
            if forceLeading is not None:
                return usefs * forceLeading
            if useExplicitLineHeight:
                return LeadingForExplicitLineHeight(bodyfont, usefs, pLineHeight)
            return usefs * finalLeadingFactor

        htmlspans = p.findall(".*")
        if len(htmlspans) < 1: # i.e. there are no spans, just a paragraph
            paragraphText = f'<para autoLeading="{autoLeading}">'
            paragraphText, maxfs = AppendItemTextInStyle(paragraphText, p.text, p, pdf,
                additional_fonts, bodyfont, bodyfs, bweight, bstyle, fontScaleFactor)
            paragraphText += '</para>'
            usefs = maxfs if maxfs > 0 else bodyfs
            pdf_styleN.leading = paragraphLeading(usefs) # line spacing (text + leading)
            pdf_flowableList.append(TextEffectsParagraph(paragraphText, pdf_styleN))
            originalFont = CollectItemFontFamily(p, family)
            if albumIndex.CheckForIndexEntry(originalFont, bodyfs):
                indexEntryText = Index.AppendIndexText(indexEntryText, p.text)

        else:
            paragraphText = f'<para autoLeading="{autoLeading}">'

            # there might be untagged text preceding a span. We have to add that to paragraphText
            # first - but we must not terminate the paragraph and add it to the flowable because
            # the first span just continues that leading text
            if p.text is not None:
                paragraphText, maxfs = AppendItemTextInStyle(paragraphText, p.text, p, pdf,
                    additional_fonts, bodyfont, bodyfs, bweight, bstyle, fontScaleFactor)
                usefs = maxfs if maxfs > 0 else bodyfs
                pdf_styleN.leading = paragraphLeading(usefs)  # line spacing (text + leading)

            # now run round the htmlspans
            for item in htmlspans:
                if item.tag == 'br':
                    br = item
                    # terminate the current pdf para and add it to the flow. The nbsp seems unnecessary
                    # but if it is not there then an empty paragraph goes missing :-(
                    paragraphText += '&nbsp;</para>'
                    usefs = maxfs if maxfs > 0 else bodyfs
                    pdf_styleN.leading = paragraphLeading(usefs)  # line spacing (text + leading)
                    pdf_flowableList.append(TextEffectsParagraph(paragraphText, pdf_styleN))
                    # start a new pdf para in the style of the para and add the tail text of this br item
                    paragraphText = f'<para autoLeading="{autoLeading}">'
                    paragraphText, maxfs = AppendItemTextInStyle(paragraphText, br.tail, p, pdf,
                        additional_fonts, bodyfont, bodyfs, bweight, bstyle, fontScaleFactor)

                elif item.tag == 'span':
                    span = item
                    spanfont, spanfs, spanweight, spanstyle = CollectFontInfo(span, pdf, additional_fonts, bodyfont,
                        bodyfs, bweight, fontScaleFactor)

                    maxfs = max(maxfs, spanfs)

                    paragraphText = AppendSpanStart(paragraphText, spanfont, spanfs, spanweight, spanstyle, bstyle)

                    if span.text is not None:
                        paragraphText = AppendText(paragraphText, html.escape(span.text))
                        originalFont = CollectItemFontFamily(span, family)
                        if albumIndex.CheckForIndexEntry(originalFont, spanfs):
                            indexEntryText = Index.AppendIndexText(indexEntryText, span.text)

                    # there might be (one or more, or only one?) line break within the span.
                    brs = span.findall(".//br")
                    if len(brs) > 0:
                        # terminate the "real" span that we started above
                        paragraphText = AppendSpanEnd(paragraphText, spanweight, spanstyle, bstyle)
                        for br in brs:
                            # terminate the current pdf para and add it to the flow
                            paragraphText += '</para>'
                            usefs = maxfs if maxfs > 0 else bodyfs
                            pdf_styleN.leading = paragraphLeading(usefs)  # line spacing (text + leading)
                            pdf_flowableList.append(TextEffectsParagraph(paragraphText, pdf_styleN))
                            # start a new pdf para in the style of the current span
                            paragraphText = f'<para autoLeading="{autoLeading}">'
                            # now add the tail text of each br in the span style
                            paragraphText, maxfs = AppendItemTextInStyle(paragraphText, br.tail, span, pdf,
                                additional_fonts, bodyfont, bodyfs, bweight,
                                bstyle, fontScaleFactor)
                    else:
                        paragraphText = AppendSpanEnd(paragraphText, spanweight, spanstyle, bstyle)

                    if span.tail is not None:
                        paragraphText = AppendText(paragraphText, html.escape(span.tail))

                else:
                    logging.warning(
                        f"Ignoring unhandled tag {item.tag} in text area (tag content: {etree.tostring(item, encoding='unicode')[:100]}...)")

            # try to create a paragraph with the current text and style. Catch errors.
            try:
                paragraphText += '</para>'
                usefs = maxfs if maxfs > 0 else bodyfs
                pdf_styleN.leading = paragraphLeading(usefs)  # line spacing (text + leading)
                pdf_flowableList.append(TextEffectsParagraph(paragraphText, pdf_styleN))
            except Exception:
                logging.exception('Exception')
    return indexEntryText, paragraphText

def processTextCore(pdf_flowableList, pdf_styleN, forceLeading, additional_fonts, areaHeight, areaWidth, body, bodyfont: str | Any, bodyfs: int,
                    bottomPad: float | int | Any, bstyle: dict[Any, Any], bweight: int, family,
                    leftPad: float | int | Any, pdf, rightPad: float | int | Any, topPad: float | int | Any,
                    fontScaleFactor: float) -> \
        tuple[bool, str | Any, float | int | Any, float | Any, float | Any, float | Any, float | int | Any, str | Any]:

    # for debugging the background colour may be useful, but it is not used in production
    # since we started to use ColorFrame to colour the background, and it is thus left
    # unset by CreateParagraphStyle
    # pdf_styleN.backColor = reportlab.lib.colors.HexColor("0xFFFF00")
    pdf_styleN.leading = bodyfs * fontScaleFactor

    # There may be multiple "index entry" paragraphs in the text area.
    # Concatenating them to just one index entry seems to work in practice
    indexEntryText = None
    # Keep track of recent text so we can provide informative errors.
    recentParagraphText = ''

    # Track all direct children of body to validate we process everything
    all_body_children = list(body)
    unprocessed_children = set(all_body_children)  # Will remove elements as we process them

    indexEntryText, recentParagraphText = processTextParas(pdf_flowableList, forceLeading, recentParagraphText,
        additional_fonts, body, bodyfont, bodyfs, bstyle, bweight, family, indexEntryText, pdf, pdf_styleN,
        fontScaleFactor, unprocessed_children)

    recentParagraphText = processTextUL(pdf_flowableList, forceLeading, recentParagraphText, additional_fonts,
        body, bodyfont, bodyfs, bstyle, bweight, pdf, pdf_styleN, fontScaleFactor, unprocessed_children)

    # The <table> tag contains margin info, not actual content - mark it as processed
    table = body.find('table')
    if table is not None:
        unprocessed_children.discard(table)

    # Validate: warn about any body children that we didn't process
    if unprocessed_children:
        logging.warning("=" * 80)
        logging.warning("TEXT CONTENT BEING SILENTLY IGNORED!")
        logging.warning(f"Found {len(unprocessed_children)} unprocessed elements as direct children of <body>:")
        for child in unprocessed_children:
            child_text = ''.join(child.itertext())[:100]  # Get text content, first 100 chars
            logging.warning(f"  Ignoring <{child.tag}> with {len(list(child))} children")
            logging.warning(f"    Text content preview: {child_text}")
            logging.warning(f"    XML: {etree.tostring(child, encoding='unicode')[:200]}...")
        logging.warning("=" * 80)

    # Add a frame object that can contain multiple paragraphs. Margins (padding) are specified in
    # the editor in mm, arriving in the mcf in 1/10 mm, but appearing in the html with the unit "px".
    # This is a bit strange, but ignoring the "px" and using mcf2rl seems to work ok.
    frameWidth = mcf2rl * areaWidth
    frameHeight = mcf2rl * areaHeight
    frameBottomLeft_x = -0.5 * frameWidth
    frameBottomLeft_y = -0.5 * frameHeight

    finalTotalHeight = topPad + bottomPad # built up in the text height check loop
    finalTotalWidth = frameWidth # should never be exceeded in the text height check loop
    availableTextHeight = frameHeight - topPad - bottomPad
    availableTextWidth = frameWidth - leftPad - rightPad

    # Go through all flowables and test if the fit in the frame. If not increase the frame height.
    # To solve the problem, that if each paragraph will fit indivdually, and also all together,
    # we need to keep track of the total summed height+
    for flowableListItem in pdf_flowableList:
        neededTextWidth, neededTextHeight = flowableListItem.wrap(availableTextWidth, availableTextHeight)
        finalTotalHeight += neededTextHeight
        availableTextHeight -= neededTextHeight
        if neededTextWidth > availableTextWidth:
            # I have never seen this happen, but check anyway
            logging.error('A set of paragraphs too wide for its frame. INTERNAL ERROR!')
            finalTotalWidth = neededTextWidth + leftPad + rightPad

    # ReportLab and CEWE can differ by a fraction of a point in their font
    # metrics. Do not reduce the font merely to correct such an invisible
    # vertical discrepancy; the frame is enlarged by that small amount below.
    fitTolerance = 0.5  # points, approximately 0.18 mm
    heightOverflow = finalTotalHeight - frameHeight
    textWrapProblem = heightOverflow > fitTolerance
    if heightOverflow > 0 and not textWrapProblem:
        logging.debug(
            f"Text frame exceeds its height by {heightOverflow:.2f} points "
            f"(within {fitTolerance:.2f}-point tolerance); not shrinking"
        )
    if textWrapProblem:
        # One of the possible causes here is that wrap function has used an extra line (because
        #  of some slight mismatch in character widths and a frame that matches too precisely?)
        #  so that a word wraps over when it shouldn't. I don't know how to fix that sensibly.
        #  Increasing the height is NOT a good visual solution, because the line wrap is still
        #  not where the user expects it - increasing the width would almost be more sensible!
        # Another suspected cause is in the use of multiple font sizes in one text. Perhaps the
        #  line scale (interline space) gets confused by this?
        # From Mar 2026 the code outside of this will iterate up to 3 times, shrinking the font
        # slightly to see if it helps. If it doesn't then we increase the frame height as a last
        # resort, just like we did previously
        frameHeight = finalTotalHeight
    else:
        frameHeight = max(frameHeight, finalTotalHeight)

    frameWidth = max(frameWidth, finalTotalWidth)
    return textWrapProblem, indexEntryText, finalTotalHeight, frameBottomLeft_x, frameBottomLeft_y, frameHeight, frameWidth, recentParagraphText


def processTextUL(pdf_flowableList, forceLeading, paragraphText: str, additional_fonts, body,
        bodyfont: str | Any, bodyfs: int, bstyle: dict[Any, Any], bweight: int, pdf,
        pdf_styleN, fontScaleFactor: float, unprocessed_children: set[Any]) -> str:
    # Process <ul> (unordered list) elements - bulleted lists
    htmllists = body.findall("ul")

    for ul in htmllists:
        # Mark this list as processed
        unprocessed_children.discard(ul)

        listitems = ul.findall("li")

        for li in listitems:
            maxfs = 0

            # Create a copy of the style for this list item with hanging indent
            list_styleN = ParagraphStyle('list_item', parent=pdf_styleN)
            # Hanging indent: first line at 0, subsequent lines indented
            # Calculate indent based on font size - approximately 2x the font size
            # accounts for bullet width + space
            bullet_indent = bodyfs * 1.65  # Adjust multiplier if needed (1.5 - 2.5 range)
            list_styleN.leftIndent = bullet_indent  # Where wrapped lines start
            list_styleN.firstLineIndent = -bullet_indent / 2  # Pull first line (with bullet) back halfway position 0
            bullet_txt = '• '

            # Check alignment (though lists are typically left-aligned)
            if li.get('align') == 'center':
                list_styleN.alignment = reportlab.lib.enums.TA_CENTER
            elif li.get('align') == 'right':
                list_styleN.alignment = reportlab.lib.enums.TA_RIGHT
            elif li.get('align') == 'justify':
                list_styleN.alignment = reportlab.lib.enums.TA_JUSTIFY
            else:
                list_styleN.alignment = reportlab.lib.enums.TA_LEFT

            # Get line height from <li> style if present
            pLineHeight = 1.0
            liStyleAttribute = li.get('style')
            if liStyleAttribute is not None:
                liStyle = dict([kv.split(':') for kv in
                                li.get('style').lstrip(' ').rstrip(';').split('; ')])
                if 'line-height' in liStyle.keys():
                    try:
                        pLineHeight = floor(float(liStyle['line-height'].strip("%"))) / 100.0
                    except:  # noqa: E722
                        logging.warning(f"Ignoring invalid list item line-height setting {liStyleAttribute}")
            finalLeadingFactor = LineScales.lineScaleForFont(bodyfont) * pLineHeight

            # Start paragraph - we'll add bullet inside the styled text
            paragraphText = '<para autoLeading="max">'

            # Check if there are child elements (spans, br, etc.)
            lispans = li.findall(".*")

            if len(lispans) < 1:
                # Simple list item with just text, no spans
                # Prepend bullet to the text so it gets styled
                bullet_plus_text = bullet_txt + (li.text if li.text is not None else "")
                paragraphText, maxfs = AppendItemTextInStyle(paragraphText, bullet_plus_text, li, pdf,
                                                             additional_fonts, bodyfont, bodyfs, bweight, bstyle, fontScaleFactor)
                paragraphText += '</para>'
                usefs = maxfs if maxfs > 0 else bodyfs
                list_styleN.leading = usefs * forceLeading if forceLeading is not None else usefs * finalLeadingFactor
                pdf_flowableList.append(TextEffectsParagraph(paragraphText, list_styleN))
            else:
                # List item with spans and other formatting
                bullet_plus_text = bullet_txt + (li.text if li.text is not None else "")
                paragraphText, maxfs = AppendItemTextInStyle(paragraphText, bullet_plus_text, li, pdf,
                                                             additional_fonts, bodyfont, bodyfs, bweight, bstyle, fontScaleFactor)
                paragraphText, maxfs = AppendItemTextInStyle(paragraphText, bullet_plus_text, li, pdf,
                                                             additional_fonts, bodyfont, bodyfs, bweight, bstyle, fontScaleFactor)
                usefs = maxfs if maxfs > 0 else bodyfs
                list_styleN.leading = usefs * forceLeading if forceLeading is not None else usefs * finalLeadingFactor

                # Process child elements (spans, br, etc.)
                for item in lispans:
                    if item.tag == 'br':
                        br = item
                        # For lists, we don't typically break into multiple paragraphs on <br>
                        # Instead, insert a line break within the same paragraph
                        paragraphText += '<br/>'
                        if br.tail:
                            paragraphText, maxfs = AppendItemTextInStyle(paragraphText, br.tail, li, pdf,
                                                                         additional_fonts, bodyfont, bodyfs, bweight,
                                                                         bstyle, fontScaleFactor)

                    elif item.tag == 'span':
                        span = item
                        spanfont, spanfs, spanweight, spanstyle = CollectFontInfo(span, pdf, additional_fonts, bodyfont,
                                                                                  bodyfs, bweight, fontScaleFactor)

                        maxfs = max(maxfs, spanfs)

                        paragraphText = AppendSpanStart(paragraphText, spanfont, spanfs, spanweight, spanstyle, bstyle)

                        if span.text is not None:
                            paragraphText = AppendText(paragraphText, html.escape(span.text))

                        # Handle line breaks within spans
                        brs = span.findall(".//br")
                        if len(brs) > 0:
                            paragraphText = AppendSpanEnd(paragraphText, spanweight, spanstyle, bstyle)
                            for br in brs:
                                paragraphText += '<br/>'
                                if br.tail:
                                    paragraphText, maxfs = AppendItemTextInStyle(paragraphText, br.tail, span, pdf,
                                                                                 additional_fonts, bodyfont, bodyfs,
                                                                                 bweight, bstyle, fontScaleFactor)
                        else:
                            paragraphText = AppendSpanEnd(paragraphText, spanweight, spanstyle, bstyle)

                        if span.tail is not None:
                            paragraphText = AppendText(paragraphText, html.escape(span.tail))

                    else:
                        logging.warning(
                            f"Ignoring unhandled tag {item.tag} in list item (tag content: {etree.tostring(item, encoding='unicode')[:100]}...)")

                # Finalize the list item paragraph
                try:
                    paragraphText += '</para>'
                    usefs = maxfs if maxfs > 0 else bodyfs
                    list_styleN.leading = usefs * forceLeading if forceLeading is not None else usefs * finalLeadingFactor
                    pdf_flowableList.append(TextEffectsParagraph(paragraphText, list_styleN))
                except Exception:
                    logging.exception('Exception')
    return paragraphText


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
