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
                      lastPage, context: RenderContext):
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
                    pageNumber, lastPage, context)


def _drawBackground(backgroundTags, state: ConversionState, backgroundLocations,
                    productstyle, pagetype, pdf, areaHeight, areaWidth,
                    areaXOffset, pageNumber, lastPage,
                    context: RenderContext):
    """Find, load, and draw the selected background image."""
    backgroundTag = next((tag for tag in backgroundTags or []
                          if tag.get('alignment') is not None), None)
    if backgroundTag is None or backgroundTag.get('designElementId') is None:
        return

    if (pagetype == PageProcessingType.RegularPage
            and ProductInfo.isAlbumDoubleSide(productstyle)
            and backgroundTag.get('alignment') == '3'):
        areaWidth = areaWidth / 2
        areaXOffset = areaXOffset + areaWidth

    bg = backgroundTag.get('designElementId')
    _reportUnsupportedBackgroundAttributes(backgroundTag)
    try:
        bgPath = findFileInDirs([bg + '.bmp', bg + '.webp', bg + '.jpg'],
                                backgroundLocations)
        logging.debug(f"Reading background file: {bgPath}")
        image = PIL.Image.open(bgPath).convert('RGB')
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
