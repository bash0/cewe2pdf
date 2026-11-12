
"""Inspect Unicode character support in font files.

Run from the repository root:

    python -m utilities.fontcheck.fontcheck

Examples:

    python -m utilities.fontcheck.fontcheck --character U+2643
    python -m utilities.fontcheck.fontcheck --character U+263A --character U+263B
    python -m utilities.fontcheck.fontcheck --directory C:\\Windows\\Fonts
    python -m utilities.fontcheck.fontcheck --family Arial
    python -m utilities.fontcheck.fontcheck --missing-only
    python -m utilities.fontcheck.fontcheck --all-present
    python -m utilities.fontcheck.fontcheck --families
    python -m utilities.fontcheck.fontcheck --csv > fontcheck.csv
    python -m utilities.fontcheck.fontcheck --summary
"""

import argparse
import csv
import sys
from pathlib import Path

from fontTools.ttLib import TTFont, TTCollection


EXTENSIONS = {".ttf", ".otf", ".ttc", ".otc"}

DEFAULT_CHARACTERS = ["U+263A", "U+263B"]


def parse_character(value):
    """Convert Unicode notation or a literal character to a character."""

    if value.upper().startswith("U+"):
        try:
            codepoint = int(value[2:], 16)
            if not 0 <= codepoint <= 0x10FFFF:
                raise ValueError
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
    """Return information about one font face."""

    cmap = font.getBestCmap() or {}

    supported = {}
    for character in characters:
        codepoint = ord(character)
        supported[character] = cmap.get(codepoint)

    return {
        "file": str(relative_path),
        "face": face_index,
        "family": family_name(font),
        "supported": supported,
    }


def inspect_file(filename, characters, directory):
    """Inspect all font faces in a font file."""

    relative_path = filename.relative_to(directory)

    try:
        if filename.suffix.lower() in {".ttc", ".otc"}:
            collection = TTCollection(str(filename), lazy=True)

            try:
                for index, font in enumerate(collection.fonts):
                    yield inspect_face(
                        font,
                        filename,
                        characters,
                        relative_path,
                        f"[face {index}]",
                    )
            finally:
                collection.close()

        else:
            font = TTFont(str(filename), lazy=True)

            try:
                yield inspect_face(
                    font,
                    filename,
                    characters,
                    relative_path,
                )
            finally:
                font.close()

    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"ERROR: {relative_path}: {exc}", file=sys.stderr)


def display_character(character):
    """Return a readable character and Unicode notation."""

    codepoint = ord(character)
    return f"{character} U+{codepoint:04X}"


def print_report(results, characters, missing_only, all_present):
    """Print the normal readable report."""

    for result in results:
        missing = [
            character
            for character in characters
            if result["supported"][character] is None
        ]

        if missing_only and not missing:
            continue

        if all_present and missing:
            continue

        print(result["file"], result["face"])
        print(f"    {result['family']}")

        for character in characters:
            glyph = result["supported"][character]

            if glyph:
                status = f"YES ({glyph})"
            else:
                status = "NO"

            print(f"    {display_character(character)}: {status}")

        print()


def print_csv(results, characters, missing_only, all_present):
    """Print the detailed report as CSV."""

    output = sys.stdout

    if hasattr(output, "reconfigure"):
        output.reconfigure(encoding="utf-8-sig")

    writer = csv.writer(output, lineterminator="\n")

    writer.writerow(
        ["File", "Face", "Family"]
        + [display_character(character) for character in characters]
    )

    for result in results:
        missing = [
            character
            for character in characters
            if result["supported"][character] is None
        ]

        if missing_only and not missing:
            continue

        if all_present and missing:
            continue

        writer.writerow(
            [
                result["file"],
                result["face"],
                result["family"],
            ]
            + [
                "YES" if result["supported"][character] else "NO"
                for character in characters
            ]
        )


def print_families(results):
    """Print distinct font families."""

    families = sorted(
        {result["family"] for result in results},
        key=str.casefold,
    )

    for family in families:
        print(family)

    print()
    print(f"{len(families)} distinct font families.")


def print_summary(results, characters):
    """Print the number of faces supporting each character."""

    total = len(results)

    print("Summary")
    print("-------")
    print(f"Font faces checked: {total}")

    for character in characters:
        supported = sum(
            result["supported"][character] is not None
            for result in results
        )

        missing = total - supported

        print(
            f"{display_character(character)}: "
            f"{supported} supported, {missing} missing"
        )


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
        ),
    )

    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("."),
        metavar="PATH",
        help="Directory to scan recursively (default: current directory).",
    )

    parser.add_argument(
        "--family",
        metavar="PATTERN",
        help="Only include font families containing this text (case-insensitive).",
    )

    parser.add_argument(
        "--families",
        action="store_true",
        help="List distinct font families instead of glyph support.",
    )

    filter_group = parser.add_mutually_exclusive_group()

    filter_group.add_argument(
        "--missing-only",
        action="store_true",
        help="Show only font faces missing at least one requested character.",
    )

    filter_group.add_argument(
        "--all-present",
        action="store_true",
        help="Show only font faces supporting all requested characters.",
    )

    parser.add_argument(
        "--csv",
        action="store_true",
        help="Output detailed results as CSV instead of a readable report.",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show support counts for each requested character.",
    )

    args = parser.parse_args()

    directory = args.directory.resolve()

    if not directory.is_dir():
        parser.error(f"Not a directory: {directory}")

    characters = args.character or [
        parse_character(value) for value in DEFAULT_CHARACTERS
    ]

    characters = list(dict.fromkeys(characters))

    font_files = sorted(
        (
            filename
            for filename in directory.rglob("*")
            if filename.is_file()
            and filename.suffix.lower() in EXTENSIONS
        ),
        key=lambda path: str(path).casefold(),
    )

    if not font_files:
        print(f"No font files found in {directory}")
        return

    results = []

    for filename in font_files:
        results.extend(
            inspect_file(filename, characters, directory)
        )

    if args.family:
        pattern = args.family.casefold()

        results = [
            result
            for result in results
            if pattern in result["family"].casefold()
        ]

    if args.families:
        print_families(results)
        return

    if args.csv:
        print_csv(
            results,
            characters,
            args.missing_only,
            args.all_present,
        )
    else:
        print(f"Scanning: {directory}")
        print(f"Font faces checked: {len(results)}")
        print()

        print_report(
            results,
            characters,
            args.missing_only,
            args.all_present,
        )

    if args.summary:
        print()
        print_summary(results, characters)


if __name__ == "__main__":
    main()
