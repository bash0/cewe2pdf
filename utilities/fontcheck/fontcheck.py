
"""Inspect Unicode character support in font files.

Run from the repository root:

    python -m utilities.fontcheck

Examples:

    python -m utilities.fontcheck --character U+2643 --directory C:\\Windows\\Fonts

    python -m utilities.fontcheck --character U+263A --character U+263B

    python -m utilities.fontcheck --character ☺ --directory tests/Resources/photofun/fonts
"""

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont, TTCollection


EXTENSIONS = {".ttf", ".otf", ".ttc", ".otc"}

DEFAULT_CHARACTERS = ["U+263A", "U+263B"]


def parse_character(value):
    """Convert a Unicode notation or literal character to a character."""

    if value.upper().startswith("U+"):
        try:
            codepoint = int(value[2:], 16)
            return chr(codepoint)
        except (ValueError, OverflowError):
            raise argparse.ArgumentTypeError(
                f"Invalid Unicode code point: {value}"
            ) from None

    if len(value) != 1:
        raise argparse.ArgumentTypeError(
            f"Expected one character or Unicode notation such as U+263A: {value}"
        )

    return value


def family_name(font):
    """Return the font's family name."""

    if "name" not in font:
        return "Unknown family"

    return (
        font["name"].getDebugName(1)
        or font["name"].getDebugName(16)
        or "Unknown family"
    )


def inspect_face(font, filename, characters, relative_path, face_index=""):
    """Inspect one font face and report character support."""

    cmap = font.getBestCmap() or {}
    family = family_name(font)

    print(f"{relative_path} {face_index}")
    print(f"    {family}")

    for character in characters:
        codepoint = ord(character)
        glyph = cmap.get(codepoint)

        notation = f"U+{codepoint:04X}"

        if glyph:
            result = f"YES ({glyph})"
        else:
            result = "NO"

        print(f"    {character} {notation}: {result}")


def inspect_file(filename, characters, directory):
    """Inspect all font faces in a font file."""

    relative_path = filename.relative_to(directory)

    try:
        if filename.suffix.lower() in {".ttc", ".otc"}:
            collection = TTCollection(str(filename), lazy=True)

            try:
                for index, font in enumerate(collection.fonts):
                    inspect_face(
                        font,
                        filename,
                        characters,
                        relative_path,
                        f"[face {index}]"
                    )
            finally:
                collection.close()

        else:
            font = TTFont(str(filename), lazy=True)

            try:
                inspect_face(
                    font,
                    filename,
                    characters,
                    relative_path
                )
            finally:
                font.close()

    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"ERROR: {relative_path}: {exc}", file=sys.stderr)


def main():
    """Parse arguments and scan the requested directory."""

    parser = argparse.ArgumentParser(
        description="Check which fonts support specified Unicode characters."
    )

    parser.add_argument(
        "--character",
        action="append",
        type=parse_character,
        metavar="CHARACTER",
        help=(
            "Character to check, either literally or as Unicode notation "
            "(e.g. U+263A). Can be specified multiple times. "
            "Defaults to U+263A and U+263B."
        )
    )

    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("."),
        metavar="PATH",
        help="Directory to scan recursively (default: current directory)."
    )

    args = parser.parse_args()

    directory = args.directory.resolve()

    if not directory.is_dir():
        parser.error(f"Not a directory: {directory}")

    characters = args.character or [
        parse_character(value) for value in DEFAULT_CHARACTERS
    ]

    # Remove duplicate characters while preserving their order.
    characters = list(dict.fromkeys(characters))

    font_files = sorted(
        (
            filename
            for filename in directory.rglob("*")
            if filename.is_file()
            and filename.suffix.lower() in EXTENSIONS
        ),
        key=lambda path: str(path).casefold()
    )

    if not font_files:
        print(f"No font files found in {directory}")
        return

    print(f"Scanning: {directory}")
    print(f"Found {len(font_files)} font files.")
    print()

    for filename in font_files:
        inspect_file(filename, characters, directory)


if __name__ == "__main__":
    main()
