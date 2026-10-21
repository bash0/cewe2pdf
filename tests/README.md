# Tests and approved output

This guide owns the regression workflow, fixture conventions, approval procedure,
and generated-output cleanup. For source installation, use the [README](../README.md#install);
for architecture and linting, use the [developer guide](../documents/DEVELOPER_GUIDE.md).
Commands below run from the repository root in the intended Python environment.

For the purpose of the different test types, an assessment of existing coverage,
and priorities for future tests, see [Testing strategy and overview](../documents/TESTING_STRATEGY.md).

## Running tests

```bash
python -m pytest -rs
```

This runs the complete suite and reports skipped tests with reasons.
`python runAllTests.py` is the convenient stop-at-first-failure wrapper.

Focused examples:

```bash
python -m pytest tests/testCewePageResolver/test_cewePageResolver.py -q
python -m pytest tests/testCalendar -q
python -m pytest -rs --ignore=tests/testCalendar
```

New tests should also run directly as Python files, including from an IDE.
Use `configureTestImportPaths(__file__)` from [testutils.py](../testutils.py) to
locate the project and local comparison helper. A `pytest.main` entry point is useful
for fixture-based tests; retain established manual-output naming where it has a purpose.

[conftest.py](../conftest.py) sets `IGNORELOCALFONTS=1` so ordinary pytest runs do not
depend on the current user's installed fonts. Tests needing a different discovery
policy must isolate that change. System font loading is a separate opt-in setting.

## Fixture conventions

Most rendering tests have this shape:

```text
tests/testFeature/
  example.mcf
  example_mcf-Dateien/       source pictures, when needed
  cewe2pdf.ini               portable resource configuration
  test_feature.py
  previous_result_pdfs/      approved reference output
```

Use fonts and resources supplied with the tests. Confirm a fixture does not silently
borrow an installed CEWE mask, background, or private font.
Keep new MCFs readable by the editor where practical, with screenshots or notes for
reverse-engineered behaviour. Vary one parameter at a time for controlled investigations.
Related examples may belong in the same established feature MCF rather than separate
disconnected tests.

`testPageNumbers` demonstrates programmatic MCF variations.
`unittest_fotobook` deliberately accumulates historical bugs, unusual layouts, and
font-substitution cases; it remains useful alongside smaller focused tests.
Use mocks to isolate effects without replacing the behaviour under test: font-directory
scanning can be real while ReportLab registration is mocked to avoid global registry changes.

## Approved results and naming

Automated tests normally create dated output beside the input:
`example.mcf.20261020S.pdf`, with `S` or `D` denoting single/double
album presentation. MCFX tests retain `.mcfx` in the name. Calendar outputs use
`a4p.mcf.YYYYMMDD.pdf` and equivalent fixture names without an album S/D suffix.
Index PNGs may be numbered, for example `example.mcf.20261020S.idx.1.png`.
Some direct/manual runs intentionally use stable undated names.

Approved PDFs are retained under `previous_result_pdfs`. The newest approved filename,
rather than filesystem modification time, selects the reference; checkout timestamps
are not reliable evidence of approval order. Preserve established filename history.

When output changes:
1. Confirm the source fixture, configuration, code, and reference being compared.
2. Identify every changed page and explain the expected effect.
3. Inspect the actual PDF against CEWE or the intended behaviour.
4. Obtain the programmer's visual approval before promoting a candidate.
5. Run the relevant regressions and retain the accepted reference.

A passing pixel test proves agreement with the approved output, not exact CEWE
compatibility of a newly implemented feature. Never replace a reference merely to turn
a failure green. Use "approved result" in new documentation.

Add page-count and structural assertions when useful. Invisible links, bookmarks,
destinations, and page labels need object/target checks as well as pixel comparison.

## Comparing PDFs

Use the modified local [compare-pdf helper](compare-pdf/README.md).
Its documentation owns the CLI modes, Python interface, and tolerance measurements.
A rendered difference image is often more informative than a text comparison.
PDF timestamps, metadata, and object organization can differ while the rendered pixels match.

### Comparison tolerances

Exact comparison is the default. Any necessary exception must be measured, justified,
and scoped to the individual test and page. Put platform policy in the test, not in
the generic comparator. Do not broaden an allowance to hide an unexplained difference.
Review an allowance when the comparator reports it was unnecessary.

The Linux-only exception in [testShadows](testShadows/test_shadows.py) addresses a
reproduced native Cairo/CairoSVG rasterisation difference in the tennis-ball SVG mask.
It is limited to page 11; Windows and all other pages stay exact.
The current limits and evidence belong beside that test.
Pinned Python packages do not pin the operating system's native Cairo implementation.

## Manual inspection with installed CEWE resources

Portable regression tests deliberately use fixture resources and substitute some fonts.
For a real-resource visual check, copy the MCF and required image/resource tree to a
scratch album directory, configure the installed CEWE paths there, and run the converter.
Use `loadSystemFonts` or an album-local `additional_fonts.txt` only as needed.
Keep this output separate from the portable approved-result comparison.

In an IDE, use the repository as working directory and select the individual test file
when debugging it. Do not assume the working directory is the file's own directory.
Avoid changing committed fixture configuration just to inspect installed fonts.

The [older Windows notes](../documents/history/unittest_fotobook-windows-notes.md)
explain the separately retained installed-font illustration; they are historical,
not instructions for the normal regression run.

## Cleaning up temporary files

Run discovery from the authorized checkout root. Review candidate paths before removal;
retain outputs requested for inspection. Protect `previous_result_pdfs` and all album
resource directories, including names containing `Dateien`.
Never delete all PDF/PNG files recursively.

The following pattern covers dated MCF/MCFX test PDFs, numbered and unnumbered index
PNGs, and the known calendar fixture PDFs. Stable manual outputs and undated executable
smoke PDFs are deliberately outside this pattern.

### Windows

First discover candidates in PowerShell:

```powershell
$pattern = '^(test|unittest|allblack)[A-Za-z0-9._-]*\.mcfx?\.\d{8}[DS](\.pdf|\.idx(\.\d+)?\.png)$|^(a4[pl]|a5l|sq21)\.mcf\.\d{8}\.pdf$'
$generatedOutputs = @(Get-ChildItem -Recurse -File |
    Where-Object {
        $_.FullName -notmatch '\\previous_result_pdfs\\' -and
        $_.FullName -notmatch '\\[^\\]*Dateien[^\\]*\\' -and
        $_.Name -match $pattern
    })
$generatedOutputs | Select-Object FullName
```

After reviewing the list, recycle those exact candidates:

```powershell
Add-Type -AssemblyName Microsoft.VisualBasic
$generatedOutputs | ForEach-Object {
    [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(
        $_.FullName,
        'OnlyErrorDialogs',
        'SendToRecycleBin'
    )
}
```

### Linux and macOS discovery

```bash
find . -type f \( -name "*.pdf" -o -name "*.png" \) \
  ! -path "*/previous_result_pdfs/*" \
  ! -path "*Dateien*/*" \
  | grep -E '/((test|unittest|allblack)[A-Za-z0-9._-]*\.mcfx?\.[0-9]{8}[DS](\.pdf|\.idx(\.[0-9]+)?\.png)|(a4[pl]|a5l|sq21)\.mcf\.[0-9]{8}\.pdf)$'
```

Review the discovered files and use the desktop Trash or another agreed removal method.
Do not append an unchecked recursive deletion.
