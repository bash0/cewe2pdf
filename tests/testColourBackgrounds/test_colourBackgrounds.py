"""Texture recolouring checks and portable single/double-page candidate PDFs."""

import colorsys
from datetime import datetime
import logging
from pathlib import Path
import sys
from xml.etree import ElementTree

import pymupdf
import pytest
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from testutils import configureTestImportPaths

configureTestImportPaths(__file__)

from backgroundColouring import getBackgroundRecolouring, recolourBackground
from backgrounds import processBackground
from compare_pdf import ComparePDF, ShowDiffsStyle
from cewe2pdf import convertMcf
from ceweInfo import PdfProductStyle
from conversionState import ConversionState
from pageTypes import PageProcessingType
from renderContext import RenderContext
from testutils import getLatestResultFile


ALBUM_FOLDER = Path(__file__).resolve().parent


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


@pytest.mark.parametrize('keepDoublePages', [False, True])
def test_colourBackgroundAlbum(keepDoublePages, caplog):
    """Render any fixture backgrounds before comparing with the approved appearance."""
    album = ALBUM_FOLDER / 'testColourBackgrounds.mcf'
    pages = ElementTree.parse(album).getroot().findall('page')
    contentPageCount = max(int(page.get('pagenr')) for page in pages if page.get('type') == 'normalpage')
    style = 'D' if keepDoublePages else 'S'
    output = ALBUM_FOLDER / f'testColourBackgrounds.mcf.{datetime.today():%Y%m%d}{style}.pdf'
    convertMcf(str(album), keepDoublePages=keepDoublePages, outputFileName=str(output))
    with pymupdf.open(output) as pdf:
        assert len(pdf) == (contentPageCount // 2 + 2 if keepDoublePages else contentPageCount + 2)
    assert 'Unsupported background recolouring' not in caplog.text
    assert 'Could not find background' not in caplog.text
    # Colour calibration is tested independently above. Keep this album free
    # to explore new images, settings and overlaid content; compare the result
    # only after writing the complete candidate PDF for visual inspection.
    approved = getLatestResultFile(ALBUM_FOLDER.name, f'*{style}.pdf')
    if approved is not None:
        comparison = ComparePDF([output, approved], ShowDiffsStyle.Nothing)
        try:
            assert comparison.compare(), 'PDF differs from the approved result; inspect the candidate before approval'
        finally:
            comparison.cleanup()


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
