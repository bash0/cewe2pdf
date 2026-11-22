# CEWE background recolouring: interpretation and evidence

These notes describe the current empirical model used by
[`backgroundColouring.py`](../../backgroundColouring.py). It was checked with
the 485 texture and a controlled synthetic JPEG substituted for downloaded
background 6480. It is not an official CEWE specification.

The [fixture guide](README.md) owns the album layout, test commands, utility
locations, reference material and candidate-PDF workflow. The retained
[CEWE reference preview](utilities/testColourBackgroundsPreview.pdf) lives
beside the measurement scripts in `utilities/`.

## MCF interpretation

An image-background record identifies its resource with `designElementId` and
can explicitly select a colour with `hue` and `fading`:

```xml
<background alignment="1" designElementId="6480" fading="0" hue="0" rotation="0" type="1"/>
```

Missing hue/fading attributes retain the source image. Explicit zero values
have a different meaning: hue 0 selects red, and fading 0 retains the source
saturation. Pages 16-17 show that distinction: their rainbow source strips
become red and pale red in CEWE's preview.

Hue is an angle in degrees, wrapped modulo 360. The fading value identifies
a preset; numerical order does not mean steadily increasing fading. The
current saturation multipliers are:

| Fading | Source-saturation multiplier | Evidence |
| --- | --- | --- |
| 0 | 1 | Controlled 6480 strips, pages 16-17 |
| 1 | 1/2 | Controlled 6480 strips, page 18 |
| 2 | 1/4 | Controlled 6480 strips, page 19 |
| 3 | 180/255, approximately 70.6% | Controlled 6480 strips, pages 20-21; 485 variants |
| 4 | 90/255, approximately 35.3% | Intermediate factor supported by the 485 comparison |
| 5 | 45/255, approximately 17.6% | Controlled 6480 strips, pages 22-23; 485 variants |

The factors are explicit empirical settings. The 8-bit values approximate the
measured strips; fading 4 halves the factor for 3 and doubles that for 5. A
controlled 6480 example of fading 4 has not been supplied. No formula is
inferred for other preset values.

Both attributes must be supplied for recolouring. Incomplete, malformed,
nonfinite or unsupported combinations produce a warning and retain the
original image. The renderer applies the model to image-background type 1
regardless of the design ID.

## Colour transform

1. Convert the source RGB pixels to HSV.
2. Replace hue with the selected MCF angle.
3. Multiply each pixel's original saturation by the preset factor.
4. Preserve each pixel's HSV value, the maximum RGB channel.
5. Convert back to RGB.

Grey pixels stay grey, black stays black, and relatively pale source colours
remain relatively pale. The pure transform returns a new image, preserving
alpha where present and leaving the source unchanged. Pillow's 8-bit HSV
conversion introduces rounding. No brightness correction is applied.

The initial 485-only investigation suggested replacing saturation with a
uniform value. The synthetic test disproved that interpretation: its grey
ramp stays neutral and its saturated/pale strip pair retains roughly the
original 100%:40% saturation ratio. Output saturation percentages measured in
485 therefore cannot be used as universal multipliers or fixed output values.

## Controlled 6480 experiment

The synthetic 1024 x 750 RGB JPEG contains:

- A grey brightness ramp from 32 to 255.
- Six hues at HSV value 224 and saturation 100%.
- The same hues at value 224 and saturation 40%.
- A reproducible warm mottled texture with varying brightness.

The editor did not offer an arbitrary local-background import. The experiment
replaced the downloaded 6480 JPEG while retaining its filename and resource ID;
the portable tests use an identical JPEG under the shared test resources.

6480 originally lacked recolouring attributes. Its local template XML was
given `multicolor="1"` and `multicolor_id="9008"`, matching the 485 template,
with the original XML backed up. The catalogue JSON was unchanged. After
restarting, resource-ID search exposed many colour variants, while the category
listing did not offer a palette. The saved variants retained design ID 6480
and stored their selected hue/fading in the MCF.

The full meaning of `multicolor_id="9008"` remains unconfirmed. The converter
uses the MCF selections and JPEG pixels, rather than reading these companion
metadata files to decide whether to recolour.

## Measurements

Representative strip-interior measurements from the CEWE preview are:

| Fading | Hue | Full-strip RGB | Full-strip saturation | Pale-strip RGB | Pale-strip saturation |
| --- | --- | --- | --- | --- | --- |
| 0 | 0 | 224, 0, 0 | 100.00% | 224, 134, 134 | 40.18% |
| 1 | 60 | 224, 224, 112 | 50.00% | 225, 224, 178 | 20.89% |
| 2 | 60 | 226, 225, 169 | 25.22% | 224, 223, 202 | 9.82% |
| 3 | 210 | 66, 145, 224 | 70.54% | 161, 192, 223 | 27.80% |
| 5 | 330 | 223, 184, 203 | 17.49% | 224, 209, 216 | 6.70% |

Source value is 224 in both colour strips. The grey ramp remains neutral in
every case. JPEG compression, book curvature and shading make the measurements
approximate; they are not flat-page pixel references. Automated transform
tests retain representative measured RGB values with a four-level per-channel
allowance, without parsing the reference preview PDF during automated tests.

The separate 485 red pages 13-15 give median output saturations of approximately
45.0%, 24.2% and 11.0% for fading 3, 4 and 5. Fading 4's interquartile range is
23.0%-25.5%. These describe regions of that particular texture and support an
intermediate preset, rather than a uniform saturation rule.

### Reproducing the sampling

[measure_testStrips.py](utilities/measure_testStrips.py) renders preview PDF
pages 10-13 at 1600 pixels wide. It samples horizontal fractions 0.07-0.11 on
the left or 0.90-0.94 on the right, avoiding the gutter and watermark. Vertical
fractions 0.32-0.40, 0.52-0.62 and 0.20-0.24 sample the saturated, pale and grey
strips respectively. It reports median RGB and per-pixel HSV saturation.

[measure_preview.py](utilities/measure_preview.py) samples the 485 red pages
on preview PDF pages 8-9, also at 1600 pixels wide. Horizontal fractions are
0.10-0.40 on the left or 0.60-0.90 on the right; vertical fractions are
0.18-0.34. It excludes pixels with red at most 80 or without a dominant red
channel, then reports median saturation and its interquartile range.

## Remaining limits

Calibration has been checked against 485 and the controlled 6480 image. The
same transform is applied to other image-background designs with supported MCF
settings, but that does not establish exact compatibility with every CEWE
resource family or editor version.

The diagnostic strips also reveal a vertical-fitting difference between the
CEWE mockup and the current flat-spread PDF. Fitting is a separate, deferred
investigation. This colour implementation preserves the existing geometry;
approved PDF regressions protect that established behaviour.
