"""Shadow geometry and alpha-silhouette rendering helpers."""

import tempfile
import logging
from math import floor

import numpy as np
from PIL import Image, ImageFilter
import reportlab.lib.colors
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table

from configUtils import getConfigurationBool
from conversionState import ConversionState
from renderContext import RenderContext

def findShadowBottomLeft(frameBottomLeft, angle, distance, swidth):
    """Return the lower-left corner of a legacy rectangular shadow."""
    x, y = frameBottomLeft
    if distance < 0.001:
        # The existing rectangular-shadow geometry requires this special case.
        return x - swidth / 2, y - swidth / 2

    angle_rad = np.radians(angle - 90)
    shadow_dx = distance * np.cos(angle_rad)
    shadow_dy = -distance * np.sin(angle_rad)
    return x + shadow_dx - swidth / 2, y + shadow_dy - swidth / 2


def intensityToGrey(value):
    """Convert CEWE's 1..255 shadow intensity to a ReportLab grey colour."""
    colorComponentValue = 1 - (max(1, min(255, value)) / 255)
    return reportlab.lib.colors.Color(colorComponentValue,
                                      colorComponentValue,
                                      colorComponentValue)


def drawBlurredImageShadow(pdf, im, imgCropWidth_mcfunit,
                           imgCropHeight_mcfunit, shadowDistance_mcfunit,
                           shadowAngle, intensity, shadowBlur_mcfunit,
                           shadowWidth_mcfunit, mcf2rl, temporary_files):
    """
    Draw a blurred, transparent shadow using the image's existing alpha mask.

    ``temporary_files`` belongs to the caller's PDF-generation lifecycle. The
    generated PNG is therefore retained until the PDF has been completed.
    """
    if im.mode != 'RGBA':
        im = im.convert('RGBA')

    # MCF geometry is in 0.1 mm while Pillow needs pixels.  Use the final,
    # cropped image dimensions: they remain correct whether or not the image
    # was downsampled earlier in processAreaImageTag.
    pixelsPerMcfunit = im.width / imgCropWidth_mcfunit

    # CEWE's displayed shadow expands by about three quarters of the nominal
    # half-width on each side. This was measured from the width-only test page
    # (0 .. 10 mm); the old ReportLab Table is noticeably larger at high values.
    spreadRadius_px = int(round(
        shadowWidth_mcfunit * pixelsPerMcfunit * 0.375
    ))

    # shadowBlurNew is stored in MCF units. Pillow's GaussianBlur has a wider
    # visible tail than CEWE's editor, so use half the nominal radius. A
    # three-radius transparent margin prevents that tail being clipped.
    # Keep the fractional radius: rounding it would make several of CEWE's
    # small blur settings render identically at the configured image DPI.
    blurRadius_px = shadowBlur_mcfunit * pixelsPerMcfunit * 0.5
    padding_px = spreadRadius_px + int(np.ceil(3 * blurRadius_px))

    alpha = im.getchannel('A')
    shadowAlpha = Image.new(
        'L', (im.width + 2 * padding_px, im.height + 2 * padding_px), 0
    )
    shadowAlpha.paste(alpha, (padding_px, padding_px))

    if spreadRadius_px > 0:
        shadowAlpha = shadowAlpha.filter(
            ImageFilter.MaxFilter(2 * spreadRadius_px + 1)
        )

    if blurRadius_px > 0:
        shadowAlpha = shadowAlpha.filter(ImageFilter.GaussianBlur(blurRadius_px))

    # CEWE's intensity maps directly to black alpha: an intensity of 128
    # produces the mid-grey core seen in the editor, while zero disables it.
    shadowOpacity = max(0, min(255, intensity)) / 255
    shadowAlpha = shadowAlpha.point(
        lambda value: int(round(value * shadowOpacity))
    )
    shadowImage = Image.new('RGBA', shadowAlpha.size, (0, 0, 0, 0))
    shadowImage.putalpha(shadowAlpha)

    # ReportLab handles the PNG alpha channel when mask='auto' is used below.
    shadowFile = tempfile.NamedTemporaryFile() # pylint:disable=consider-using-with
    shadowFile.close()
    shadowImage.save(shadowFile.name, 'PNG')
    temporary_files.append(shadowFile.name)

    # CEWE stores the direction in the same convention used by the older
    # vector shadow code: the angle identifies where the shadow is cast, not
    # the light source. The Y calculation is in PDF coordinates (Y upwards).
    angleRadians = np.radians(shadowAngle - 90)
    # The editor casts a shadow about three quarters of the stored distance.
    # This is independently visible in the angle and distance test pages.
    shadowDistanceScale = 0.75
    shadowOffsetX_mcfunit = shadowDistanceScale * shadowDistance_mcfunit * np.cos(angleRadians)
    shadowOffsetY_mcfunit = -shadowDistanceScale * shadowDistance_mcfunit * np.sin(angleRadians)
    padding_mcfunit = padding_px / pixelsPerMcfunit

    pdf.drawImage(
        ImageReader(shadowFile.name),
        mcf2rl * (-0.5 * imgCropWidth_mcfunit - padding_mcfunit
                  + shadowOffsetX_mcfunit),
        mcf2rl * (-0.5 * imgCropHeight_mcfunit - padding_mcfunit
                  + shadowOffsetY_mcfunit),
        width=mcf2rl * (imgCropWidth_mcfunit + 2 * padding_mcfunit),
        height=mcf2rl * (imgCropHeight_mcfunit + 2 * padding_mcfunit),
        mask='auto'
    )


