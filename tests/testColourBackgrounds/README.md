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
under the shared test resources. The fixture INI uses the ordinary resource
lookup with `cewe_folder = tests`; it does not depend on an installed CEWE
background or the modified downloaded resource used for the experiment.

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

Two complete conversions check both background designs and their integration
with single-page and double-page output. They create 28-page and 15-page dated
candidate PDFs beside the MCF, retaining them for review. There are no approved
result PDFs for this fixture yet; colour assertions are not visual approval.
Follow the [test workflow](../README.md) for approval and cleanup.

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

## Deferred fitting investigation

The diagnostic strips expose a vertical-fitting difference: the CEWE mockup
trims more of the grey ramp than the current flat-spread PDF. No fitting change
is included in this colour work. The tests protect the current placement and
colour behaviour; they do not establish an exact CEWE geometry match.
