# Background recolouring fixture

This fixture exercises ordinary backgrounds and CEWE hue/fading presets using
portable resources. The current interpretation, measurements and limitations
are recorded in [CEWE background recolouring](CEWE_BACKGROUND_RECOLOURING.md).

## Album and resources

The MCF contains 26 content pages:

| Album pages | Background and settings |
| --- | --- |
| 1-6 | 485, varied hues with fading 3 |
| 8-11 | 485, varied hues with fading 5 |
| 13-15 | 485, hue 0 with fading 3, 4 and 5 |
| 16-17 | Synthetic 6480, explicit hue 0/fading 0: red at source saturation |
| 18-19 | Synthetic 6480, hue 60 with fading 1 and 2 |
| 20-21 | Synthetic 6480, hue 210 with fading 3 |
| 22-23 | Synthetic 6480, hue 330 with fading 5 |
| 7, 12, 24-26 | White background 201 |

The [485 texture](../Resources/photofun/backgrounds/485.jpg) and
[synthetic 6480 image](../Resources/photofun/backgrounds/6480.jpg) are bundled
under the shared test resources. The fixture uses the ordinary resource lookup
with `cewe_folder = tests` and `hpsFolder = tests/hps`. Exploratory pages can
also use installed CEWE resources with a local configuration, but those resources
must be bundled before including such pages in portable regression runs.

## Running the tests

Run from the repository root:

```bash
python -m pytest tests/testColourBackgrounds/test_colourBackgrounds.py -q
```

The focused checks use three representative hue/fading pairs for shared pixel
properties. Calibration uses one measured saturated/pale strip pair per
available preset and the transform case for fading 4. Separate cases cover
hue wrapping, alpha preservation, missing versus explicit zero settings,
distinct invalid-input classes, and original-image fallback. There is no
hue-by-fading or background-ID-by-fading matrix.

Two complete conversions render the MCF in single-page and double-page output,
then compare with the newest approved PDFs in `previous_result_pdfs`. They do
not restrict background IDs, hue/fading combinations, alignment or overlaid
content. The expected output page count follows the MCF's content-page count.
Colour calibration is checked by the independent tests rather than by a fixed
table of settings on particular album pages. Both approved PDFs include the
reviewed spread-first fitting, so comparisons protect complete page appearance,
including geometry and overlaid content, as well as colour.

Candidate PDFs are written beside the MCF before comparison (currently 28 and
15 pages). Extending the album can therefore produce an expected comparison
failure while leaving both candidates available for inspection. Missing resources
and unsupported recolouring are still reported after rendering. Follow the
[test workflow](../README.md) for visual approval, reference updates and cleanup.

## Manual utilities

The three optional scripts live in `utilities/`. Each locates its inputs or
output relative to its own file, so it also works when launched from another
working directory. They are not imported or collected by the automated tests.

### Recreate the synthetic JPEG

[create_testBackground.py](utilities/create_testBackground.py) recreates the
1024 x 750 RGB diagnostic image using a fixed random seed. Its output is the
shared `tests/Resources/photofun/backgrounds/6480.jpg` resource.

```bash
python tests/testColourBackgrounds/utilities/create_testBackground.py
```

### Measure the 485 red pages

[measure_preview.py](utilities/measure_preview.py) reports median saturation
and interquartile ranges for album pages 13-15, shown on preview PDF pages 8-9.

```bash
python tests/testColourBackgrounds/utilities/measure_preview.py
```

### Measure the controlled 6480 strips

[measure_testStrips.py](utilities/measure_testStrips.py) reports median RGB and
saturation for the full, pale and grey strips on album pages 16-23, shown on
preview PDF pages 10-13.

```bash
python tests/testColourBackgrounds/utilities/measure_testStrips.py
```

## Reference preview and local experiments

The [CEWE reference preview](utilities/testColourBackgroundsPreview.pdf) is
retained beside the measurement scripts in `utilities/`. It is a watermarked,
curved CEWE book mockup, not a flat-page pixel reference or an approved
cewe2pdf result. Export a fresh preview to that location when deliberately
updating the fixture's comparison evidence.

The preview PDF, three utility scripts and two shared source JPEGs are useful
fixture material to retain in version control. Automated tests use the
measured colour samples without parsing the preview PDF. The exploratory
`485variations/` directory remains ignored and should stay out of the commit.

## Background fitting

Regular album backgrounds are cropped to the complete spread while preserving
proportions, then the renderer selects the left, centre or right page window.
Both PDF styles use this rule even beside a different design. Matching left/right records share
a crop anchor, and differing colours use the corresponding halves. This keeps
the ramp and strip boundaries consistent across the 6480 variants in single-page
and double-page output. The separate cover/inside-cover passes are unchanged.

The CEWE preview remains a curved, shaded mockup; its precise crop is not an
exact flat-page pixel reference. Visual comparison of the controlled strips
supports the fitting rule, including the corrected vertical fit in single-page
output. The approved cewe2pdf PDFs preserve that reviewed appearance; agreement
with them alone does not establish a match with CEWE.
