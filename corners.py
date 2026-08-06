"""Corner-decoration parsing and geometry helpers."""

import logging
from enum import Enum
from typing import NamedTuple

from PIL import Image, ImageChops, ImageDraw


class CornerShape(Enum):
    Default = "default"
    Convex = "convex"
    Notched = "notched"
    Bevelled = "bevelled"
    Unknown = "unknown"


class CornerInfo(NamedTuple):
    shape: CornerShape = CornerShape.Default
    length_mcf: float = 0


class CornersInfo(NamedTuple):
    topLeft: CornerInfo = CornerInfo()
    topRight: CornerInfo = CornerInfo()
    bottomLeft: CornerInfo = CornerInfo()
    bottomRight: CornerInfo = CornerInfo()


def getCornerInfo(corners, where):
    """Return shape and length, in MCF units, for one named corner."""
    corner = corners.find(f"corner[@where='{where}']")
    if corner is None:
        return CornerInfo()

    cornerLength = corner.get('length')
    cornerShapeText = corner.get('shape', 'default')

    try:
        cornerShape = CornerShape(cornerShapeText)
    except ValueError:
        cornerShape = CornerShape.Unknown

    if cornerLength is None:
        return CornerInfo(cornerShape, 0)

    return CornerInfo(cornerShape, float(cornerLength))


def getCornersInfo(area):
    """Return shape and length information for all enabled image corners."""
    for decoration in area.findall('decoration'):
        for corners in decoration.findall('corners'):
            if corners.get('enabled') != 'yes':
                continue

            return CornersInfo(
                topLeft=getCornerInfo(corners, 'top-left'),
                topRight=getCornerInfo(corners, 'top-right'),
                bottomLeft=getCornerInfo(corners, 'bottom-left'),
                bottomRight=getCornerInfo(corners, 'bottom-right')
            )

    return CornersInfo()


def buildCornerPath(pdf, left, bottom, width, height, mcf2rl,
                    cornersInfo=None, radiusAdjustment=0):
    """
    Build a PDF path for a rectangle with optional convex or bevelled corners.

    radiusAdjustment expands or contracts the outline, for example when a
    border is inside or outside the image area.
    """
    kappa = 0.5522847498

    if cornersInfo is None:
        path = pdf.beginPath()
        path.moveTo(left, bottom)
        path.lineTo(left + width, bottom)
        path.lineTo(left + width, bottom + height)
        path.lineTo(left, bottom + height)
        path.close()
        return path

    def getRadius(cornerInfo):
        if cornerInfo.shape not in (
                CornerShape.Convex, CornerShape.Bevelled):
            return 0

        radius = mcf2rl * cornerInfo.length_mcf + radiusAdjustment
        return max(0, min(radius, width / 2, height / 2))

    topLeftRadius = getRadius(cornersInfo.topLeft)
    topRightRadius = getRadius(cornersInfo.topRight)
    bottomLeftRadius = getRadius(cornersInfo.bottomLeft)
    bottomRightRadius = getRadius(cornersInfo.bottomRight)

    topLeftShape = cornersInfo.topLeft.shape if topLeftRadius > 0 else CornerShape.Default
    topRightShape = cornersInfo.topRight.shape if topRightRadius > 0 else CornerShape.Default
    bottomLeftShape = cornersInfo.bottomLeft.shape if bottomLeftRadius > 0 else CornerShape.Default
    bottomRightShape = cornersInfo.bottomRight.shape if bottomRightRadius > 0 else CornerShape.Default

    right = left + width
    top = bottom + height

    path = pdf.beginPath()
    path.moveTo(left + bottomLeftRadius, bottom)

    path.lineTo(right - bottomRightRadius, bottom)
    if bottomRightShape == CornerShape.Convex:
        radius = bottomRightRadius
        path.curveTo(right - radius + kappa * radius, bottom,
                     right, bottom + radius - kappa * radius,
                     right, bottom + radius)
    elif bottomRightShape == CornerShape.Bevelled:
        path.lineTo(right, bottom + bottomRightRadius)
    else:
        path.lineTo(right, bottom)

    path.lineTo(right, top - topRightRadius)
    if topRightShape == CornerShape.Convex:
        radius = topRightRadius
        path.curveTo(right, top - radius + kappa * radius,
                     right - radius + kappa * radius, top,
                     right - radius, top)
    elif topRightShape == CornerShape.Bevelled:
        path.lineTo(right - topRightRadius, top)
    else:
        path.lineTo(right, top)

    path.lineTo(left + topLeftRadius, top)
    if topLeftShape == CornerShape.Convex:
        radius = topLeftRadius
        path.curveTo(left + radius - kappa * radius, top,
                     left, top - radius + kappa * radius,
                     left, top - radius)
    elif topLeftShape == CornerShape.Bevelled:
        path.lineTo(left, top - topLeftRadius)
    else:
        path.lineTo(left, top)

    path.lineTo(left, bottom + bottomLeftRadius)
    if bottomLeftShape == CornerShape.Convex:
        radius = bottomLeftRadius
        path.curveTo(left, bottom + radius - kappa * radius,
                     left + radius - kappa * radius, bottom,
                     left + radius, bottom)
    elif bottomLeftShape == CornerShape.Bevelled:
        path.lineTo(left + bottomLeftRadius, bottom)
    else:
        path.lineTo(left, bottom)

    path.close()
    return path


