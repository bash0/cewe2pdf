"""Rendering of CEWE image and image-background areas."""

import logging
import os
import re
import tempfile
from io import BytesIO
from math import sqrt

import PIL
from reportlab.lib.utils import ImageReader
import cairosvg
from clipart.catalog import getClipConfig, loadClipart
from clipart.areas import hasEnabledShadow, insertClipartFile
from conversionState import ConversionState
from decorations.corners import applyCornerMask, getCornersInfo
from decorations.passepartout import Passepartout
from imageUtils import autorot, getMapUrlFromExif
from infrastructure.configUtils import getConfigurationBool
from renderContext import RenderContext


def _getDecorationOpacity(area):
    """Return an image area's CEWE decoration opacity as a value from 0 to 1."""
    decoration = area.find('decoration')
    if decoration is None or decoration.get('alpha') is None:
        return 1

    alphaText = decoration.get('alpha')
    try:
        return max(0, min(1, float(alphaText)))
    except ValueError:
        logging.warning('Ignoring invalid image decoration alpha %r', alphaText)
        return 1


def _applyDecorationAlpha(image, area):
    """Apply a CEWE image area's optional decoration opacity to ``image``.

    CEWE stores an area's opacity on its ``decoration`` element, for both
    clipart and photographs.  Preserve any alpha already supplied by the
    source image, a passepartout mask, or a corner mask by scaling rather
    than replacing its alpha channel.
    """
    opacity = _getDecorationOpacity(area)

    if opacity == 1:
        return image

    image = image.convert('RGBA')
    image.putalpha(image.getchannel('A').point(lambda value: int(value * opacity)))
    return image


def _isSavedIndexImage(imageFileName, outputFileName):
    """Return whether a CEWE resource is a previously generated index PNG.

    The album editor prefixes files copied into ``safecontainer:`` with its
    own identifier.  The meaningful suffix remains our output stem followed
    by ``.idx``.  Test output names add ``.YYYYMMDDS`` while ordinary runs use
    ``.S`` or ``.D``; remove either suffix so an album saved after an earlier
    run is recognised too.
    """
    if not outputFileName or not imageFileName.startswith('safecontainer:/'):
        return False

    imageName = os.path.basename(imageFileName).casefold()
    outputStem = os.path.splitext(os.path.basename(outputFileName))[0].casefold()
    stableStem = re.sub(r'\.\d{8}[sd]$', '', outputStem)
    stems = {outputStem, stableStem}
    for stem in stems:
        # CEWE adds a prefix ending in an underscore.  Current output always
        # uses '.idx.<number>.png'; accept the old '.idx.png' convention too
        # so existing CEWE albums can still have their stale index removed.
        pattern = rf'(?:^|_){re.escape(stem)}(?:\.[sd])?\.idx(?:\.\d+)?\.png$'
        if re.search(pattern, imageName):
            return True
    return False


def _drawPassepartoutShadow(photo, imageTag, area, xmlInfo, pdf, context, state, drawShadow):
    """Paint the combined silhouette while the canvas is at the full frame centre."""
    if (xmlInfo is None or xmlInfo.clipartFile is None
            or not any(hasEnabledShadow(tag) for tag in area.findall('decoration'))
            or getConfigurationBool(context.default_config_section, 'noShadows', 'False')):
        return False
    position = area.find('position')
    areaWidth = float(position.get('width').replace(',', '.'))
    areaHeight = float(position.get('height').replace(',', '.'))
    areaRotation = float(position.get('rotation'))
    colorReplacements, flipX, flipY = getClipConfig(imageTag)
    shadowImage = Passepartout.createShadowImage(photo, xmlInfo, areaWidth, areaHeight,
        int(_getDecorationOpacity(area) * 255), colorReplacements, context, flipX, flipY)
    if shadowImage is None:
        return False
    for decorationTag in area.findall('decoration'):
        drawShadow(decorationTag, areaHeight, areaWidth, pdf, context, state,
            shadowImage, areaWidth, areaHeight, areaRotation=areaRotation)
    return True


def _getPassepartoutInfo(imageTag, context, state):
    """Resolve a frame/mask through the conversion's shared resource catalogue."""
    passepartoutId = imageTag.get('passepartoutDesignElementId')
    if passepartoutId is None:
        return None
    passepartoutId = int(passepartoutId)
    if state.passepartout_files is None:
        logging.info('Regenerating passepartout index from .XML files.')
        state.passepartout_files = Passepartout.buildElementIdIndex(context.passepartout_folders)
    filename = state.passepartout_files.get(passepartoutId)
    if filename is None:
        logging.warning(f'Could not find passepartout {passepartoutId}; rendering the unframed image.')
        return None
    return Passepartout.extractInfoFromXml(filename, passepartoutId)


