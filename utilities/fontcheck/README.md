# FontCheck

A small Python utility for inspecting Unicode character support in font files.

FontCheck recursively scans a directory for font files and reports which Unicode characters each font face can display. It is particularly useful when investigating missing glyphs and choosing fallback fonts.

## Requirements

- Python 3.10 or later
- [fontTools](https://fonttools.readthedocs.io/)

Install fontTools if necessary:

```powershell
pip install fonttools
```

## Running

Run from the repository root:

```powershell
python -m utilities.fontcheck.fontcheck
```

By default, FontCheck:

- Scans the current directory and all its subdirectories.
- Looks for `.ttf`, `.otf`, `.ttc` and `.otc` files.
- Checks Unicode characters U+263A and U+263B.
- Displays the font family and support status for each character.

TrueType and OpenType collections (`.ttc` and `.otc`) are inspected face by face.

## Command-line options

| Option | Description |
|---|---|
| `--directory PATH` | Directory to scan recursively (default: current directory). |
| `--character CHARACTER` | Character to check, either literally or as Unicode notation such as `U+263A`. Can be specified multiple times. |
| `--family PATTERN` | Only include font families whose names contain the specified text (case-insensitive). |
| `--families` | List distinct font families instead of checking glyph support. |
| `--missing-only` | Show only font faces missing at least one requested character. |
| `--all-present` | Show only font faces supporting all requested characters. |
| `--csv` | Output detailed results as CSV. |
| `--summary` | Show support counts for each requested character. |

`--missing-only` and `--all-present` are mutually exclusive.

## Examples

### Scan the current directory

```powershell
python -m utilities.fontcheck.fontcheck
```

### Scan a specific directory

```powershell
python -m utilities.fontcheck.fontcheck --directory tests\Resources\photofun\fonts
```

### Check different Unicode characters

```powershell
python -m utilities.fontcheck.fontcheck --character U+0177
```

Multiple characters can be specified:

```powershell
python -m utilities.fontcheck.fontcheck --character U+263A --character U+263B --character U+0177
```

Literal characters are also accepted:

```powershell
python -m utilities.fontcheck.fontcheck --character ŷ
```

### List distinct font families

```powershell
python -m utilities.fontcheck.fontcheck --families
```

### Filter by font family

```powershell
python -m utilities.fontcheck.fontcheck --family Arial
```

The filter is case-insensitive and matches part of the family name.

### Show only fonts with missing characters

```powershell
python -m utilities.fontcheck.fontcheck --missing-only
```

### Show only fonts supporting all requested characters

```powershell
python -m utilities.fontcheck.fontcheck --all-present
```

### Display a summary

```powershell
python -m utilities.fontcheck.fontcheck --summary
```

The summary reports the number of font faces checked and how many support each requested character.

### Export results to CSV

```powershell
python -m utilities.fontcheck.fontcheck --csv > fontcheck.csv
```

The CSV file can be opened in Excel.

CSV output uses UTF-8 with a byte-order mark (BOM) to help Excel recognise Unicode characters correctly.

It can be combined with the other filtering options:

```powershell
python -m utilities.fontcheck.fontcheck --all-present --csv > all-present.csv
```

```powershell
python -m utilities.fontcheck.fontcheck --family Bodoni --missing-only --csv > bodoni-missing.csv
```

**Note:** Do not combine `--csv` and `--summary` when producing a file intended for Excel, as the summary is additional text following the CSV data.

## Output

The normal report shows:

- Font file name and, for collections, face index.
- Font family name.
- Each requested character, its Unicode code point and whether it is supported.
- The glyph name when a character is present.

CSV output contains one row per font face, with columns for the file, face, family and each requested character.

A font is considered to support a character when its character map (cmap) contains the corresponding Unicode code point.

## Notes

- FontCheck examines font character maps; it does not test actual rendering.
- A character being present in a font does not guarantee that it will render correctly in every PDF library or application.
- Fonts with unusual or incomplete metadata may be reported with the family name `Unknown family`.
- Font inspection errors are written to standard error, leaving CSV output clean.