def hasImplementedCorners(cornersInfo):
    if cornersInfo is None:
        return False
    for cornerInfo in (
            cornersInfo.topLeft,
            cornersInfo.topRight,
            cornersInfo.bottomLeft,
            cornersInfo.bottomRight):
        if (cornerInfo.length_mcf > 0
                and cornerInfo.shape in (
                    CornerShape.Convex, CornerShape.Bevelled)):
            return True
    return False


def applyCornerMask(im, cornersInfo, imgCropWidth_mcfunit):
    """Apply convex and bevelled corner masks to an image."""
    def getCornerRadius_px(cornerInfo):
        if cornerInfo.shape == CornerShape.Default:
            return 0

        radius_px = int(round(
            cornerInfo.length_mcf * im.width / imgCropWidth_mcfunit
        ))
        return max(0, min(radius_px, im.width // 2, im.height // 2))

    topLeftRadius_px = getCornerRadius_px(cornersInfo.topLeft)
    topRightRadius_px = getCornerRadius_px(cornersInfo.topRight)
    bottomLeftRadius_px = getCornerRadius_px(cornersInfo.bottomLeft)
    bottomRightRadius_px = getCornerRadius_px(cornersInfo.bottomRight)

    if max(topLeftRadius_px, topRightRadius_px,
           bottomLeftRadius_px, bottomRightRadius_px) == 0:
        return im

    if im.mode != "RGBA":
        im = im.convert("RGBA")

    width, height = im.size
    mask = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(mask)

    def warnUnimplemented(cornerInfo, where):
        logging.warning(
            f"Corner shape '{cornerInfo.shape.value}' is not implemented; "
            f"ignoring {where} corner decoration."
        )

    if topLeftRadius_px > 0:
        radius = topLeftRadius_px
        cornerInfo = cornersInfo.topLeft
        if cornerInfo.shape == CornerShape.Convex:
            draw.rectangle((0, 0, radius, radius), fill=0)
            draw.pieslice((0, 0, 2 * radius, 2 * radius),
                          start=180, end=270, fill=255)
        elif cornerInfo.shape == CornerShape.Bevelled:
            draw.polygon([(0, 0), (radius, 0), (0, radius)], fill=0)
        else:
            warnUnimplemented(cornerInfo, 'top-left')

    if topRightRadius_px > 0:
        radius = topRightRadius_px
        cornerInfo = cornersInfo.topRight
        if cornerInfo.shape == CornerShape.Convex:
            draw.rectangle((width - radius, 0, width, radius), fill=0)
            draw.pieslice((width - 2 * radius, 0, width, 2 * radius),
                          start=270, end=360, fill=255)
        elif cornerInfo.shape == CornerShape.Bevelled:
            draw.polygon([(width - radius, 0), (width, 0), (width, radius)],
                         fill=0)
        else:
            warnUnimplemented(cornerInfo, 'top-right')

    if bottomLeftRadius_px > 0:
        radius = bottomLeftRadius_px
        cornerInfo = cornersInfo.bottomLeft
        if cornerInfo.shape == CornerShape.Convex:
            draw.rectangle((0, height - radius, radius, height), fill=0)
            draw.pieslice((0, height - 2 * radius, 2 * radius, height),
                          start=90, end=180, fill=255)
        elif cornerInfo.shape == CornerShape.Bevelled:
            draw.polygon([(0, height - radius), (0, height),
                          (radius, height)], fill=0)
        else:
            warnUnimplemented(cornerInfo, 'bottom-left')

    if bottomRightRadius_px > 0:
        radius = bottomRightRadius_px
        cornerInfo = cornersInfo.bottomRight
        if cornerInfo.shape == CornerShape.Convex:
            draw.rectangle((width - radius, height - radius, width, height),
                           fill=0)
            draw.pieslice((width - 2 * radius, height - 2 * radius,
                           width, height), start=0, end=90, fill=255)
        elif cornerInfo.shape == CornerShape.Bevelled:
            draw.polygon([(width - radius, height), (width, height),
                          (width, height - radius)], fill=0)
        else:
            warnUnimplemented(cornerInfo, 'bottom-right')

    # Retain alpha already present, for example from a passepartout mask.
    im.putalpha(ImageChops.multiply(im.getchannel("A"), mask))
    return im
