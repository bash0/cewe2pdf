"""Border-decoration rendering for CEWE areas."""

from math import floor

import reportlab.lib.colors
from reportlab.platypus import Table

from corners import buildCornerPath, hasImplementedCorners
from renderContext import RenderContext


def processDecorationBorders(decoration, areaHeight, areaWidth, pdf,
                             context: RenderContext, cornersInfo=None):
    """Draw the border decoration for an already-positioned area."""
    mcf2rl = context.mcf_to_reportlab
    for border in decoration.findall('border'):
        if border.get('enabled') is not None and border.get('enabled') != '1':
            return

        borderWidth = 1
        widthText = border.get('width')
        if widthText is not None:
            borderWidth = mcf2rl * floor(float(widthText))

        borderColor = reportlab.lib.colors.blue
        colorText = border.get('color')
        if colorText is not None:
            # CEWE ignores border transparency and sometimes stores a border
            # with no visible colour to mean no border.
            if colorText == '#00000000':
                return
            borderColor = reportlab.lib.colors.HexColor(colorText)

        adjustment = 0
        gap = 0
        gapText = border.get('gap')
        if gapText is not None:
            gap = mcf2rl * floor(float(gapText))
        position = border.get('position')
        if position == "insideWithGap":
            adjustment = -borderWidth * 0.5 - gap
        if position == "inside":
            adjustment = -borderWidth * 0.5
        if position == "outside":
            adjustment = borderWidth * 0.5
        if position == "outsideWithGap":
            adjustment = borderWidth * 0.5 + gap

        frameBottomLeftX = -0.5 * (mcf2rl * areaWidth) - adjustment
        frameBottomLeftY = -0.5 * (mcf2rl * areaHeight) - adjustment
        frameWidth = mcf2rl * areaWidth + 2 * adjustment
        frameHeight = mcf2rl * areaHeight + 2 * adjustment

        if hasImplementedCorners(cornersInfo):
            path = buildCornerPath(pdf, frameBottomLeftX, frameBottomLeftY,
                                   frameWidth, frameHeight, mcf2rl,
                                   cornersInfo, adjustment)
            pdf.saveState()
            pdf.setLineWidth(borderWidth)
            pdf.setStrokeColor(borderColor)
            pdf.drawPath(path, stroke=1, fill=0)
            pdf.restoreState()
        else:
            # Preserve the historic Table rendering for rectangular borders so
            # existing regression PDFs remain unchanged.
            borderTable = Table(
                data=[[None]], colWidths=frameWidth, rowHeights=frameHeight,
                style=[
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('BOX', (0, 0), (0, 0), borderWidth, borderColor),
                    ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                ])
            borderTable.wrapOn(pdf, frameWidth, frameHeight)
            borderTable.drawOn(pdf, frameBottomLeftX, frameBottomLeftY)
