"""Rendering of CEWE clipart areas."""

import logging

from reportlab.lib.utils import ImageReader

from clipArt import getClipConfig, loadClipart
from renderContext import RenderContext


def processAreaClipartTag(clipartElement, areaHeight, areaRot, areaWidth, pdf, transx, transy,
                          clipArtDecoration, context: RenderContext,
                          borderProcessor):
    """Render one clipart area and its optional border."""
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
                      transy, areaRot, flipX, flipY, clipArtDecoration, context, borderProcessor)


def insertClipartFile(fileName, colorReplacements, transx, areaWidth, areaHeight, alpha, pdf,
                      transy, areaRot, flipX, flipY, decoration, context: RenderContext,
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
    logging.debug(f"Clipart file: {fileName}")
    pdf.translate(transx, transy)
    pdf.rotate(-areaRot)
    pdf.drawImage(ImageReader(clipart.pngMemFile),
                  context.mcf_to_reportlab * -0.5 * areaWidth,
                  context.mcf_to_reportlab * -0.5 * areaHeight,
                  width=context.mcf_to_reportlab * areaWidth,
                  height=context.mcf_to_reportlab * areaHeight, mask='auto')
    if decoration is not None and borderProcessor is not None:
        borderProcessor(decoration, areaHeight, areaWidth, pdf)
    pdf.rotate(areaRot)
    pdf.translate(-transx, -transy)
