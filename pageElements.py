"""Render the MCF area elements that make up one resolved page."""

# ``pages.processPages`` defines this callback's established argument list,
# and unpacking an MCF area naturally needs several local geometry values.
# Keep that rendering boundary explicit rather than wrapping it in an opaque
# parameter object solely to satisfy pylint.
# pylint: disable=too-many-arguments,too-many-locals

from math import floor

from albumIndex import AlbumIndex
from borders import processDecorationBorders
from ceweInfo import AlbumInfo
from cewePageResolver import getPageElementForPageNumber
from clipartareas import processAreaClipartTag
from conversionState import ConversionState
from imageareas import processAreaImageTag
from pageTypes import PageProcessingType
from renderContext import RenderContext
from shadows import processDecorationShadow
from textareas import processAreaTextTag


def processElements(additional_fonts, fotobook, imagedir,
                    productstyle, mcfBaseFolder, oddpage, page, pageNumber,
                    pagetype, pdf, pageH, pageW, lastpage,
                    context: RenderContext, state: ConversionState,
                    albumIndex: AlbumIndex):
    """Render images, text, and clip art from one MCF page element.

    ``pages.processPages`` resolves the unusual cover and paired-page rules.
    This function then selects the areas visible on this PDF page and delegates
    each area type to its specialist renderer.
    """
    if (AlbumInfo.isAlbumDoubleSide(productstyle)
            and pagetype == PageProcessingType.RegularPage
            and not oddpage and not lastpage):
        # In double-page mode, all images are drawn by the odd pages.
        return

    # The MCF stores ordinary album pages in pairs.  For an odd page, retrieve
    # the preceding even page element, which contains the shared areas.
    if (AlbumInfo.isAlbumProduct(productstyle)
            and pagetype == PageProcessingType.RegularPage and oddpage):
        page = getPageElementForPageNumber(fotobook, 2 * floor(pageNumber / 2))

    for area in page.findall('area'):
        areaPos = area.find('position')
        areaLeft = float(areaPos.get('left').replace(',', '.'))
        if (pagetype != PageProcessingType.FrontInsideCoverBackground
                or len(area.findall('imagebackground')) == 0):
            if oddpage and AlbumInfo.isAlbumSingleSide(productstyle):
                # Shift double-page content from the other page.
                areaLeft -= pageW
        areaTop = float(areaPos.get('top').replace(',', '.'))
        areaWidth = float(areaPos.get('width').replace(',', '.'))
        areaHeight = float(areaPos.get('height').replace(',', '.'))
        areaRot = float(areaPos.get('rotation'))

        # Skip an image which is wholly outside this side of a single-page
        # album spread.
        if (AlbumInfo.isAlbumSingleSide(productstyle)
                and pagetype in [PageProcessingType.RegularPage,
                                 PageProcessingType.Cover]):
            if oddpage and (areaLeft + areaWidth) < 0:
                continue
            if not oddpage and areaLeft > pageW:
                continue

        # Translate to the area's centre so ReportLab rotation has the same
        # origin as the Album Editor.
        cx = areaLeft + 0.5 * areaWidth
        cy = pageH - (areaTop + 0.5 * areaHeight)
        transCx = context.mcf_to_reportlab * cx
        transCy = context.mcf_to_reportlab * cy

        for imageTag in area.findall('imagebackground') + area.findall('image'):
            processAreaImageTag(
                imageTag, area, areaHeight, areaRot, areaWidth, imagedir,
                productstyle, mcfBaseFolder, pagetype, pdf, pageW, transCx,
                transCy, context, state, processDecorationShadow,
                processDecorationBorders)

        for textTag in area.findall('text'):
            processAreaTextTag(
                textTag, additional_fonts, area, areaWidth, areaHeight,
                areaRot, pdf, transCx, transCy, pageNumber, context, state,
                albumIndex)

        # A clipartarea has both designElementIDs and clipart elements.  The
        # latter contains the actual renderable clip art.
        if area.get('areatype') == 'clipartarea':
            decoration = area.find('decoration')
            for clipartElement in area.findall('clipart'):
                processAreaClipartTag(
                    clipartElement, areaHeight, areaRot, areaWidth, pdf,
                    transCx, transCy, decoration, context,
                    lambda decoration, height, width, canvas:
                    processDecorationBorders(decoration, height, width,
                                             canvas, context))
