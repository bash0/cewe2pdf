"""A replacement colour can make selected SVG paint transparent."""

from pathlib import Path
import sys
from xml.etree import ElementTree

from PIL import Image
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)

from clipart.catalog import getClipConfig
from clipart.clpfile import ClpFile


def colourReplacement(source, target):
    clipart = ElementTree.Element('clipart')
    config = ElementTree.SubElement(clipart, 'ClipartConfiguration')
    colours = ElementTree.SubElement(config, 'colors')
    ElementTree.SubElement(colours, 'color', source=source, target=target)
    return getClipConfig(clipart)[0]


def test_clipart_config_preserves_colour_alpha_and_ordinary_rgb():
    assert colourReplacement('#fae917', '#000000,0') == [('#FAE917', 'rgba(0,0,0,0)')]
    assert colourReplacement('#fae917', '#f47723') == [('#FAE917', '#F47723')]


def test_existing_balloons_keep_letters_and_other_colours_when_yellow_is_transparent():
    fixture = Path(__file__).with_name('test_clipart_colorreplacement.mcf')
    root = ElementTree.parse(fixture).getroot()
    record = next(tag for tag in root.iter('clipart') if tag.get('designElementId') == '104304')
    art = ClpFile(PROJECT_ROOT / 'tests/Resources/photofun/decorations/7065-CLIP-SF.clp')
    before = art.rasterSvgData(528, 394).convert('RGBA')
    art.replaceColors(getClipConfig(record)[0])
    art.convertToPngInBuffer(528, 394, alpha=255)
    with Image.open(art.pngMemFile) as raster:
        after = raster.convert('RGBA')

    def firstPixel(colour, startRow=0):
        return next((x, y) for y in range(startRow, before.height) for x in range(before.width)
            if before.getpixel((x, y)) == colour)

    # The first solid yellow fill is on the upper H balloon. Near the bottom,
    # only strings remain, giving a separate check of stroke transparency.
    assert after.getpixel(firstPixel((250, 233, 23, 255)))[3] == 0
    assert after.getpixel(firstPixel((250, 233, 23, 255), 3 * before.height // 4))[3] == 0
    assert after.getpixel(firstPixel((255, 255, 255, 255))) == (255, 255, 255, 255)
    assert after.getpixel(firstPixel((128, 173, 209, 255))) == (128, 173, 209, 255)


@pytest.mark.parametrize('paintLocation', ['style', 'attributes'])
def test_transparent_fill_stroke_and_gradient_preserve_other_paint_and_area_opacity(paintLocation):
    def paint(**properties):
        properties = {key.replace('_', '-'): value for key, value in properties.items()}
        if paintLocation == 'style':
            return {'style': ';'.join(f'{key}:{value}' for key, value in properties.items())}
        return properties

    svg = ElementTree.Element('svg', xmlns='http://www.w3.org/2000/svg', width='80', height='20')
    definitions = ElementTree.SubElement(svg, 'defs')
    gradient = ElementTree.SubElement(definitions, 'linearGradient', id='fade')
    ElementTree.SubElement(gradient, 'stop', offset='0', **paint(stop_color='#fae917'))
    ElementTree.SubElement(gradient, 'stop', offset='1', **paint(stop_color='#00ff00'))
    ElementTree.SubElement(svg, 'rect', x='2', y='2', width='16', height='16',
        **paint(fill='#fae917', stroke='#00ff00', stroke_width='4'))
    ElementTree.SubElement(svg, 'rect', x='32', y='2', width='16', height='16',
        **paint(fill='#00ff00', stroke='#fae917', stroke_width='4'))
    ElementTree.SubElement(svg, 'rect', x='60', y='0', width='20', height='20', fill='url(#fade)')
    art = ClpFile()
    art.svgData = ElementTree.tostring(svg)
    # The RGB value is unchanged: the alpha change must still take effect.
    art.replaceColors(colourReplacement('#fae917', '#fae917,0'))
    art.convertToPngInBuffer(80, 20, alpha=128)
    with Image.open(art.pngMemFile) as raster:
        result = raster.convert('RGBA')
    assert result.getpixel((10, 10))[3] == 0  # Transparent fill.
    assert result.getpixel((30, 10))[3] == 0  # Transparent stroke.
    assert result.getpixel((1, 10)) == (0, 255, 0, 128)  # Unchanged green outline.
    assert result.getpixel((40, 10)) == (0, 255, 0, 128)  # Unchanged green fill.
    assert 0 < result.getpixel((61, 10))[3] < 30
    assert result.getpixel((78, 10))[3] > 100  # Gradient retains its opaque end.


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
