# Centering album page content

`contenttocenter.py` adjusts the horizontal position of page content in a CEWE
album. It reads the edited MCF or MCFX and an explicit list of pages to center;
it does not need the original album or a record of how pages changed.

## Page selection

Page numbers are one-based editor page numbers. Use comma-separated page
numbers or inclusive ranges. Pages cannot repeat. For example:

```text
2-5,8,10-65
```

This selects pages 2 through 5, page 8, and pages 10 through 65 in the edited
album. Only selected pages are adjusted. CEWE album page 1 is on the right;
odd pages are on the right and even pages are on the left.

## Centering rule

For each selected physical page, the tool finds the horizontal bounding box of
all positioned areas, including rotated areas. It shifts every area on that
page by the same amount so the center of that bounding box matches the physical
page center. This preserves relative positions between photos, text, and other
elements. It does not scale, mirror, or move elements vertically. Pages with no
positioned areas are skipped; pages do not need to contain photos.

MCF positions use spread-wide coordinates. Areas are assigned to a physical
page by the center of their rotated horizontal bounds. Page backgrounds stored
separately from page areas are not translated.

## Run

From the repository root:

```text
python utilities/contenttocenter/contenttocenter.py --pages 2-65 --dry-run edited.mcf
```

Review the reported shifts and centered bounds. To write the corrected MCF,
omit `--dry-run`:

```text
python utilities/contenttocenter/contenttocenter.py --pages 2-65 edited.mcf
```

The output has the same format as the input. By default, this creates
`edited.centered.mcf` or `edited.centered.mcfx` beside the input and never
overwrites an existing file. For MCFX input, the tool uses the project's
`unpackMcfx()` reader and replaces only the embedded MCF in a copy of the
archive, preserving its other files. Use `--output corrected.mcf` or
`--output corrected.mcfx` to choose another destination with the matching
extension. Open the result in CEWE and inspect the changed spreads before
continuing to edit the album.
