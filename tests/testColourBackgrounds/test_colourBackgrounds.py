"""Texture recolouring checks and portable single/double-page candidate PDFs."""

import colorsys
from datetime import datetime
import logging
from pathlib import Path
import sys
from xml.etree import ElementTree

import pymupdf
import pytest
from PIL import Image, ImageStat


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from testutils import configureTestImportPaths

configureTestImportPaths(__file__)

from backgroundColouring import getBackgroundRecolouring, recolourBackground
from backgrounds import processBackground
from cewe2pdf import convertMcf
from ceweInfo import PdfProductStyle
from conversionState import ConversionState
from pageTypes import PageProcessingType
from renderContext import RenderContext


ALBUM_FOLDER = Path(__file__).resolve().parent
# Confirmed against the normalpage background records, not preview PDF indices.
PAGE_COLOURS = {
    1: (0, 3), 2: (240, 3), 3: (60, 3), 4: (120, 3),
    5: (300, 3), 6: (330, 3), 8: (0, 5), 9: (60, 5),
    10: (210, 5), 11: (300, 5), 13: (0, 3), 14: (0, 4), 15: (0, 5),
    16: (0, 0), 17: (0, 0), 18: (60, 1), 19: (60, 2), 20: (210, 3), 21: (210, 3),
    22: (330, 5), 23: (330, 5),
}


def backgroundTag(**attributes):
    return ElementTree.Element('background', {
        'alignment': '1', 'designElementId': '485', 'rotation': '0',
        'type': '1', **attributes,
    })


@pytest.mark.parametrize('hue, fading, saturationScale', [
    (0, 0, 1.0), (210, 3, 180 / 255), (330, 4, 90 / 255)])
def test_recolourTexture(hue, fading, saturationScale):
    """Exercise shared pixel properties with representative strong and pale colours."""
    source = Image.new('RGB', (5, 1))
    source.putdata([(210, 120, 70), (80, 180, 220), (150, 150, 150),
        (255, 240, 245), (0, 0, 0)])
    originalBytes = source.tobytes()
    result = recolourBackground(source, hue, fading)
    assert result is not source
    assert source.tobytes() == originalBytes
    assert result.size == source.size
    assert result.mode == 'RGB'
    assert result.convert('HSV').getchannel('V').tobytes() == source.convert('HSV').getchannel('V').tobytes()
    for index in range(4):
        _, actualSaturation, _ = result.convert('HSV').getpixel((index, 0))
        # An RGB round trip quantises the smaller channel differences.
        sourceSaturation = source.convert('HSV').getpixel((index, 0))[1]
        assert abs(actualSaturation - sourceSaturation * saturationScale) <= 2
        if sourceSaturation == 0:
            assert result.getpixel((index, 0)) == source.getpixel((index, 0))
            continue
        # Almost-grey RGB pixels have only a few chroma levels, so recovering
        # an angle from them magnifies rounding. Compare RGB with the standard
        # library's independent HSV conversion instead of that unstable angle.
        expectedColour = colorsys.hsv_to_rgb(
            round((hue % 360) / 360 * 255) / 255,
            round(sourceSaturation * saturationScale) / 255,
            max(source.getpixel((index, 0))) / 255)
        assert max(abs(actual - round(expected * 255)) for actual, expected in
            zip(result.getpixel((index, 0)), expectedColour)) <= 1
    assert result.getpixel((4, 0)) == (0, 0, 0)


def test_hueWraparound():
    source = Image.new('RGB', (2, 2), (190, 120, 80))
    assert recolourBackground(source, 0, 3).tobytes() == recolourBackground(source, 360, 3).tobytes()
    assert recolourBackground(source, -30, 3).tobytes() == recolourBackground(source, 330, 3).tobytes()


@pytest.mark.parametrize('hue, fading, previewColours', [
    (0, 0, [(224, 0, 0), (224, 134, 134)]),
    (60, 1, [(224, 224, 112), (225, 224, 178)]),
    (60, 2, [(226, 225, 169), (224, 223, 202)]),
    (210, 3, [(66, 145, 224), (161, 192, 223)]),
    (330, 5, [(223, 184, 203), (224, 209, 216)]),
])
def test_matchesCeweTestStrips(hue, fading, previewColours):
    """Check each measured preset against its saturated/pale CEWE strip pair."""
    source = Image.new('RGB', (2, 1))
    source.putdata([(224, 0, 0), (224, 134, 134)])
    result = recolourBackground(source, hue, fading)
    # The book preview is JPEG-compressed and shaded; flat strip interiors
    # agree within four RGB levels, rather than being exact pixel references.
    for index, previewColour in enumerate(previewColours):
        assert max(abs(actual - expected) for actual, expected in
            zip(result.getpixel((index, 0)), previewColour)) <= 4


