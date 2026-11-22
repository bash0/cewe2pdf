"""Estimate the three red-background saturations from the CEWE reference preview.

Run this utility python file directly after exporting the fixture as testColourBackgroundsPreview.pdf, which
you can do by right-clicking the testColourBackgrounds.mcf fixture in the CEWE editor and
selecting "Export preview PDF". Save it beside this script in utilities/.
The book mockup is shaded, so these measurements are approximate, not flat-page targets.
"""

from pathlib import Path
from statistics import median, quantiles

from PIL import Image
import pymupdf


def measurePreview(previewPath):
    """Sample upper page interiors, away from the gutter and CEWE watermark."""
    with pymupdf.open(previewPath) as preview:
        # PDF page 8 contains album pages 12-13; page 9 contains pages 14-15.
        for albumPage, pdfIndex, fading, left, right in [
                (13, 7, 3, 0.60, 0.90),
                (14, 8, 4, 0.10, 0.40),
                (15, 8, 5, 0.60, 0.90)]:
            page = preview[pdfIndex]
            scale = 1600 / page.rect.width
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            image = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
            patch = image.crop((round(image.width * left), round(image.height * 0.18),
                round(image.width * right), round(image.height * 0.34)))
            # For red backgrounds, HSV saturation is (R - min(G, B)) / R.
            # Ignore dark edges and any pixels without a dominant red channel.
            saturations = [(red - min(green, blue)) / red
                for red, green, blue in patch.get_flattened_data()
                if red > 80 and red > green and red > blue]
            if not saturations:
                raise ValueError(f'No red background pixels found on album page {albumPage}')
            lower, _, upper = quantiles(saturations, n=4)
            print(f'Album page {albumPage}, fading {fading}: '
                f'median saturation {median(saturations):.2%}, '
                f'interquartile range {lower:.2%}-{upper:.2%}, '
                f'{len(saturations)} pixels')


if __name__ == '__main__':
    measurePreview(Path(__file__).resolve().with_name('testColourBackgroundsPreview.pdf'))
