# PDF visual comparison helper

This is the project's modified local copy of
[Formartha/compare-pdf](https://github.com/Formartha/compare-pdf), under its
[MIT licence](LICENSE). It renders PDF pages with PyMuPDF at 150 dpi and compares
their RGB pixels using OpenCV.

## Environment and local copy

Use the converter's [supported environment](../../README.md#install).
Its pinned dependencies supply PyMuPDF, OpenCV, and NumPy.
Regression tests arrange imports through `configureTestImportPaths` in
[testutils.py](../../testutils.py), so they use this local helper without a separate
PyPI installation. An installed upstream version may not have this project's extensions.

## Command-line comparison

From the repository root:

```bash
python tests/compare-pdf/compare_pdf/compare_pdf.py \
  --pdf path/to/new.pdf --pdf path/to/approved.pdf --showdiffs=diffimage
```

Use at least two `--pdf` arguments. `--showdiffs` accepts:
- `nothing`, the default: report differences without opening windows;
- `sidebyside`: show the differing pages beside one another;
- `diffimage`: show differing pixels against a white background.

A key press dismisses a displayed page. Display modes require a working desktop
OpenCV window environment, which may be unavailable in a headless CI/WSL session.
Command-line comparison is exact. The direct script prints its final result;
it does not currently set an operating-system exit status from that result, so use
the Python API/assertions for automated verification.

## Python API and page tolerances

`ComparePDF.compare()` returns a boolean. Existing callers remain exact by default.
A test may declare a narrowly scoped exception with one-based PDF page numbers:

```python
from compare_pdf import ComparePDF, PageTolerance, ShowDiffsStyle

comparison = ComparePDF(
    [new_pdf, approved_pdf],
    ShowDiffsStyle.Nothing,
    page_tolerances={
        11: PageTolerance(
            max_different_pixels=200,
            max_channel_difference=2,
            max_combined_rgb_difference=4,
            reason="Brief explanation of the known rendering variation.",
        ),
    },
)
assert comparison.compare()
```

The numbers above illustrate the interface; measure the actual difference before
choosing limits for a regression test. Platform selection belongs in that test,
not in the comparator.

A tolerated page must meet all three limits:
- `max_different_pixels`: absolute number of changed pixels;
- `max_channel_difference`: largest absolute difference in any one RGB channel of any
  pixel, from 0 to 255;
- `max_combined_rgb_difference`: largest sum of absolute red, green, and blue differences
  at any one pixel, from 0 to 765.

Pages without a tolerance remain exact. Every non-exact comparison reports the
measurements, including changed-pixel percentage. Accepted tolerances are logged with
their reason; an exact match on a tolerated page reports that the allowance was
unnecessary. See [test policy](../README.md#comparison-tolerances) for when an exception
is appropriate.
