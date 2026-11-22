"""Measure the synthetic 6480 strips in the CEWE reference preview beside this script."""

import colorsys
from pathlib import Path
from statistics import median

from PIL import Image
import pymupdf


def measureTestStrips(previewPath):
    """Sample outside the gutter/watermark, at the interiors of both colour rows."""
    with pymupdf.open(previewPath) as preview:
        for number, pdfIndex, fading, side in [
                (16, 9, 0, 'left'), (17, 9, 0, 'right'),
                (18, 10, 1, 'left'), (19, 10, 2, 'right'),
                (20, 11, 3, 'left'), (21, 11, 3, 'right'),
                (22, 12, 5, 'left'), (23, 12, 5, 'right')]:
            page = preview[pdfIndex]
            scale = 1600 / page.rect.width
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            image = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
            measureStripRows(image, number, fading, side)


def measureStripRows(image, pageNumber, fading, side):
    """Report median RGB and HSV saturation for saturated, pale and grey strips."""
    left, right = (0.07, 0.11) if side == 'left' else (0.90, 0.94)
    for label, top, bottom in [('full', 0.32, 0.40), ('pale', 0.52, 0.62), ('grey', 0.20, 0.24)]:
        patch = image.crop((round(image.width * left), round(image.height * top),
            round(image.width * right), round(image.height * bottom)))
        pixels = list(patch.get_flattened_data())
        hsv = [colorsys.rgb_to_hsv(*(channel / 255 for channel in pixel)) for pixel in pixels]
        rgb = tuple(median(pixel[channel] for pixel in pixels) for channel in range(3))
        print(f'Album page {pageNumber}, fading {fading}, {label}: '
            f'RGB={rgb}, saturation={median(colour[1] for colour in hsv):.2%}')


if __name__ == '__main__':
    measureTestStrips(Path(__file__).resolve().with_name('testColourBackgroundsPreview.pdf'))
