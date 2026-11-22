
#!/usr/bin/env python3
"""
clp2svg - Extract SVG files from CEWE CLP files.

Usage:
    python -m utilities.clp2svg.clp2svg file.clp
    python -m utilities.clp2svg.clp2svg file.clp -o mask.svg
    python -m utilities.clp2svg.clp2svg *.clp -d output
"""

import argparse
from pathlib import Path


def decode_clp(clp_path: Path, svg_path: Path) -> None:
    """Decode a CEWE CLP file and write the resulting SVG."""

    text = clp_path.read_text(encoding="ascii").strip()

    # Check the CEWE CLP signature
    if not text.startswith("a"):
        raise ValueError("Unrecognised CLP file format")

    # Remove the signature and inserted characters g-z
    encoded = text[1:].translate(
        str.maketrans("", "", "ghijklmnopqrstuvwxyz")
    )

    # Convert hexadecimal data into bytes
    svg_data = bytes.fromhex(encoded)

    # Basic validation of the extracted content
    if not svg_data.lstrip().startswith(b"<"):
        raise ValueError("Decoded data does not appear to be SVG/XML")

    svg_path.write_bytes(svg_data)


def main():
    parser = argparse.ArgumentParser(
        description="Extract SVG files from CEWE CLP files."
    )

    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        help="One or more CLP files to decode",
    )

    output = parser.add_mutually_exclusive_group()

    output.add_argument(
        "-o", "--output",
        type=Path,
        help="Output filename (only valid with one input file)",
    )

    output.add_argument(
        "-d", "--output-dir",
        type=Path,
        help="Output directory (defaults to current directory)",
    )

    args = parser.parse_args()

    if args.output and len(args.files) != 1:
        parser.error("--output can only be used with one input file")

    output_dir = args.output_dir or Path.cwd()

    if args.output_dir:
        if not output_dir.is_dir():
            parser.error(f"Output directory does not exist: {output_dir}")

    successes = 0
    failures = 0

    for clp_path in args.files:
        try:
            if not clp_path.is_file():
                raise FileNotFoundError("File not found")

            svg_path = (
                args.output
                if args.output
                else output_dir / clp_path.with_suffix(".svg").name
            )

            decode_clp(clp_path, svg_path)

            print(f"OK: {clp_path} -> {svg_path}")
            successes += 1

        except (OSError, ValueError) as exc:
            print(f"ERROR: {clp_path}: {exc}")
            failures += 1

    print(f"\nCompleted: {successes} successful, {failures} failed")


if __name__ == "__main__":
    main()
