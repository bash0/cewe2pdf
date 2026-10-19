"""Rendering of CEWE clipart areas."""

import logging

from PIL import Image
from reportlab.lib.utils import ImageReader

from .catalog import getClipConfig, loadClipart
from conversionState import ConversionState
from renderContext import RenderContext


def _hasEnabledShadow(decoration):
    """Return whether ``decoration`` contains a CEWE-enabled shadow."""
    return (decoration is not None
            and any(shadow.get('shadowEnabled') in (None, '1')
                    for shadow in decoration.findall('shadow')))


def processAreaClipartTag(clipartElement, areaHeight, areaRot, areaWidth, pdf, transx, transy,
                          clipArtDecoration, context: RenderContext,
                          state: ConversionState, shadowProcessor, borderProcessor):
    """Render one clipart area and its optional decorations."""
    clipartID = int(clipartElement.get('designElementId'))
    if clipartID == 0:
        return

    fileName = context.clipart_files.get(clipartID)
    if not fileName:
        logging.warning(f"Could not find clipart {clipartID}; leaving it out.")
        return

    alpha = 255
    if clipArtDecoration is not None:
        alphaText = clipArtDecoration.get('alpha')
        if alphaText is not None:
            alpha = int(float(alphaText) * 255)

    colorReplacements, flipX, flipY = getClipConfig(clipartElement)
    insertClipartFile(fileName, colorReplacements, transx, areaWidth, areaHeight, alpha, pdf,
                      transy, areaRot, flipX, flipY, clipArtDecoration, context, state,
                      shadowProcessor, borderProcessor)


def insertClipartFile(fileName, colorReplacements, transx, areaWidth, areaHeight, alpha, pdf,
                      transy, areaRot, flipX, flipY, decoration, context: RenderContext,
                      state: ConversionState | None = None, shadowProcessor=None,
                      borderProcessor=None):
    """Rasterise a clipart file and draw it at the supplied area geometry."""
    newWidth = int(0.5 + areaWidth * context.image_resolution / 254.0)
    newHeight = int(0.5 + areaHeight * context.image_resolution / 254.0)

    clipart = loadClipart(fileName, context.clipart_paths)
    if len(clipart.svgData) <= 0:
        logging.error(f"Clipart file could not be loaded: {fileName}")
        return

    if len(colorReplacements) > 0:
        clipart.replaceColors(colorReplacements)

    clipart.convertToPngInBuffer(newWidth, newHeight, alpha, flipX, flipY)
    clipartImage = None
    if _hasEnabledShadow(decoration) and shadowProcessor is not None and state is not None:
        # Use the rasterised SVG's alpha silhouette.  In particular, open
        # artwork (for example an arrow) must not cast a rectangular shadow.
        clipartImage = Image.open(clipart.pngMemFile).convert('RGBA')
        clipartImage.load()
        clipart.pngMemFile.seek(0)
    logging.debug(f"Clipart file: {fileName}")
    pdf.translate(transx, transy)
    pdf.rotate(-areaRot)
    if clipartImage is not None:
        shadowProcessor(decoration, areaHeight, areaWidth, pdf, context, state,
                        clipartImage, areaWidth, areaHeight, areaRotation=areaRot)
    pdf.drawImage(ImageReader(clipart.pngMemFile),
                  context.mcf_to_reportlab * -0.5 * areaWidth,
                  context.mcf_to_reportlab * -0.5 * areaHeight,
                  width=context.mcf_to_reportlab * areaWidth,
                  height=context.mcf_to_reportlab * areaHeight, mask='auto')
    if decoration is not None and borderProcessor is not None:
        borderProcessor(decoration, areaHeight, areaWidth, pdf)
    pdf.rotate(areaRot)
    pdf.translate(-transx, -transy)
