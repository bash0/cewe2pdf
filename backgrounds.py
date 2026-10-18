"""Background rendering for CEWE book pages."""

from io import BytesIO
import logging

# Background discovery tries several optional file locations; failure in one
# location is expected and is reported before processing continues.
# pylint: disable=broad-exception-caught

import PIL
from reportlab.lib.utils import ImageReader

from ceweInfo import ProductInfo
from infrastructure.configUtils import getConfigurationBool
from infrastructure.extraLoggers import page_rendering
from conversionState import ConversionState
from infrastructure.pathutils import findFileInDirs
from pageTypes import PageProcessingType
from renderContext import RenderContext


def processBackground(backgroundTags, state: ConversionState, backgroundLocations,
                      productstyle, pagetype, pdf, ph, pw, pageNumber,
                      oddPage, lastPage, context: RenderContext,
                      facingBackgroundTags=None):
    """Draw the page background, including special handling for inside covers."""
    areaHeight = ph
    areaWidth = pw
    areaXOffset = 0

    if pagetype == PageProcessingType.OpeningContentPage:
        # This pass processes page 1 after FrontInsideCoverBackground has
        # drawn its alternative endpaper background.
        if ProductInfo.isAlbumSingleSide(productstyle):
            page_rendering.debug(
                'Page %d: not drawing the CEWE front inside-cover/endpaper '
                'in single-sided output.', pageNumber)
            return
        if ProductInfo.isAlbumDoubleSide(productstyle):
            areaWidth = areaWidth / 2

    if pagetype == PageProcessingType.BackInsideCover:
        if ProductInfo.isAlbumSingleSide(productstyle):
            page_rendering.debug(
                'Page %d: not drawing the CEWE back inside-cover/endpaper '
                'in single-sided output.', pageNumber)
            return
        if ProductInfo.isAlbumDoubleSide(productstyle):
            areaWidth = areaWidth / 2
            areaXOffset = areaXOffset + areaWidth

    if pagetype in [PageProcessingType.OpeningContentPage, PageProcessingType.BackInsideCover] and \
            not getConfigurationBool(context.default_config_section, 'insideCoverWhite', 'False'):
        # Returning deliberately uses the already-painted facing content-page
        # background as the endpaper. An explicit configuration setting instead
        # draws CEWE's default white background.
        page_rendering.debug(
            'Page %d: using the %s content-page background as the %s '
            'inside-cover/endpaper (insideCoverWhite=False).',
            pageNumber,
            'first' if pagetype == PageProcessingType.OpeningContentPage else 'last',
            'front' if pagetype == PageProcessingType.OpeningContentPage else 'back')
        return

    _drawBackground(backgroundTags, state, backgroundLocations, productstyle,
                    pagetype, pdf, areaHeight, areaWidth, areaXOffset,
                    pageNumber, oddPage, lastPage, context,
                    facingBackgroundTags)


def _drawBackground(backgroundTags, state: ConversionState, backgroundLocations,
                    productstyle, pagetype, pdf, areaHeight, areaWidth,
                    areaXOffset, pageNumber, oddPage, lastPage,
                    context: RenderContext, facingBackgroundTags=None):
    """Find, load, and draw the selected background image."""
    backgroundTag = next((tag for tag in backgroundTags or []
                          if tag.get('alignment') is not None), None)
    if backgroundTag is None or backgroundTag.get('designElementId') is None:
        return

    isSpreadBackground = (pagetype == PageProcessingType.RegularPage
                          and ProductInfo.isAlbumDoubleSide(productstyle)
                          and _sameBackground(backgroundTag, facingBackgroundTags))
    if isSpreadBackground and oddPage:
        # The even-page operation has already painted this one CEWE spread
        # background across both physical pages.
        return

    if (pagetype == PageProcessingType.RegularPage
            and ProductInfo.isAlbumDoubleSide(productstyle)
            and not lastPage
            and not isSpreadBackground):
        # Individual album pages retain their own background record even
        # though their areas are stored as a two-page CEWE bundle.  Paint that
        # record into its physical half of the PDF spread.  The final content
        # page instead fills the complete spread, because its background is
        # deliberately retained for the facing back endpaper.
        areaWidth = areaWidth / 2
        if oddPage:
            areaXOffset += areaWidth

    bg = backgroundTag.get('designElementId')
    _reportUnsupportedBackgroundAttributes(backgroundTag)
    try:
        bgPath = findFileInDirs([bg + '.bmp', bg + '.webp', bg + '.jpg'],
                                backgroundLocations)
        logging.debug(f"Reading background file: {bgPath}")
        image = PIL.Image.open(bgPath).convert('RGB')
        if pagetype == PageProcessingType.RegularPage and not isSpreadBackground:
            image = _cropBackgroundToArea(
                image, areaWidth, areaHeight, backgroundTag.get('alignment'))
        memFileHandle = BytesIO()
        image.save(memFileHandle, 'jpeg')
        memFileHandle.seek(0)
        _logBackgroundDrawing(pagetype, productstyle, pageNumber, lastPage)
        pdf.drawImage(ImageReader(memFileHandle),
                      context.mcf_to_reportlab * areaXOffset, 0,
                      width=context.mcf_to_reportlab * areaWidth,
                      height=context.mcf_to_reportlab * areaHeight)
    except Exception:
        if bg not in state.background_not_found_paths:
            logging.warning(
                f'Could not find background {bg}; leaving the page background unchanged.')
        state.background_not_found_paths.add(bg)


