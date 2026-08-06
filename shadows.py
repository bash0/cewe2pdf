"""Shadow geometry and alpha-silhouette rendering helpers."""

import tempfile

import numpy as np
from PIL import Image, ImageFilter
import reportlab.lib.colors
from reportlab.lib.utils import ImageReader


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
                           shadowWidth_mcfunit, mcf2rl, tempFileList):
    """
    Draw a blurred, transparent shadow using the image's existing alpha mask.

    ``tempFileList`` belongs to the caller's PDF-generation lifecycle. The
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
    tempFileList.append(shadowFile.name)

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