def test_alphaPreserved():
    source = Image.new('RGBA', (2, 1))
    source.putdata([(190, 120, 80, 0), (120, 80, 30, 123)])
    originalBytes = source.tobytes()
    result = recolourBackground(source, 240, 5)
    assert result.mode == 'RGBA'
    assert result.getchannel('A').tobytes() == source.getchannel('A').tobytes()
    assert source.tobytes() == originalBytes


@pytest.mark.parametrize('hue, fading', [(0, 6), (float('nan'), 3)])
def test_transformRejectsUnsupportedSettings(hue, fading):
    with pytest.raises(ValueError):
        recolourBackground(Image.new('RGB', (1, 1)), hue, fading)


@pytest.mark.parametrize('attributes', [
    {'hue': '0', 'fading': '6'}, {'hue': '120'},
    {'hue': 'nan', 'fading': '3'}, {'hue': 'oops', 'fading': '3'},
    {'hue': '0', 'fading': '3', 'type': '2'},
])
def test_unsupportedRecolouringWarns(attributes, caplog):
    with caplog.at_level(logging.WARNING):
        assert getBackgroundRecolouring(backgroundTag(**attributes)) is None
    assert 'using the original background image' in caplog.text


def test_explicitZeroIsDifferentFromMissingSettings(caplog):
    assert getBackgroundRecolouring(backgroundTag(designElementId='6480')) is None
    assert getBackgroundRecolouring(backgroundTag(designElementId='6480', hue='0', fading='0')) == (0, 0)
    source = Image.new('RGB', (1, 1), (0, 224, 0))
    assert recolourBackground(source, 0, 0).getpixel((0, 0)) == (224, 0, 0)
    assert source.getpixel((0, 0)) == (0, 224, 0)
    assert not caplog.records


@pytest.mark.parametrize('attributes', [{}, {'hue': '0', 'fading': '6'}])
def test_fallbackDrawsOriginalImage(attributes):
    """Exercise the actual renderer and its JPEG fallback without a mock transform."""
    class BackgroundCanvas:
        def __init__(self):
            self.images = []

        def drawImage(self, image, *_args, **_kwargs):
            self.images.append(image.getRGBData())

    context = RenderContext(1, 150, 80, 150, Image.Resampling.LANCZOS, {}, {}, ())
    resourceFolder = PROJECT_ROOT / 'tests/Resources/photofun/backgrounds'
    tag = backgroundTag(designElementId='6480', **attributes)
    pdf = BackgroundCanvas()
    processBackground([tag], ConversionState(), (str(resourceFolder),),
        PdfProductStyle.AlbumSingleSide, PageProcessingType.RegularPage,
        pdf, 2750, 2100, 2, False, False, context)
    ordinaryTag = backgroundTag(designElementId=tag.get('designElementId'))
    originalPdf = BackgroundCanvas()
    processBackground([ordinaryTag], ConversionState(), (str(resourceFolder),),
        PdfProductStyle.AlbumSingleSide, PageProcessingType.RegularPage,
        originalPdf, 2750, 2100, 2, False, False, context)
    assert len(pdf.images) == 1
    assert pdf.images == originalPdf.images


def assertRecolouredPixel(actual, source, hue, fading):
    """Compare decoded JPEG colour against the original pixel's saturation/value."""
    _, sourceSaturation, sourceValue = colorsys.rgb_to_hsv(*(channel / 255 for channel in source))
    actualHue, actualSaturation, actualValue = colorsys.rgb_to_hsv(*(channel / 255 for channel in actual))
    saturationScale = {0: 1.0, 1: 0.5, 2: 0.25, 3: 180 / 255, 4: 90 / 255, 5: 45 / 255}[fading]
    assert abs(actualSaturation - sourceSaturation * saturationScale) < 0.03
    assert abs(actualValue - sourceValue) <= 4 / 255
    if sourceSaturation == 0:
        return
    hueDifference = abs(actualHue * 360 - hue % 360)
    assert min(hueDifference, 360 - hueDifference) < 6


