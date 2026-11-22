# Clip-art colour replacement

Run from the repository root:

```bash
python -m pytest tests/testClipartColorReplacement -q
```

The portable INI selects the shared resources under `tests/Resources` and
`tests/hps`. No additional installed clip art is required.

PDF page 4 (album page 3, stored with its areas on MCF page 2) exercises
transparent replacement colours using the existing birthday balloons, design
104304 (`7065-CLIP-SF`). Yellow `#fae917` is replaced with `#000000,0`.
The yellow balloons and strings should disappear, revealing the pink background
and the red line behind them. White letters and the other colours remain visible.
The previous parser discarded the alpha suffix, making these parts opaque black.

`test_transparentColours.py` covers the MCF colour parser and real balloon
resource, plus SVG fills, strokes and gradient stops expressed in inline styles
or presentation attributes. It also checks colour-specific alpha when RGB is
unchanged, and its interaction with the whole object's opacity. The
[implementation notes](../../clipart/CLP_FILE_FORMAT.md#replacement-colours)
describe the representation used by the renderer.

The album regression compares against approved PDFs. Changed output requires
visual review using the [approval workflow](../README.md#approved-results-and-naming).
