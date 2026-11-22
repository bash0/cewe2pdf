"""Create a reproducible JPEG for manual CEWE background-colouring experiments."""

import colorsys
from pathlib import Path
import random

from PIL import Image, ImageOps


def createTestBackground(outputPath):
    """Combine a brightness ramp, colour patches and a warm mottled texture."""
    width, height = 1024, 750
    image = Image.new('RGB', (width, height))
    pixels = image.load()
    for left in range(width):
        value = round(32 + 223 * left / (width - 1))
        for top in range(160):
            pixels[left, top] = (value, value, value)

    # Both rows have the same HSV value. Hue replacement should make each row
    # uniform; saturation scaling should keep the second row relatively pale.
    for row, saturation in enumerate((1.0, 0.4)):
        for patch in range(6):
            colour = tuple(round(channel * 255) for channel in
                colorsys.hsv_to_rgb(patch / 6, saturation, 224 / 255))
            image.paste(colour, (patch * width // 6, 160 + row * 160,
                (patch + 1) * width // 6, 320 + row * 160))

    # Fixed random samples make the asset reproducible without borrowing a
    # CEWE texture. Two spatial scales retain recognisable brightness detail.
    randomSource = random.Random(1741)
    textureSize = (width, height - 480)
    coarse = Image.new('L', (12, 4))
    coarse.putdata([randomSource.randrange(256) for _ in range(48)])
    fine = Image.new('L', (48, 12))
    fine.putdata([randomSource.randrange(256) for _ in range(576)])
    textureValue = ImageOps.autocontrast(Image.blend(
        coarse.resize(textureSize, Image.Resampling.BICUBIC),
        fine.resize(textureSize, Image.Resampling.BICUBIC), 0.3))
    textureValue = textureValue.point([64 + round(value * 176 / 255) for value in range(256)])
    texture = Image.merge('HSV', (
        Image.new('L', textureSize, 28), Image.new('L', textureSize, 150), textureValue))
    image.paste(texture.convert('RGB'), (0, 480))
    image.save(outputPath, 'JPEG', quality=95, subsampling=0)


if __name__ == '__main__':
    # Shared test resources live under tests/, two levels above utilities/.
    destination = Path(__file__).resolve().parents[2] / 'Resources/photofun/backgrounds/6480.jpg'
    createTestBackground(destination)
    print(destination)
