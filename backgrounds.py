"""Background rendering for CEWE book pages."""

from io import BytesIO
import logging

import PIL
from reportlab.lib.utils import ImageReader

from ceweInfo import AlbumInfo
from configUtils import getConfigurationBool
from pathutils import findFileInDirs
from pageTypes import PageType


def processBackground(backgroundTags, bg_notFoundDirList, cewe_folder, backgroundLocations,
                      productstyle, pagetype, pdf, ph, pw, defaultConfigSection, mcf2rl):  # noqa: C901
    """Draw the page background, including special handling for inside covers."""
    areaHeight = ph
    areaWidth = pw
    areaXOffset = 0

    if pagetype == PageType.EmptyPage:
        # EmptyPage is used when processing the inside-cover / first-page pair
        # for the second time after it was already processed as SingleSide.
        if AlbumInfo.isAlbumSingleSide(productstyle):
            return
        if AlbumInfo.isAlbumDoubleSide(productstyle):
            areaWidth = areaWidth / 2

    if pagetype == PageType.BackInsideCover:
        if AlbumInfo.isAlbumSingleSide(productstyle):
            return
        if AlbumInfo.isAlbumDoubleSide(productstyle):
            areaWidth = areaWidth / 2
            areaXOffset = areaXOffset + areaWidth

    if pagetype in [PageType.EmptyPage, PageType.BackInsideCover] and \
            not getConfigurationBool(defaultConfigSection, 'insideCoverWhite', 'False'):
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

        if pagetype == PageType.Normal and AlbumInfo.isAlbumDoubleSide(productstyle) and \
                backgroundTag.get('alignment') == '3':
            areaWidth = areaWidth / 2
            areaXOffset = areaXOffset + areaWidth

        if cewe_folder and backgroundTag.get('designElementId') is not None:
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
                pdf.drawImage(ImageReader(memFileHandle), mcf2rl * areaXOffset, 0,
                              width=mcf2rl * areaWidth, height=mcf2rl * areaHeight)
            except Exception:
                if bgPath not in bg_notFoundDirList:
                    logging.error('Could not find background or error when adding to pdf')
                    logging.exception('Exception')
                bg_notFoundDirList.add(bgPath)
