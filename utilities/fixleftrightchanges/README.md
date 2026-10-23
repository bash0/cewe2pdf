# MCF page layout repositioning

`fixleftrightchanges.py` corrects horizontal layout after pages have been
inserted, deleted, or rearranged in the CEWE editor. It reads the edited MCF
or MCFX and an old-to-new map of the pages that still correspond. The old
album is not needed; the map tells the utility which pages have changed from
left to right or right to left.

## Page map

Page numbers are one-based editor page numbers. Each comma-separated item maps
old page numbers to new page numbers with `:`. A single page or an inclusive
range can appear on either side. Ranges must have equal lengths and page
numbers cannot repeat. For example:

```text
1-2:1-2,3-8:4-9
```

This says pages 1 and 2 stayed in place, while old pages 3 through 8 became
new pages 4 through 9. Pages omitted from the map were inserted or deleted.
Only mapped pages that changed side are repositioned. CEWE album page 1 is on
the right; odd pages are on the right and even pages are on the left.

## Anchor and movement rule

The utility considers photo areas and all other positioned areas on the
physical page. It identifies the photo nearest the outer edge of that page:
after a side change, this was the photo nearest the old inner edge. Its gap to
the physical page edge records the former inner-margin spacing. The photo at
the opposite edge of the page's content becomes the new inner anchor. One
horizontal translation puts that photo at the same gap from the new inner
edge. Every positioned area on that page receives the same translation, so
relative placement, text, and photo arrangement stay intact. No scaling,
mirroring, or vertical movement is applied.

Pages without photo areas are skipped. The utility changes only pages whose
old and new page numbers have different parity. It does not infer a mapping or
move areas on unmapped pages. Page backgrounds stored separately from page
areas are not translated.

The MCF stores spread-wide coordinates. Each area is assigned to a physical
page by the center of its rotated horizontal bounds. The measured gap is to
the physical page edge; no separate safe-margin guide is encoded in the MCF.

## Run

From the repository root:

```text
python utilities/fixleftrightchanges/fixleftrightchanges.py --page-map "1-2:1-2,3-8:4-9" --dry-run edited.mcf
```

Review the reported anchor photos and offsets. To write the corrected MCF,
omit `--dry-run`:

```text
python utilities/fixleftrightchanges/fixleftrightchanges.py --page-map "1-2:1-2,3-8:4-9" edited.mcf
```

The output has the same format as the input. By default, this creates
`edited.repositioned.mcf` or `edited.repositioned.mcfx` beside the input and
never overwrites an existing file. For MCFX input, the tool uses the project's
`unpackMcfx()` reader and replaces only the embedded MCF in a copy of the
archive, preserving its other files. Use `--output corrected.mcf` or
`--output corrected.mcfx` to choose another destination with the matching
extension. Open the result in CEWE and inspect the changed spreads before
continuing to edit the album.
