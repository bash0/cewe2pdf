"""Background rendering for CEWE book pages."""

from io import BytesIO
import logging

# Background discovery tries several optional file locations; failure in one
# location is expected and is reported before processing continues.
# pylint: disable=broad-exception-caught

import PIL
from reportlab.lib.utils import ImageReader

from ceweInfo import AlbumInfo
from configUtils import getConfigurationBool
from conversionState import ConversionState
from pathutils import findFileInDirs
from pageTypes import PageProcessingType
from renderContext import RenderContext


def processBackground(backgroundTags, state: ConversionState, backgroundLocations,
                      productstyle, pagetype, pdf, ph, pw, context: RenderContext):  # noqa: C901
    """Draw the page background, including special handling for inside covers."""
    areaHeight = ph
    areaWidth = pw
    areaXOffset = 0

    if pagetype == PageProcessingType.FrontInsideCover:
        # This pass processes the inside-cover / first-page pair after its
        # background was handled by FrontInsideCoverBackground.
        if AlbumInfo.isAlbumSingleSide(productstyle):
            return
        if AlbumInfo.isAlbumDoubleSide(productstyle):
            areaWidth = areaWidth / 2

    if pagetype == PageProcessingType.BackInsideCover:
        if AlbumInfo.isAlbumSingleSide(productstyle):
            return
        if AlbumInfo.isAlbumDoubleSide(productstyle):
            areaWidth = areaWidth / 2
            areaXOffset = areaXOffset + areaWidth

    if pagetype in [PageProcessingType.FrontInsideCover, PageProcessingType.BackInsideCover] and \
            not getConfigurationBool(context.default_config_section, 'insideCoverWhite', 'False'):
        # Returning accepts the background already underneath.  An explicit
        # configuration setting instead draws CEWE's default white background.
        return

    if backgroundTags is not None and len(backgroundTags) > 0:
        backgroundTag = None
        for curTag in backgroundTags:
            if curTag.get('alignment') is not None:
                backgroundTag = curTag
                break

        if backgroundTag is None:
            return

        if pagetype == PageProcessingType.RegularPage and AlbumInfo.isAlbumDoubleSide(productstyle) and \
                backgroundTag.get('alignment') == '3':
            areaWidth = areaWidth / 2
            areaXOffset = areaXOffset + areaWidth

        if backgroundTag.get('designElementId') is not None:
            bg = backgroundTag.get('designElementId')
            for attribute, expected in [('fading', 0.0), ('hue', 0.0), ('rotation', 0.0)]:
                if attribute in backgroundTag.attrib and float(backgroundTag.get(attribute)) != expected:
                    logging.warning(f"value of background attribute not supported: {attribute} = {backgroundTag.get(attribute)}")
            if 'type' in backgroundTag.attrib and int(backgroundTag.get('type')) != 1:
                logging.warning(f"value of background attribute not supported: type = {backgroundTag.get('type')}")

            bgPath = ''
            try:
                bgPath = findFileInDirs([bg + '.bmp', bg + '.webp', bg + '.jpg'], backgroundLocations)
                logging.debug(f"Reading background file: {bgPath}")
                image = PIL.Image.open(bgPath).convert('RGB')
                memFileHandle = BytesIO()
                image.save(memFileHandle, 'jpeg')
                memFileHandle.seek(0)
                pdf.drawImage(ImageReader(memFileHandle), context.mcf_to_reportlab * areaXOffset, 0,
                              width=context.mcf_to_reportlab * areaWidth,
                              height=context.mcf_to_reportlab * areaHeight)
            except Exception:
                if bg not in state.background_not_found_paths:
                    logging.warning(
                        f'Could not find background {bg}; leaving the page background unchanged.')
                state.background_not_found_paths.add(bg)