def assertRecolouredBackgroundPage(page, background, pageNumber, keepDoublePages):
    """Select the physical page's background, including independent spread halves."""
    horizontalFraction = (0.75 if pageNumber % 2 else 0.25) if keepDoublePages else 0.5
    midpoint = pymupdf.Point(page.rect.width * horizontalFraction, page.rect.height / 2)
    imageReferences = [image[0] for image in page.get_images()
        if any(rect.contains(midpoint) for rect in page.get_image_rects(image[0]))]
    assert len(imageReferences) == 1
    embedded = pymupdf.Pixmap(page.parent, imageReferences[0])
    resource = PROJECT_ROOT / 'tests/Resources/photofun/backgrounds' / f"{background.get('designElementId')}.jpg"
    with Image.open(resource) as source:
        rectangle = next(rect for rect in page.get_image_rects(imageReferences[0]) if rect.contains(midpoint))
        # Page 1 uses the existing front-inside-cover background pass, which
        # retains the full image even in single-page output.
        expectedWidth = source.width if pageNumber == 1 else min(
            source.width, round(source.height * rectangle.width / rectangle.height))
        assert (embedded.width, embedded.height) == (expectedWidth, source.height)
        sourceLeft = source.width - embedded.width if background.get('alignment') == '3' else 0
        left, top = embedded.width // 2, embedded.height // 2
        # Average one JPEG block: an individual textured pixel changed by six
        # brightness levels in the measured output, although the pure transform
        # preserves V exactly. Block means avoid JPEG ringing at that pixel.
        actualImage = Image.frombytes('RGB', (embedded.width, embedded.height), embedded.samples)
        actualColour = ImageStat.Stat(actualImage.crop((left - 4, top - 4, left + 4, top + 4))).mean
        sourceColour = ImageStat.Stat(source.crop((sourceLeft + left - 4, top - 4,
            sourceLeft + left + 4, top + 4))).mean
        assertRecolouredPixel(actualColour, sourceColour,
            float(background.get('hue')), int(background.get('fading')))


@pytest.mark.parametrize('keepDoublePages', [False, True])
def test_colourBackgroundAlbum(keepDoublePages, caplog):
    album = ALBUM_FOLDER / 'testColourBackgrounds.mcf'
    pages = ElementTree.parse(album).getroot().findall('page')
    actualColours = {}
    for page in pages:
        if page.get('type') != 'normalpage':
            continue
        tag = page.find('background')
        if tag.get('hue') is not None and tag.get('fading') is not None:
            actualColours[int(page.get('pagenr'))] = (int(tag.get('hue')), int(tag.get('fading')))
    assert actualColours == PAGE_COLOURS
    for number in range(16, 24):
        page = next(page for page in pages if page.get('type') == 'normalpage' and page.get('pagenr') == str(number))
        tag = page.find('background')
        assert tag.get('designElementId') == '6480'
        assert tag.get('alignment') == ('3' if number % 2 else '1')
        if number in (16, 17):
            assert tag.get('hue') == '0' and tag.get('fading') == '0'
    style = 'D' if keepDoublePages else 'S'
    output = ALBUM_FOLDER / f'testColourBackgrounds.mcf.{datetime.today():%Y%m%d}{style}.pdf'
    convertMcf(str(album), keepDoublePages=keepDoublePages, outputFileName=str(output))
    with pymupdf.open(output) as pdf:
        assert len(pdf) == (15 if keepDoublePages else 28)
        for number in range(1, 27):
            index = 1 + number // 2 if keepDoublePages else number
            page = pdf[index]
            if number in PAGE_COLOURS:
                background = next(tag.find('background') for tag in pages
                    if tag.get('type') == 'normalpage' and tag.get('pagenr') == str(number))
                assertRecolouredBackgroundPage(page, background, number, keepDoublePages)
                continue
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(0.5, 0.5), alpha=False)
            horizontalFraction = (0.75 if number % 2 else 0.25) if keepDoublePages else 0.5
            red, green, blue = pixmap.pixel(int(pixmap.width * horizontalFraction), pixmap.height // 2)
            assert (red, green, blue) == (255, 255, 255)
    assert 'Unsupported background recolouring' not in caplog.text
    assert 'Could not find background' not in caplog.text


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
