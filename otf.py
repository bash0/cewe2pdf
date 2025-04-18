# This file contains code to handle .otf files, which we do by converting to ttf files

# This code is heavily based on https://github.com/awesometoolbox/otf2ttf/blob/master/src/otf2ttf/cli.py
# and https://github.com/SwagLyrics/SwagLyrics-For-Spotify/blob/master/swaglyrics/__init__.py#L8-L32

import os

from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.misc.cliTools import makeOutputFileName
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.cu2qu import errors # noqa: errors not used here, but this ensures that pyinstaller gets it pylint: disable=unused-import

from extraLoggers import configlogger
from pathutils import appdata_dir

# default approximation error, measured in UPEM
MAX_ERR = 1.0
# default 'post' table format
POST_FORMAT = 2.0
# assuming the input contours' direction is correctly set (counter-clockwise),
# we just flip it to clockwise
REVERSE_DIRECTION = True


def glyphs_to_quadratic(
    glyphs, max_err=MAX_ERR, reverse_direction=REVERSE_DIRECTION
):
    quadGlyphs = {}
    for gname in glyphs.keys():
        glyph = glyphs[gname]
        ttPen = TTGlyphPen(glyphs)
        cu2quPen = Cu2QuPen(
            ttPen, max_err, reverse_direction=reverse_direction
        )
        glyph.draw(cu2quPen)
        quadGlyphs[gname] = ttPen.glyph()
    return quadGlyphs


def otf_to_ttf(ttFont, post_format=POST_FORMAT, **kwargs):
    assert ttFont.sfntVersion == "OTTO"
    assert "CFF " in ttFont

    glyphOrder = ttFont.getGlyphOrder()

    ttFont["loca"] = newTable("loca")
    ttFont["glyf"] = glyf = newTable("glyf")
    glyf.glyphOrder = glyphOrder
    glyf.glyphs = glyphs_to_quadratic(ttFont.getGlyphSet(), **kwargs)
    del ttFont["CFF "]
    glyf.compile(ttFont)

    ttFont["maxp"] = maxp = newTable("maxp")
    maxp.tableVersion = 0x00010000
    maxp.maxZones = 1
    maxp.maxTwilightPoints = 0
    maxp.maxStorage = 0
    maxp.maxFunctionDefs = 0
    maxp.maxInstructionDefs = 0
    maxp.maxStackElements = 0
    maxp.maxSizeOfInstructions = 0
    maxp.maxComponentElements = max(
        len(g.components if hasattr(g, "components") else [])
        for g in glyf.glyphs.values()
    )
    maxp.compile(ttFont)

    post = ttFont["post"]
    post.formatType = post_format
    post.extraNames = []
    post.mapping = {}
    post.glyphOrder = glyphOrder
    try:
        post.compile(ttFont)
    except OverflowError:
        post.formatType = 3
        configlogger.warning("Dropping glyph names, they do not fit in 'post' table.")

    ttFont.sfntVersion = "\000\001\000\000"


def getTtfsFromOtfs(otfFiles, ttfdirPath=None):
    resultingTtfFiles = []

    if ttfdirPath is None:
        ttfdirPath = appdata_dir()

    if not os.path.exists(ttfdirPath):
        os.mkdir(ttfdirPath)

    for otfFile in otfFiles:
        if "LiebeGerda-BoldItalic" in otfFile:
            configlogger.info("LiebeGerda-BoldItalic not available: the otf->ttf conversion hangs!")
            continue # the conversion code hangs on this font!
        ttfFile = makeOutputFileName(
            otfFile,
            outputDir=ttfdirPath,
            extension=".ttf",
            overWrite=True, # options.overwrite
        )
        if os.path.exists(ttfFile):
            configlogger.info(f"Accepting otf->ttf font conversion: {ttfFile}")
        else:
            configlogger.warning(f"One-time font conversion otf->ttf: {ttfFile}")
            font = TTFont(otfFile, fontNumber=0) # options.face_index
            otf_to_ttf(
                font,
                post_format=POST_FORMAT, # options.post_format
                max_err=MAX_ERR, # options.max_error
                reverse_direction=REVERSE_DIRECTION, # options.reverse_direction
            )
            font.save(ttfFile)

        resultingTtfFiles.append(ttfFile)

    return resultingTtfFiles
