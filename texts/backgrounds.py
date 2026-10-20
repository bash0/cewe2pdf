"""Shared text-background colour/opacity and TextArt ring painting."""

import logging

from colorUtils import ReorderColorBytesMcf2Rl


def getTextBackground(area):
    """Return the background colour and separate decoration opacity."""
    textAreaAlpha = 1.0
    for decorationTag in area.findall('decoration'):
        alphaText = decorationTag.get('alpha')
        if alphaText is not None:
            try:
                textAreaAlpha = float(alphaText)
            except ValueError:
                logging.warning(f"Ignoring invalid text-area alpha setting {alphaText!r}")
            else:
                if not 0.0 <= textAreaAlpha <= 1.0:
                    logging.warning(f"Clamping text-area alpha setting {alphaText!r} to 0..1")
                    textAreaAlpha = max(0.0, min(1.0, textAreaAlpha))

    backgroundColor = None
    backgroundColorAttrib = area.get('backgroundcolor')
    if backgroundColorAttrib is not None:
        backgroundColor = ReorderColorBytesMcf2Rl(backgroundColorAttrib)
    return backgroundColor, textAreaAlpha


def drawTextArtBackground(pdf, area, radiusX, radiusY, circleCenterY, bandWidth):
    """Paint the complete ring behind curved text, leaving its centre transparent."""
    backgroundColor, textAreaAlpha = getTextBackground(area)
    if backgroundColor is None or backgroundColor.alpha == 0 or textAreaAlpha == 0:
        return
    if radiusY is None:
        radiusY = radiusX
    if radiusX <= 0 or radiusY <= 0 or bandWidth <= 0:
        return

    # The editor's default 490-unit / 18-point example has an inner radius
    # of 171 and an outer radius of 245 MCF units. Its 74-unit band is the
    # same font-sized top inset used to anchor the text curve. Keep the full
    # ring even when the text occupies only a short arc.
    outerX, outerY = radiusX + bandWidth, radiusY + bandWidth
    pdf.saveState()
    pdf.setFillColor(backgroundColor, alpha=backgroundColor.alpha * textAreaAlpha)
    path = pdf.beginPath()
    path.ellipse(-outerX, circleCenterY - outerY, 2 * outerX, 2 * outerY)
    path.ellipse(-radiusX, circleCenterY - radiusY, 2 * radiusX, 2 * radiusY)
    # Even-odd filling punches a real hole: painting it white would hide any
    # photograph or coloured page underneath, and breaks transparency.
    pdf.drawPath(path, stroke=0, fill=1, fillMode=0)
    pdf.restoreState()
