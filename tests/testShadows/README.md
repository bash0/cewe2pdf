# Shadow fixture

Run from the repository root:

```bash
python -m pytest tests/testShadows -q
```

The album exercises image, masked-photo and clip-art shadows, including rotated
objects and CEWE shadow parameter variations. The shared portable resources are
selected by `cewe2pdf.ini`; no installed CEWE resources are required.

Album page 16 (PDF page 17 in single-page output) contains two examples of
passepartout 125186 (`12809-DECO-ZZ`), at 0 and 60 degrees. Its patterned frame
extends outside the photo opening and contains transparent holes. The plain
pink background 6044 makes those holes and the frame shadows visible. Both the
frame and its `fotoarea` descriptor are reused from the shared test resources.
Those three shared files were refreshed together from the editor's installed
resource: the older descriptor specified a wider photo opening and produced a
black padded strip with the new MCF's crop settings. Keep the XML, mask and
frame artwork from the same resource version. The refresh also changes the
existing examples on PDF page 7 of `unittest_fotobook` and PDF page 3 of
`testClipartColorReplacement`.

`test_passepartoutShadow.py` checks the combined silhouette, partial alpha,
photo offsets, full-frame shadow placement and drawing order. The existing
album comparison protects the resulting PDF. The Linux-only allowance for the
tennis-ball mask remains limited to PDF page 11; it does not apply to the new
frame examples.

The editor preview `test_shadows.mcf.preview.pdf` is useful for visual comparison;
it is a curved, shaded book mockup rather than an exact flat-page pixel reference.
New approved PDFs must be reviewed using the [test workflow](../README.md#approved-results-and-naming).
