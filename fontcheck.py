
from pathlib import Path
from fontTools.ttLib import TTFont, TTCollection

'''
run this script directly with python fontcheck to check if the smiley characters
are present or not in the fonts in the specified directory.
'''

FONT_ROOT = Path(
    r".\tests\Resources\photofun\fonts"
)

SMILEYS = {
    "U+263A": "\u263A",
    "U+263B": "\u263B",
}

EXTENSIONS = {".ttf", ".otf", ".ttc", ".otc"}


def family_name(font):
    """Return the font's family name."""
    if "name" not in font:
        return "Unknown family"

    return (
        font["name"].getDebugName(1)
        or font["name"].getDebugName(16)
        or "Unknown family"
    )


def inspect_face(font, filename, face_index=""):
    cmap = font.getBestCmap() or {}
    family = family_name(font)

    results = []
    for code, character in SMILEYS.items():
        glyph = cmap.get(ord(character))
        results.append(
            f"{code}: {'YES (' + glyph + ')' if glyph else 'NO'}"
        )

    print(f"{filename} {face_index}")
    print(f"    {family}")
    print(f"    {' | '.join(results)}")


def inspect_file(filename):
    try:
        if filename.suffix.lower() in {".ttc", ".otc"}:
            collection = TTCollection(str(filename), lazy=True)
            try:
                for index, font in enumerate(collection.fonts):
                    inspect_face(font, filename, f"[face {index}]")
            finally:
                collection.close()
        else:
            font = TTFont(str(filename), lazy=True)
            try:
                inspect_face(font, filename)
            finally:
                font.close()

    except Exception as exc:
        print(f"ERROR: {filename}: {exc}")


for filename in sorted(FONT_ROOT.rglob("*")):
    if filename.is_file() and filename.suffix.lower() in EXTENSIONS:
        inspect_file(filename)
