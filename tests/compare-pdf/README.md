# PDF comparison helper

This is the project's modified local copy of [Formartha/compare-pdf](https://github.com/Formartha/compare-pdf), under its [MIT licence](LICENSE).

The helper compares PDF files in two ways:

- **Visual comparison:** renders PDF pages with PyMuPDF at 150 dpi and compares their RGB pixels using OpenCV.
- **Structural comparison:** compares page counts, bookmarks (document outlines), internal links and external links.

Both forms of comparison are enabled by default. The overall result is successful only if both comparisons pass.

## Environment and local copy

Use the converter's [supported environment](../../README.md#install).

Its pinned dependencies supply PyMuPDF, OpenCV, and NumPy.

Regression tests arrange imports through `configureTestImportPaths` in [testutils.py](../../testutils.py), so they use this local helper without a separate PyPI installation. An installed upstream version may not have this project's extensions.

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

Structural comparison is enabled by default. Use `--no-structure` to disable it and perform visual comparison only.

A key press dismisses a displayed page. Display modes require a working desktop OpenCV window environment, which may be unavailable in a headless CI/WSL session.

Command-line comparison is exact by default for visual comparison. The direct script prints its final result; it does not currently set an operating-system exit status from that result, so use the Python API/assertions for automated verification.

## Structural comparison

Structural comparison checks:

- **Page counts:** the PDFs must have the same number of pages.
- **Bookmarks:** bookmark titles, hierarchy levels and destinations must agree.
- **Internal links:** source pages and clickable areas, together with their destination pages and positions, must agree.
- **External links:** source pages and clickable areas, together with link types and target URLs, must agree.

Geometric comparisons use a tolerance of 0.01 PDF points. Titles, destination page numbers and URLs are compared exactly.

Structural comparison is independent of visual comparison. A PDF can look identical to another PDF but still fail structural comparison if, for example, a bookmark or hyperlink is missing or points to the wrong destination.

Structural comparison can be disabled through the Python API using `compare_structure=False`.

## Python API and page tolerances

`ComparePDF.compare()` returns a boolean. Both visual and structural comparisons are enabled by default.

A test may declare a narrowly scoped exception for visual differences with one-based PDF page numbers:

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

To perform visual comparison only:

```python
comparison = ComparePDF(
    [new_pdf, approved_pdf],
    ShowDiffsStyle.Nothing,
    compare_structure=False,
)
```

The numbers above illustrate the interface; measure the actual difference before choosing limits for a regression test. Platform selection belongs in that test, not in the comparator.

A tolerated page must meet all three limits:

- `max_different_pixels`: absolute number of changed pixels;
- `max_channel_difference`: largest absolute difference in any one RGB channel of any pixel, from 0 to 255;
- `max_combined_rgb_difference`: largest sum of absolute red, green, and blue differences at any one pixel, from 0 to 765.

Pages without a tolerance remain exact. Every non-exact comparison reports the measurements, including changed-pixel percentage. Accepted tolerances are logged with their reason; an exact match on a tolerated page reports that the allowance was unnecessary.

Page tolerances affect only visual comparison. They do not relax structural comparison.

See [test policy](../README.md#comparison-tolerances) for when an exception is appropriate.