# cewe2pdf project context

This document records implementation decisions and the reasons behind them for programmers and coding assistants.
Use [AGENTS.md](../AGENTS.md) for working conventions,
[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for the architecture and test workflow,
and [README.md](../README.md) for supported behaviour and configuration.

These notes complement those documents. They do not require access to a particular conversation, computer, account, editor, or private resource collection.
Check the current code and fixtures before changing a recorded behaviour; update this document when a decision is deliberately replaced.

## Purpose and development approach

The main purpose is converting CEWE photograph albums from MCF/MCFX to PDF.
Calendars and Photo Pairs have explicit support; other editor products are not automatically supported.
MCFX files are SQLite containers holding the MCF and associated resources.

The converter interprets an undocumented format. Small fixtures, actual editor output, and resource data are stronger evidence than assumptions based on tag names.
Vary one parameter at a time when investigating behaviour. Prefer a general rule over a workaround for one object or product.
Empirical calibration is sometimes necessary, but record its purpose and validate it across related examples.

The code has evolved through several contributors. Improve maintainability through coherent extractions while preserving recognizable logic.
Do not refactor merely for visual consistency, remove small potentially useful utilities without a reason, or build abstractions solely to satisfy lint metrics.
Sequential rendering is the current design; parallel conversion would add font, state, merge, and logging complexity without a demonstrated benefit for typical workloads.
A graphical front end is not part of the current implementation.

## Cross-platform development

Python 3.12 is the supported development/CI baseline.
Use an isolated environment and requirements-pinned.txt to reproduce the Python dependency set.
Windows and WSL environments are separate even when given the same name; do not share a virtual environment between them.
[TestingOnWSL.md](TestingOnWSL.md) provides a Linux/WSL recipe.

Text line endings are a checkout concern rather than a universal Windows rule.
Follow repository attributes and explicit local conventions, otherwise preserve existing endings and keep unrelated newline changes out of a patch.
LF is normal for Linux/macOS development; a Windows programmer may prefer CRLF.
Do not convert binary assets as text: even an ASCII-looking PDF contains byte offsets that newline conversion can invalidate.
Git timestamps and content changes are separate; a newly created worktree can have newer timestamps without different source content.

Use resource discovery and platform-aware paths rather than machine-specific installation assumptions.
Tests should remain portable even when exercising Windows path syntax.
Close temporary files and SQLite connections explicitly; Windows prevents some operations on open files that Linux permits.
System font sets and native rendering libraries can vary between machines despite pinned Python packages.

## State and module boundaries

The current ownership model separates:

- ConversionSetup: prepared input, configuration, fonts, and resource mappings.
- RenderContext: shared rendering settings and resources.
- ConversionState: caches, missing-resource reports, temporary-file tracking, font substitutions, and counters for one conversion.
- AlbumIndex: optional index state, separate from general rendering state.
- AlbumConversionSession: lifetime of one conversion, including setup, canvas, saving, and cleanup.

Do not introduce mutable conversion globals or put unrelated state into a general context object.
The public convertMcf entry point delegates to the session.
cewePageResolver interprets CEWE page conventions; pages.py manages drawing and canvas policy; pageElements.py coordinates element z-order and specialist renderers.
The specialist packages are calendars, texts, decorations, fonts, indexing, and clipart; infrastructure contains configuration, paths, logging, versioning, and Windows integration.
Package __init__.py files intentionally avoid broad facades: import the module providing the operation.
Image rendering remains top-level because it is closely coupled to page-area traversal. Input extraction and generic image utilities have distinct roles.
See the developer guide for the complete source map.

## Regression evidence and approved output

Pixel comparison is central to safe changes in this renderer.
A passing comparison proves consistency with the approved result, not correctness of a newly implemented feature against CEWE.

A feature change should:

1. Have a reproducible MCF/MCFX fixture and, where available, editor screenshots.
2. Explain the relevant tags/resources and intended visual change.
3. Exercise the actual rendering path and expected page count.
4. Include focused structural assertions where pixels cannot protect the behaviour.
5. Identify and visually inspect changed pages before the programmer approves replacement output.
6. Pass the relevant regressions and update documentation.

Use portable test fonts and resources rather than a developer's private fonts or installed CEWE content.
A test MCF should remain readable by the editor where practicable.
Prefer adding related parameter variations to an established feature fixture when the same algorithm affects all of them.
Use a dedicated fixture when that better isolates the case.

unittest_fotobook deliberately combines historical bugs and unusual cases, including font substitution.
Its diagnostic noise does not make it redundant. New functionality should still have focused coverage.
Tests should run via pytest and directly as Python files; configureTestImportPaths(__file__) supports the import setup.
Preserve meaningful distinctions between stable manual output names and dated automated results rather than renaming old files solely for consistency.

conftest.py sets IGNORELOCALFONTS=1 to keep pytest independent of user-installed fonts.
runAllTests.py normally stops at the first failure; python -m pytest -rs runs the complete collection and reports skipped reasons.
Use the repository flake8/pylint configuration and explain intentional suppressions.

Mocks should isolate expensive or destructive effects without replacing the behaviour being tested.
For example, system-font discovery can scan actual platform directories while registration is mocked to avoid mutating ReportLab's process-wide registry.

### Narrow comparison tolerances

ComparePDF remains exact by default.
An exceptional tolerance is declared by the individual test for a specific one-based PDF page; platform selection belongs in the test rather than the comparator.
PageTolerance requires an explanation and limits all three measurements:

- number of changed pixels;
- maximum per-channel RGB difference, from 0 to 255;
- maximum combined RGB difference at any pixel, from 0 to 765.

Accepted differences are logged explicitly. An exact match on a page with a configured tolerance reports that the tolerance was unnecessary.
Do not weaken a limit simply to hide an unexplained regression.

The existing Linux-only testShadows page-11 allowance addresses measured native Cairo/CairoSVG differences in a tennis-ball SVG mask.
The observed difference was 146 pixels, channel maximum 14, combined maximum 41; the test limits are 160 / 15 / 45.
Windows and the other pages remain exact.
This is a documented exception, not a general allowance for platform differences.

### Output cleanup

Use the current README cleanup section as the source of the discovery patterns.
Generated output includes dated MCF/MCFX PDFs, index PNGs, and calendar PDFs without the album S/D suffix.
Approved PDFs under previous_result_pdfs and source images under Dateien directories must be excluded.
Review candidates before removal, prefer a reversible method, and keep outputs requested for inspection.
Do not delete all PDFs or PNGs recursively.

## Product and page interpretation

MCF structure and actual per-page bundlesize take precedence over marketing product identifiers.
ProductInfo.ceweFormats supplies fallback dimensions and diagnostics.
PdfProductStyle describes the output presentation rather than the printed product's name.
Calendar tags identify calendar structure, with CAL identifiers as compatibility fallbacks.
MEM3 Photo Pairs uses independent-card semantics instead of album cover/spread rules.
Do not assume every album contains only 26 content pages.

Album XML is asymmetric:

- fullcover supplies outer-cover and spine artwork. The separate spine record is structural metadata, not an independently rendered page.
- The opening emptypage can contain the first editable content page, while normal page 1 supplies its background.
- The final normalpage contains closing content; the trailing emptypage represents the back endpaper.
- Therefore raw emptypage cannot uniformly mean an inside cover.
- The processing vocabulary separates FrontInsideCoverBackground, OpeningContentPage, and BackInsideCover.
- Single-page PDFs omit endpapers. Double-page PDFs normally extend facing content-page backgrounds onto them; insideCoverWhite=True selects white printed-style endpapers.

The cewe2pdf.page_rendering debug logger records actual canvas operations around opening/closing content and endpapers.
loggerconfig.yaml is read from the process working directory, which an IDE may set to the project root.

--pages selects editable content-page numbers and cover, for example cover,1-12,15.
CLI zero is rejected; the legacy programmatic integer interface retains its defined zero-as-cover compatibility.
Selecting either member of a double-page spread selects the complete physical spread.
Output is de-duplicated and emitted in natural order.
Calendar cover means its front cover; Photo Pairs rejects cover.
Partial selection has a concise mustsee diagnostic; argument syntax errors use argparse's early diagnostic.
Keep product dispatch explicit and reject unsupported styles.

### Backgrounds

Distinguish a visual background tag from an editor layout-template reference; the latter is not another paint layer.
Regular alignment 1/2/3 selects left/centre/right crops while preserving aspect ratio.
Matching left/right background records can describe a continuous spread; separate records render independently.
BUNDLE photo backgrounds span the spread. Avoid applying the right-page offset twice.
Sharper aspect-preserving cropping is an accepted choice even where the editor's resampling looks slightly softer.

## Text, font, and PDF decisions

Normal text layout primarily follows the HTML-like text rather than stale or conflicting textformat values.
Reuse the established ReportLab layout path and shared font substitution.

Shrink-to-fit allows a small explicit overflow tolerance before reducing the font.
Diagnostics should explain original frame height, adjusted height, shrink percentage, and space required by unshrunk text.
Font size already includes its scale adjustment; do not apply the factor a second time when calculating metrics.
The unusual ascent/leading fallback should be exercised with portable fonts, rather than requiring a proprietary CEWE font.

Simple left-aligned, unwrapped tabbed paragraphs use a custom flowable with 8 mm tab stops, preserving styled runs, outlines, spacing, and transparency.
Complex tab combinations retain a documented fallback; nonbreaking spaces on that route do not mean the simple-tab implementation is unused.
Basic imported bullet and numbered lists are supported without a promise of exact editor indentation/wrapping.

TextArt uses a common ellipse renderer; circular text is the equal-axis case.
Retain the necessary legacy/current geometry inputs. IndentMargin reduces radii while retaining the centre.
TextArt background rendering remains outside the implemented feature set.

### Font sources and configuration

Keep these sources distinct:

- CEWE-delivered fonts;
- per-user local fonts, automatically discovered unless IGNORELOCALFONTS suppresses them;
- system font folders, enabled by loadSystemFonts=True (default False) or explicit configuration.

additional_fonts.txt is optional; lookup uses the first file found in the album directory, working directory, then program location.
The root additional_fonts.example.txt is an example rather than active default configuration.
Use the existing missing-font substitutions, including ReportLab standard fonts, for calendars as well as albums.
A missing CEWE installation should degrade through ordinary missing-resource diagnostics, without a missing-installation flag threaded through every renderer.
Installed CEWE resources remain the principal real-user scenario; portable test resources exercise the same mechanisms.

### Indexing and invisible PDF features

Indexing is a cewe2pdf extension.
Single- and multi-page indexes use numbered .idx.1.png, .idx.2.png output.
Continue recognizing legacy unnumbered index images when excluding stale results saved back into an album.
Identify old index resources from the actual output stem.
Index PDF margins control pagination; PNG placement margins control the finished image's size and position.

Indexes provide bookmarks and clickable contents rows targeting actual output pages.
PDF page labels work independently of indexing, including covers, selections, and spreads.
Test destinations and annotations as well as visible pixels.

HTTP(S) link annotations are added after text rendering to preserve appearance.
Links keep the editor's text colour; automatic blue styling is not part of the feature.
URL wrapping uses slash opportunities. Cover long URLs, styled spans, query strings, and reader behaviour.
Group wrapped hits so readers do not report each line as a separate logical link.

PDF_METADATA supplies optional title and author; absent/blank title uses the filename fallback.
PDF_GEO_LINKS is opt-in and uses EXIF GPS.
Its default invisible hotspot is 10 mm square at the photo's top-left, clamped to the photograph; a sufficiently large hotspotSizeMm links the whole image.
A configurable URL template supports different map providers.
Adding missing GPS metadata to the original photograph is preferable to maintaining a second location database in the converter.

## Calendars and resource-driven layouts

Read calendar style, names, holidays, and personal events from the MCF and installed resources.
Do not hard-code national holidays, month names, product coordinates, or behaviour keyed to a layout's '(1)'/'(2)' suffix.
- calendar_layout.xml supplies base sizing, alignment, padding, and borders.
- calendar_schema.xml supplies colours.
- CalendarWeekNames.xml supplies localised names.
- The MCF language selects holiday resources; missing data should not invent holidays.

Portable tests use small fixture resources and explicit [CALENDAR] schema/layout substitutions while retaining editor-faithful MCF names.
Normal installed resources remain authoritative for actual conversions.
Skip calendar resource loading for non-calendar products.

Preserve XML order for multiple event captions. free and show events have different holiday/emphasis roles.
Wrap captions using actual font metrics and usable cell width.
A personal-event thumbnail can replace the day number rather than being fitted alongside it.
Image lookup prefers the actual MCF resource before configured fixture fallback.
Reuse shared font substitution; synthetic bold remains a possible refinement rather than an established requirement.

## Decorations, opacity, and shadows

Supported corner shapes are default, convex, bevelled, notched, and concave.
Borders must respect corner geometry, width, gap, and position, including use on non-image objects.

Decoration alpha multiplies existing image alpha after crop/masks/corners.
A passepartout frame shares the photograph's opacity; it must not subsequently be painted fully opaque.
An accepted small tonal difference in one comparison does not establish exact compositing equivalence.

Images, clip art, and text use a shared silhouette-shadow model.
Stored shadow angles are page-relative, so compensate for image-area rotation.
Masks and corners affect shape rather than selecting a separate direction rule.
Open-arrow fixtures established that protrusion expands the silhouette's bounds rather than dilating every opaque stroke.
Utstikk / Überstand is not the original object's stroke width; its exact rendering remains empirical.

Current shadow calibration uses spread 0.30, blur 0.5, and distance 0.70 scales; verify the source before adjusting them.
Validate a change against both open and solid silhouettes, corners, rotations, and parameter series.
Do not change distance to correct a shadow projecting too far beyond both ends.
Check whether an apparent border belongs to the photo itself before changing decoration geometry.

Text shadows obtain alpha from actual laid-out ReportLab text through a temporary transparent PDF and PyMuPDF, then use the shared shadow processor.
This preserves rich-text layout instead of duplicating it with a simplified font renderer.
The integrated testShadows fixture checks the common algorithm across object types.
Minor residual softness/darkness differences require explicit visual review, not automatic replacement of approved output.

## CLP and authored resources

CLP stores hex-encoded SVG with an a prefix; reuse ClpFile's conversion facilities.
The old cliparts_default.xml registration advice is obsolete; resources are discovered from the filesystem.
The original custom travel-frame fixture uses designElementId 990001.

Frame and mask SVG canvases follow different aspect-ratio conventions:
the frame matches the full passepartout; the mask matches the fotoarea photo window.
When an authored resource fails, check that convention before changing a renderer that already handles delivered CEWE resources.
Validate authored resources in the editor where possible, then copy identical assets into portable test resources.
Changes to an installed CEWE resource store are separate from repository edits and require the programmer's authorization.
See [CLP file format notes](../clipart/CLP_FILE_FORMAT.md) for detailed authoring notes.

## Packaging, integration, and versioning

Keep Windows-only conveniences separate from normal Python operation on all supported platforms.
The requirements split is deliberate:

- requirements.txt: direct converter/test dependencies.
- requirements-pinned.txt: reproducible Python development/CI versions.
- requirements-winexe.txt: Windows PyInstaller overlay.

Windows executable tooling is not required merely to develop on Linux/macOS.
The Windows executable bundles Cairo and required libraries; users should not need a developer environment.
Test a frozen build as an executable rather than assuming source tests prove packaging.
The Linux executable workflow is manually triggered.

PROGRAM_VERSION lives in a dependency-free module.
Maintainers choose major/minor versions; the canonical master workflow adds successful build tags.
Source and frozen runs report available version/provenance and support --version.
Retrieve the version through Python imports, not fragile matching of source text.

Windows discovery uses existing file associations to avoid guessing retailer-branded CEWE directories.
A valid explicit configuration takes precedence; automatic mode can discover CEWE when configured paths are absent or stale.
Preserve the editor's .mcf/.mcfx double-click association.
The converter adds an Explorer context-menu command.
An argumentless terminal launch does not install integration; --install is explicit, while Explorer double-click of the frozen executable may offer installation.
Explorer detection accounts for PyInstaller's same-name bootloader ancestor.
Automatic conversion logs are overwritten each run and include non-propagating named loggers without duplicate lines.
cewe_folder.txt is obsolete: warn but do not read it.
Locked output files should fail with a useful diagnostic.

## Scope and future changes

The decisions above describe the present design rather than permanently excluding future proposals.
Revisit them when a concrete use case and evidence justify the change.
Examples needing separate scope include parallel rendering, a GUI, automatic link styling, TextArt backgrounds, and additional synthetic font effects.
Avoid speculative additions while fixing a narrower rendering defect.
Do not preserve a stale test count, local build result, or transient CI failure as a project invariant.
