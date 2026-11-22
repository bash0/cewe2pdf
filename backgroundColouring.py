"""Conservative HSV approximation of CEWE's textured background recolouring."""

import logging
from math import isfinite

from PIL import Image


def getBackgroundRecolouring(backgroundTag):
    """Return a validated (hue, fading) pair, or retain the original image.

    Explicit MCF colour settings request recolouring regardless of the design
    ID. The HSV approximation and supported fading settings were calibrated
    with design 485 and a synthetic image substituted for 6480.
    """
    hueText = backgroundTag.get('hue')
    fadingText = backgroundTag.get('fading')
    # Missing colour settings retain the source image. Explicit hue/fading zero
    # instead selects red with the source saturation intact (6480 pages 16-17).
    if hueText is None and fadingText is None:
        return None
    try:
        hue = float(hueText) if hueText is not None else 0.0
        fading = float(fadingText) if fadingText is not None else 0.0
        hasColourSettings = hueText is not None and fadingText is not None
        if (backgroundTag.get('type', '1') == '1'
                and hasColourSettings
                and isfinite(hue) and fading in (0, 1, 2, 3, 4, 5)):
            return hue, fading
    except ValueError:
        # Malformed optional colour attributes must not hide a valid image.
        pass
    logging.warning(
        f"Unsupported background recolouring for design {backgroundTag.get('designElementId')}: "
        f"hue={hueText}, fading={fadingText}; using the original background image.")
    return None


def recolourBackground(image, hue, fading):
    """Replace hue, scale source saturation and preserve the source HSV value.

    The synthetic 6480 preview retains grey pixels and the saturation ratio
    between its two colour strips. Fully saturated pixels give approximately
    255, 128, 64, 180 and 45 on Pillow's 0-255 saturation scale for fading 0, 1, 2, 3
    and 5. Fading 4's intermediate factor is supported by the 485 comparison.
    These are empirical settings, not a general fading formula. Pillow's 8-bit
    HSV introduces rounding errors. No brightness calibration is applied.
    """
    if not isfinite(hue):
        raise ValueError('Background hue must be finite')
    if fading not in (0, 1, 2, 3, 4, 5):
        raise ValueError(f'Unsupported background fading: {fading}')
    saturationScale = {0: 1.0, 1: 0.5, 2: 0.25, 3: 180 / 255, 4: 90 / 255, 5: 45 / 255}[fading]
    hsv = image.convert('RGB').convert('HSV')
    value = hsv.getchannel('V')
    hueChannel = Image.new('L', image.size, round((hue % 360) / 360 * 255))
    saturationChannel = hsv.getchannel('S').point([
        round(saturation * saturationScale) for saturation in range(256)])
    result = Image.merge('HSV', (hueChannel, saturationChannel, value)).convert('RGB')
    if 'A' in image.getbands() or 'transparency' in image.info:
        result.putalpha(image.convert('RGBA').getchannel('A'))
    return result