def _sameBackground(backgroundTag, facingBackgroundTags):
    """Return whether two regular album pages use one CEWE spread background."""
    facingBackgroundTag = next((tag for tag in facingBackgroundTags or []
                                if tag.get('alignment') is not None), None)
    return (facingBackgroundTag is not None
            and backgroundTag.get('designElementId') ==
            facingBackgroundTag.get('designElementId'))


def _cropBackgroundToArea(image, areaWidth, areaHeight, alignment):
    """Crop a background without distorting it, respecting CEWE alignment.

    CEWE's values 1, 2 and 3 mean left, centre and right respectively.  They
    select the horizontal part of an image when its aspect ratio is wider than
    the destination area.  A portrait source needs vertical cropping instead;
    CEWE has no vertical background alignment value, so retain its centre.
    """
    targetRatio = areaWidth / areaHeight
    sourceRatio = image.width / image.height
    if sourceRatio > targetRatio:
        cropWidth = int(round(image.height * targetRatio))
        availableWidth = image.width - cropWidth
        horizontalPosition = {'1': 0, '2': 0.5, '3': 1}.get(alignment, 0.5)
        left = int(round(availableWidth * horizontalPosition))
        return image.crop((left, 0, left + cropWidth, image.height))
    if sourceRatio < targetRatio:
        cropHeight = int(round(image.width / targetRatio))
        top = (image.height - cropHeight) // 2
        return image.crop((0, top, image.width, top + cropHeight))
    return image


def _reportUnsupportedBackgroundAttributes(backgroundTag):
    """Warn for background effects which the PDF renderer cannot reproduce."""
    for attribute, expected in [('fading', 0.0), ('hue', 0.0), ('rotation', 0.0)]:
        if attribute in backgroundTag.attrib and float(backgroundTag.get(attribute)) != expected:
            logging.warning(
                f"value of background attribute not supported: {attribute} = "
                f"{backgroundTag.get(attribute)}")
    if 'type' in backgroundTag.attrib and int(backgroundTag.get('type')) != 1:
        logging.warning(
            f"value of background attribute not supported: type = {backgroundTag.get('type')}")


def _logBackgroundDrawing(pagetype, productstyle, pageNumber, lastPage):
    """Record a significant endpaper or content-page background draw."""
    if pagetype == PageProcessingType.FrontInsideCoverBackground:
        page_rendering.debug('Page %d: drawing the first content-page background.',
                      pageNumber)
    elif pagetype == PageProcessingType.OpeningContentPage:
        page_rendering.debug('Page %d: drawing the front inside-cover/endpaper '
                      'background%s.', pageNumber,
                      ' on the left side of the spread'
                      if ProductInfo.isAlbumDoubleSide(productstyle) else '')
    elif pagetype == PageProcessingType.BackInsideCover:
        page_rendering.debug('Page %d: drawing the back inside-cover/endpaper '
                      'background%s.', pageNumber,
                      ' on the right side of the spread'
                      if ProductInfo.isAlbumDoubleSide(productstyle) else '')
    elif pagetype == PageProcessingType.RegularPage and lastPage:
        page_rendering.debug('Page %d: drawing the last content-page background.',
                      pageNumber)
