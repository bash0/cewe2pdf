"""Rendering of CEWE image and image-background areas."""

import logging
import os
import tempfile
from math import sqrt

import PIL
from reportlab.lib.utils import ImageReader

from ceweInfo import AlbumInfo
from clipArt import getClipConfig, loadClipart
from clipartareas import insertClipartFile
from conversionState import ConversionState
from corners import applyCornerMask, getCornersInfo
from imageUtils import autorot
from passepartout import Passepartout
from renderContext import RenderContext


def processAreaImageTag(imageTag, area, areaHeight, areaRot, areaWidth, imageDirectory,
                        productStyle, mcfBaseFolder, pageType, pdf, pageWidth,
                        transx, transy, context: RenderContext, state: ConversionState,
                        drawShadow, drawBorders):
    """Crop, decorate and draw one CEWE image area."""
    if imageTag.get('filename') is None:
        return

    mcf2rl = context.mcf_to_reportlab
    imagePath = os.path.join(mcfBaseFolder, imageDirectory, imageTag.get('filename'))
    # The layout software copies the images to another collection folder.
    imagePath = imagePath.replace('safecontainer:/', '')
    image = PIL.Image.open(imagePath)

    imageTransx = transx
    if (imageTag.get('backgroundPosition') == 'RIGHT_OR_BOTTOM' and
            AlbumInfo.isAlbumDoubleSide(productStyle)):
        # A double-side output canvas still uses the full CEWE spread.  The
        # background position identifies its right half.  In single-side
        # output, pageElements has already moved that half to local page
        # coordinates, so applying another page-width shift would draw the
        # image completely off the PDF page.
        imageTransx += mcf2rl * pageWidth / 2

    # The source image is first cropped in MCF coordinates, then resized for
    # the output PDF. Decorations are applied to that final crop so masks,
    # corners, shadows and borders all describe the visible image rather than
    # the original photograph.
    image = autorot(image)
    imageLeft = float(imageTag.find('cutout').get('left').replace(',', '.'))
    imageTop = float(imageTag.find('cutout').get('top').replace(',', '.'))
    imageScale = float(imageTag.find('cutout').get('scale'))

    passepartoutId = imageTag.get('passepartoutDesignElementId')
    frameClipartFileName = None
    maskClipartFileName = None
    frameDeltaX_mcfunit = 0
    frameDeltaY_mcfunit = 0
    frameAlpha = 255
    imageCropWidth_mcfunit = areaWidth
    imageCropHeight_mcfunit = areaHeight
    if passepartoutId is not None:
        passepartoutId = int(passepartoutId)
        if state.passepartout_files is None:
            logging.info("Regenerating passepartout index from .XML files.")
            state.passepartout_files = Passepartout.buildElementIdIndex(context.passepartout_folders)
        try:
            passepartoutXmlFileName = state.passepartout_files[passepartoutId]
        except KeyError:
            passepartoutXmlFileName = None
        if passepartoutXmlFileName is None:
            logging.warning(f"Could not find passepartout {passepartoutId}; rendering the unframed image.")
        else:
            passepartoutInfo = Passepartout.extractInfoFromXml(passepartoutXmlFileName, passepartoutId)
            frameClipartFileName = Passepartout.getClipartFullName(passepartoutInfo)
            maskClipartFileName = Passepartout.getMaskFullName(passepartoutInfo)
            logging.debug(f"Using mask file: {maskClipartFileName}")
            if passepartoutInfo.fotoarea_x is not None:
                frameDeltaX_mcfunit = passepartoutInfo.fotoarea_x * areaWidth
                frameDeltaY_mcfunit = passepartoutInfo.fotoarea_y * areaHeight
                imageCropWidth_mcfunit = passepartoutInfo.fotoarea_width * areaWidth
                imageCropHeight_mcfunit = passepartoutInfo.fotoarea_height * areaHeight

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
        image = maskClipart.applyAsAlphaMaskToFoto(image)

    cornersInfo = getCornersInfo(area)
    image = applyCornerMask(image, cornersInfo, imageCropWidth_mcfunit)

    temporaryImage = tempfile.NamedTemporaryFile()
    # The file must be closed before PIL can reopen it on Windows.
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
    pdf.translate(-frameShiftX_mcf * mcf2rl, -frameShiftY_mcf * mcf2rl)

    for decorationTag in area.findall('decoration'):
        drawShadow(decorationTag, areaHeight, areaWidth, pdf, context, state,
                   image, imageCropWidth_mcfunit, imageCropHeight_mcfunit)

    pdf.drawImage(ImageReader(temporaryImage.name),
                  mcf2rl * -0.5 * imageCropWidth_mcfunit,
                  mcf2rl * -0.5 * imageCropHeight_mcfunit,
                  width=mcf2rl * imageCropWidth_mcfunit,
                  height=mcf2rl * imageCropHeight_mcfunit, mask='auto')
    pdf.translate(frameShiftX_mcf * mcf2rl, frameShiftY_mcf * mcf2rl)

    if frameClipartFileName is not None:
        colorReplacements, _flipX, _flipY = getClipConfig(imageTag)
        insertClipartFile(frameClipartFileName, colorReplacements, 0, areaWidth,
                          areaHeight, frameAlpha, pdf, 0, 0, False, False,
                          None, context)

    for decorationTag in area.findall('decoration'):
        drawBorders(decorationTag, areaHeight, areaWidth, pdf, context, cornersInfo)

    pdf.rotate(areaRot)
    pdf.translate(-imageTransx, -transy)

    state.temporary_files.append(temporaryImage.name)