def processDecorationShadow(decoration, areaHeight, areaWidth, pdf,
                            context: RenderContext, state: ConversionState, im=None,
                            imgCropWidth_mcfunit=None,
                            imgCropHeight_mcfunit=None):
    """Draw an enabled CEWE shadow decoration for an already-positioned area."""
    if getConfigurationBool(context.default_config_section, "noShadows", "False"):
        return

    mcf2rl = context.mcf_to_reportlab
    frameBottomLeftX = -0.5 * (mcf2rl * areaWidth)
    frameBottomLeftY = -0.5 * (mcf2rl * areaHeight)
    frameWidth = mcf2rl * areaWidth
    frameHeight = mcf2rl * areaHeight

    for shadow in decoration.findall('shadow'):
        if shadow.get('shadowEnabled') is not None and shadow.get('shadowEnabled') != '1':
            continue

        shadowWidth = 1
        shadowWidth_mcfunit = shadowWidth / mcf2rl
        widthText = shadow.get('shadowWidthInMM')
        if widthText is not None:
            shadowWidth_mcfunit = floor(float(widthText) * 10)
            shadowWidth = mcf2rl * shadowWidth_mcfunit

        shadowDistance = 10
        shadowDistance_mcfunit = shadowDistance / mcf2rl
        distanceText = shadow.get('shadowDistance')
        if distanceText is not None:
            shadowDistance_mcfunit = floor(float(distanceText))
            shadowDistance = mcf2rl * shadowDistance_mcfunit

        intensity = 128
        intensityText = shadow.get('shadowIntensity')
        if intensityText is not None:
            intensity = int(intensityText)

        shadowBlur_mcfunit = 0
        blurText = shadow.get('shadowBlurNew')
        if blurText is not None:
            shadowBlur_mcfunit = float(blurText)

        shadowAngle = 135
        angleText = shadow.get('shadowAngle')
        if angleText is not None:
            shadowAngle = floor(float(angleText))
        if shadowAngle < 0.0:
            shadowAngle = shadowAngle + 360

        if im is not None:
            drawBlurredImageShadow(
                pdf, im, imgCropWidth_mcfunit, imgCropHeight_mcfunit,
                shadowDistance_mcfunit, shadowAngle, intensity,
                shadowBlur_mcfunit, shadowWidth_mcfunit, mcf2rl,
                state.temporary_files
            )
        else:
            shadowBottomLeftX, shadowBottomLeftY = findShadowBottomLeft(
                (frameBottomLeftX, frameBottomLeftY), shadowAngle,
                shadowDistance, shadowWidth)
            shadowTable = Table(
                data=[[None]],
                colWidths=frameWidth + shadowWidth,
                rowHeights=frameHeight + shadowWidth,
                style=[
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('BACKGROUND', (0, 0), (0, 0), intensityToGrey(intensity)),
                    ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                ])
            shadowTable.wrapOn(pdf, frameWidth + shadowWidth, frameHeight + shadowWidth)
            shadowTable.drawOn(pdf, shadowBottomLeftX, shadowBottomLeftY)


def warnAndIgnoreEnabledDecorationShadow(decoration, context: RenderContext):
    """Explain the known limitation for shadow decorations on text areas."""
    if getConfigurationBool(context.default_config_section, "noShadows", "False"):
        return
    for shadow in decoration.findall('shadow'):
        if shadow.get('shadowEnabled') == '1':
            logging.warning("Ignoring shadow specified on text, that is not implemented!")
