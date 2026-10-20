"""Render real text to transparent silhouettes for the shared shadow engine."""

from io import BytesIO
import copy
import logging

import pymupdf
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame

from decorations.shadows import processDecorationShadow
from colorFrame import ColorFrame
from conversionState import ConversionState
from renderContext import RenderContext
from infrastructure.configUtils import getConfigurationBool


def hasEnabledTextShadow(area, context):
    """Avoid rasterising text when its shadows are disabled."""
    if getConfigurationBool(context.default_config_section, 'noShadows', False):
        return False
    return any(shadow.get('shadowEnabled', '1') == '1'
        for decoration in area.findall('decoration')
        for shadow in decoration.findall('shadow'))


def renderTextSilhouette(drawText, width, height, resolution, expandBounds=False):
    """Return an RGBA text mask and its bounds in the original PDF coordinates."""
    with BytesIO() as stream:
        shadowCanvas = canvas.Canvas(stream, pagesize=(width, height))
        drawText(shadowCanvas)
        shadowCanvas.showPage()
        shadowCanvas.save()
        pdfBytes = stream.getvalue()
    with pymupdf.open(stream=pdfBytes, filetype='pdf') as document:
        page = document[0]
        bounds = pymupdf.Rect(0, 0, width, height)
        if expandBounds:
            # Curved lettering can extend beyond its area. Read actual glyph
            # bounds, then enlarge the temporary page rather than clipping the
            # mask or guessing padding from font sizes. PyMuPDF's bounds use a
            # top-left origin; MediaBox uses PDF's bottom-left coordinates.
            for kind, rectangle in page.get_bboxlog():
                if kind in ('fill-text', 'stroke-text'):
                    bounds |= pymupdf.Rect(rectangle)
            bounds = pymupdf.Rect(bounds.x0, height - bounds.y1, bounds.x1, height - bounds.y0)
            page.set_mediabox(bounds)
        scale = resolution / 72.0
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=True)
        image = Image.frombytes('RGBA', (pixmap.width, pixmap.height), pixmap.samples)
    return image, (bounds.x0, bounds.y0, bounds.width, bounds.height)


def drawTextShadow(
    pdf_flowableList, frameWidth, frameHeight,
    leftPad, bottomPad, rightPad,
    topPad, area, areaHeight, areaWidth, areaRot, pdf,
    context: RenderContext, state: ConversionState
):
    """Render the actual laid-out text to an alpha silhouette and shadow it.

    CEWE shadows the glyphs, not the rectangular text area.  Text flowables
    already know how to reproduce CEWE's rich text: fonts, spans, tab stops,
    outlines and line wrapping.  Rendering a copy of them into a transparent
    one-page PDF therefore gives us the same alpha silhouette which image and
    clip-art shadows use, without attempting to recreate the text in Pillow.
    """
    shadowFrame = ColorFrame(
        0, 0, frameWidth, frameHeight,
        leftPadding=leftPad, bottomPadding=bottomPad,
        rightPadding=rightPad, topPadding=topPad,
        showBoundary=0
    )
    try:
        # Frame.addFromList consumes its input. Render a copy for the shadow,
        # leaving the original flowables for the normal text pass below.
        textImage, _ = renderTextSilhouette(
            lambda shadowCanvas: Frame.addFromList(shadowFrame, copy.deepcopy(pdf_flowableList), shadowCanvas),
            frameWidth, frameHeight, context.image_resolution)
    except Exception:  # pylint: disable=broad-exception-caught
        logging.exception('Could not create text shadow silhouette')
        return

    # The mask occupies the full text area, so it uses the same local origin
    # as the real text.  The caller has already applied the area's transform.
    for decorationTag in area.findall('decoration'):
        processDecorationShadow(
            decorationTag, areaHeight, areaWidth, pdf, context, state,
            im=textImage, imgCropWidth_mcfunit=areaWidth,
            imgCropHeight_mcfunit=areaHeight, areaRotation=areaRot
        )


def drawTextArtShadow(pdf, area, areaWidth, areaHeight, areaRot, drawText, context, state):
    """Cast a shadow from the exact curved glyphs, without its ring or border."""
    if not hasEnabledTextShadow(area, context):
        return
    width = areaWidth * context.mcf_to_reportlab
    height = areaHeight * context.mcf_to_reportlab

    def paintMask(shadowCanvas):
        shadowCanvas.translate(width / 2, height / 2)
        drawText(shadowCanvas)

    try:
        image, bounds = renderTextSilhouette(paintMask, width, height, context.image_resolution, True)
    except Exception:  # A shadow failure must not suppress the visible text. pylint: disable=broad-exception-caught
        logging.exception('Could not create TextArt shadow silhouette')
        return
    left, bottom, maskWidth, maskHeight = bounds
    maskWidthMcf = maskWidth / context.mcf_to_reportlab
    maskHeightMcf = maskHeight / context.mcf_to_reportlab
    pdf.saveState()
    # The shared image-shadow renderer centres its input. Compensate for any
    # asymmetric extension of the mask beyond the original text-area page.
    pdf.translate(left + maskWidth / 2 - width / 2, bottom + maskHeight / 2 - height / 2)
    for decoration in area.findall('decoration'):
        processDecorationShadow(decoration, maskHeightMcf, maskWidthMcf, pdf, context, state,
            im=image, imgCropWidth_mcfunit=maskWidthMcf, imgCropHeight_mcfunit=maskHeightMcf,
            areaRotation=areaRot)
    pdf.restoreState()
