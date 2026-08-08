"""Rendering of CEWE clipart areas."""

import logging

from reportlab.lib.utils import ImageReader

from clipArt import getClipConfig, loadClipart


def processAreaClipartTag(clipartElement, areaHeight, areaRot, areaWidth, pdf, transx, transy,
                          clipArtDecoration, clipartDict, clipartPathList, image_res, mcf2rl,
                          borderProcessor):
    """Render one clipart area and its optional border."""
    clipartID = int(clipartElement.get('designElementId'))
    if clipartID == 0:
        return

    fileName = clipartDict.get(clipartID)
    if not fileName:
        logging.error(f"Problem getting file name for clipart ID: {clipartID}")
        return

    alpha = 255
    if clipArtDecoration is not None:
        alphaText = clipArtDecoration.get('alpha')
        if alphaText is not None:
            alpha = int(float(alphaText) * 255)

    colorReplacements, flipX, flipY = getClipConfig(clipartElement)
    insertClipartFile(fileName, colorReplacements, transx, areaWidth, areaHeight, alpha, pdf,
                      transy, areaRot, flipX, flipY, clipArtDecoration, clipartPathList,
                      image_res, mcf2rl, borderProcessor)


def insertClipartFile(fileName, colorReplacements, transx, areaWidth, areaHeight, alpha, pdf,
                      transy, areaRot, flipX, flipY, decoration, clipartPathList, image_res,
                      mcf2rl, borderProcessor=None):
    """Rasterise a clipart file and draw it at the supplied area geometry."""
    newWidth = int(0.5 + areaWidth * image_res / 254.0)
    newHeight = int(0.5 + areaHeight * image_res / 254.0)

    clipart = loadClipart(fileName, clipartPathList)
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
                  mcf2rl * -0.5 * areaWidth, mcf2rl * -0.5 * areaHeight,
                  width=mcf2rl * areaWidth, height=mcf2rl * areaHeight, mask='auto')
    if decoration is not None and borderProcessor is not None:
        borderProcessor(decoration, areaHeight, areaWidth, pdf)
    pdf.rotate(areaRot)
    pdf.translate(-transx, -transy)