def _drawEmptyImageFrame(imageTag, area, pdf, centre, context, state):
    """CEWE prints an empty passepartout's artwork, leaving its photo opening clear."""
    info = _getPassepartoutInfo(imageTag, context, state)
    if info is None or info.clipartFile is None:
        return
    position = area.find('position')
    width, height, rotation = (float(position.get(name, '0').replace(',', '.'))
        for name in ('width', 'height', 'rotation'))
    replacements, flipX, flipY = getClipConfig(imageTag)
    pdf.saveState()
    try:
        pdf.translate(*centre)
        pdf.rotate(-rotation)
        # Empty frames in CEWE's print preview show the artwork itself, without
        # the photo's border/shadow or a grey editor placeholder. A mask without
        # separate artwork has nothing visible to draw until a photo is supplied.
        insertClipartFile(Passepartout.getClipartFullName(info), replacements, 0,
            width, height, int(_getDecorationOpacity(area) * 255), pdf, 0, 0,
            flipX, flipY, None, context)
    finally:
        pdf.restoreState()


# Keep the shared page-renderer signature and legacy crop pipeline together;
# productStyle/pageWidth remain accepted for caller compatibility.
# pylint: disable-next=too-many-arguments,too-many-locals,too-many-statements
def processAreaImageTag(imageTag, area, areaHeight, areaRot, areaWidth, imageDirectory,
                        productStyle, mcfBaseFolder, pageType, pdf, pageWidth,  # pylint: disable=unused-argument
                        transx, transy, context: RenderContext, state: ConversionState,
                        drawShadow, drawBorders):
    """Crop, decorate and draw one CEWE image area."""
    if not imageTag.get('filename'):
        _drawEmptyImageFrame(imageTag, area, pdf, (transx, transy), context, state)
        return

    mcf2rl = context.mcf_to_reportlab
    imageFileName = imageTag.get('filename')
    if _isSavedIndexImage(imageFileName, state.output_file_name):
        logging.info(f'Omitting previously generated index image {imageFileName}')
        return

    imagePath = os.path.join(mcfBaseFolder, imageDirectory, imageFileName)
    # The layout software copies the images to another collection folder.
    imagePath = imagePath.replace('safecontainer:/', '')
    if not os.path.isfile(imagePath):
        # An MCF can retain a reference to a previously generated index image
        # after that temporary PNG has been removed. Do not let one stale
        # optional image prevent the page text and a replacement index from
        # rendering; the missing image is reported for ordinary photos too.
        logging.warning(f'Could not find image file {imagePath}; image omitted.')
        return
    if imagePath.lower().endswith('.svg'):
        with open(imagePath, 'rb') as svgFile:
            pngData = cairosvg.svg2png(bytestring=svgFile.read())
        image = PIL.Image.open(BytesIO(pngData))
        image.load()
    else:
        image = PIL.Image.open(imagePath)

    geoLinkUrl = (getMapUrlFromExif(image, context.geo_link_url_template)
                  if context.geo_links_enabled else None)

    # ``transx`` already contains the MCF area's position.  In a double-page
    # output a RIGHT_OR_BOTTOM background area therefore already lies in the
    # right half of the spread; applying a second half-page offset would put
    # it beyond the canvas.  For a single-page output, pageElements has
    # already made the equivalent move into local page coordinates.
    imageTransx = transx

    # The source image is first cropped in MCF coordinates, then resized for
    # the output PDF. Decorations are applied to that final crop so masks,
    # corners, shadows and borders all describe the visible image rather than
    # the original photograph.
    image = autorot(image)
    imageLeft = float(imageTag.find('cutout').get('left').replace(',', '.'))
    imageTop = float(imageTag.find('cutout').get('top').replace(',', '.'))
    imageScale = float(imageTag.find('cutout').get('scale'))

    passepartoutId = imageTag.get('passepartoutDesignElementId')
    passepartoutInfo = None
    frameClipartFileName = None
    maskClipartFileName = None
    colorReplacements, flipX, flipY = [], False, False
    frameDeltaX_mcfunit = 0
    frameDeltaY_mcfunit = 0
    # A passepartout has a separately drawn frame as well as the masked photo.
    # CEWE applies the image area's decoration opacity to both components.
    frameAlpha = int(_getDecorationOpacity(area) * 255)
    imageCropWidth_mcfunit = areaWidth
    imageCropHeight_mcfunit = areaHeight
    if passepartoutId is not None:
        passepartoutInfo = _getPassepartoutInfo(imageTag, context, state)
        if passepartoutInfo is not None:
            colorReplacements, flipX, flipY = getClipConfig(imageTag)
            frameClipartFileName = Passepartout.getClipartFullName(passepartoutInfo)
            maskClipartFileName = Passepartout.getMaskFullName(passepartoutInfo)
            logging.debug(f"Using mask file: {maskClipartFileName}")
            fotoareaX, fotoareaY, fotoareaWidth, fotoareaHeight = Passepartout.getFotoarea(
                passepartoutInfo, flipX, flipY)
            frameDeltaX_mcfunit = fotoareaX * areaWidth
            frameDeltaY_mcfunit = fotoareaY * areaHeight
            imageCropWidth_mcfunit = fotoareaWidth * areaWidth
            imageCropHeight_mcfunit = fotoareaHeight * areaHeight

    # Crop co-ordinates can lie outside the image. Pillow fills that area with
    # black, which is acceptable for the exceptional passepartout case.
    cropLeft = int(0.5 - imageLeft / imageScale + 0 * frameDeltaX_mcfunit / imageScale)
    cropUpper = int(0.5 - imageTop / imageScale + 0 * frameDeltaY_mcfunit / imageScale)
    cropRight = int(0.5 - imageLeft / imageScale + 0 * frameDeltaX_mcfunit / imageScale +
                    imageCropWidth_mcfunit / imageScale)
    cropLower = int(0.5 - imageTop / imageScale + 0 * frameDeltaY_mcfunit / imageScale +
                    imageCropHeight_mcfunit / imageScale)
    image = image.crop((cropLeft, cropUpper, cropRight, cropLower))

    # Retain the established page-type check, including its historical string
    # comparison, so this extraction does not change rendered output.
    if imageTag.tag == 'imagebackground' and pageType != 'cover':
        resolution = context.background_resolution
    else:
        resolution = context.image_resolution
    newWidth = int(0.5 + imageCropWidth_mcfunit * resolution / 254.0)
    newHeight = int(0.5 + imageCropHeight_mcfunit * resolution / 254.0)
    factor = sqrt(newWidth * newHeight / float(image.size[0] * image.size[1]))
    if factor <= 0.8:
        image = image.resize((newWidth, newHeight), context.image_resampling_filter)
    image.load()

    if maskClipartFileName is not None:
        maskClipart = loadClipart(maskClipartFileName, context.clipart_paths)
        image = maskClipart.applyAsAlphaMaskToFoto(image, flipX, flipY)

    cornersInfo = getCornersInfo(area)
    image = applyCornerMask(image, cornersInfo, imageCropWidth_mcfunit)
    image = _applyDecorationAlpha(image, area)

    # ConversionState owns the file lifetime; close the handle before PIL can
    # reopen it on Windows rather than limiting its lifetime to a with block.
    temporaryImage = tempfile.NamedTemporaryFile()  # pylint: disable=consider-using-with
    temporaryImage.close()
    if image.mode in ('RGBA', 'P'):
        image.save(temporaryImage.name, "PNG")
    else:
        image.save(temporaryImage.name, "JPEG", quality=context.image_quality)

    logging.debug(f"image: {imageTag.get('filename')}")
    pdf.translate(imageTransx, transy)
    pdf.rotate(-areaRot)

    frameShiftX_mcf = -(frameDeltaX_mcfunit -
        ((areaWidth - imageCropWidth_mcfunit) - frameDeltaX_mcfunit)) / 2
    frameShiftY_mcf = (frameDeltaY_mcfunit -
        ((areaHeight - imageCropHeight_mcfunit) - frameDeltaY_mcfunit)) / 2

    # Paint one shadow behind both foreground components before applying the
    # photo's fotoarea offset. Mask-only passepartouts retain the photo path.
    hasFrameShadow = _drawPassepartoutShadow(
        image, imageTag, area, passepartoutInfo, pdf, context, state, drawShadow)
    pdf.translate(-frameShiftX_mcf * mcf2rl, -frameShiftY_mcf * mcf2rl)

    if not hasFrameShadow:
        for decorationTag in area.findall('decoration'):
            drawShadow(decorationTag, areaHeight, areaWidth, pdf, context, state,
                image, imageCropWidth_mcfunit, imageCropHeight_mcfunit,
                areaRotation=areaRot)

    pdf.drawImage(ImageReader(temporaryImage.name),
                  mcf2rl * -0.5 * imageCropWidth_mcfunit,
                  mcf2rl * -0.5 * imageCropHeight_mcfunit,
                  width=mcf2rl * imageCropWidth_mcfunit,
                  height=mcf2rl * imageCropHeight_mcfunit, mask='auto')
    if geoLinkUrl is not None:
        # Relative coordinates use the photograph's existing CEWE transforms,
        # including rotation and double-page positioning.
        hotspotSize_mcfunit = min(
            context.geo_link_hotspot_size_mm * 10,
            imageCropWidth_mcfunit, imageCropHeight_mcfunit)
        left = -0.5 * imageCropWidth_mcfunit
        top = 0.5 * imageCropHeight_mcfunit
        pdf.linkURL(
            geoLinkUrl,
            (mcf2rl * left,
             mcf2rl * (top - hotspotSize_mcfunit),
             mcf2rl * (left + hotspotSize_mcfunit),
             mcf2rl * top),
            relative=True, thickness=0)
    pdf.translate(frameShiftX_mcf * mcf2rl, frameShiftY_mcf * mcf2rl)

    if frameClipartFileName is not None:
        insertClipartFile(frameClipartFileName, colorReplacements, 0, areaWidth,
                          areaHeight, frameAlpha, pdf, 0, 0, flipX, flipY,
                          None, context)

    for decorationTag in area.findall('decoration'):
        drawBorders(decorationTag, areaHeight, areaWidth, pdf, context, cornersInfo)

    pdf.rotate(areaRot)
    pdf.translate(-imageTransx, -transy)

    state.temporary_files.append(temporaryImage.name)
