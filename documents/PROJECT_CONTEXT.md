# cewe2pdf implementation rationale

These notes explain why the converter makes certain choices. They complement the
[architecture guide](DEVELOPER_GUIDE.md), [user guide](../README.md), and
[test workflow](../tests/README.md); configuration values and procedures belong there.
Check current code and fixtures when revisiting a decision.

## Interpreting an undocumented format

CEWE product identifiers and XML names are useful clues, not a complete specification.
Use actual per-page geometry, structural tags, installed resource data, and controlled
editor examples. A small fixture varying one parameter at a time is more convincing
than a plausible interpretation of an attribute's name.

Installed CEWE resources are the main real-user scenario. Small, portable fixture
resources exist to exercise the same loading and rendering mechanisms in CI.
Do not let a synthetic test substitute become the specification for normal conversion.
When installed resources are absent, use ordinary missing-resource diagnostics rather
than threading a special no-CEWE mode through every renderer.

## Architecture choices

The [developer guide](DEVELOPER_GUIDE.md#conversion-model) defines ownership.
Separate setup, rendering settings, mutable conversion state, and indexing to prevent
state leaking between successive albums in one Python process. Indexing is optional
output state, so it is passed only to paths that need it.

Specialist packages keep page traversal recognizable while isolating complex features.
Empty package initializers avoid creating another public interface to maintain.
Image rendering remains close to page-area traversal; extraction and generic image
utilities have different responsibilities.

Sequential rendering is deliberate. Parallel page conversion would require additional
font initialization, state coordination, merging, and log buffering without a
demonstrated benefit for typical album sizes. A GUI is a separate possible project,
not a prerequisite for converter changes.

## Page and background interpretation

The [page interpretation section](DEVELOPER_GUIDE.md#product-and-page-interpretation)
records the asymmetric opening and closing XML records. Keep that interpretation in
the resolver rather than spreading raw `pagenr` tests across renderers.
A raw `emptypage` is not uniformly an endpaper: the opening record can contain the
first editable content page.

The double-page default extends facing content-page backgrounds onto the endpapers
for a continuous PDF presentation. `insideCoverWhite` exists for readers wanting the
printed product's white endpapers. These are deliberate alternative presentations.

A visual background and an editor layout-template reference are different meanings of
"background"; only the former is a paint layer. Matching left/right records can
describe one continuous spread, while distinct records require independent rendering.
Image-background offsets must be applied once, not once for the spread and again for
its right-hand page. Aspect-preserving crops are preferred to copying the editor's
slightly softer or distorted resampling.

## Text layout and fonts

Normal text follows the HTML-like content rather than stale or conflicting
`textformat` attributes. Keep the established ReportLab layout path instead of
duplicating it in separate renderers.

Shrink-to-fit tolerates small metric differences before reducing a font. The style's
font size is already adjusted; multiplying it again when measuring ascent/descent or
leading was a double-scaling error. The unusual ascent fallback is generic and should
be tested with a portable fixture font, not a required proprietary font.

Simple tabs need a custom flowable because ordinary ReportLab paragraphs cannot place
the styled runs at the editor's tab stops. Complex cases retain a documented fallback;
its nonbreaking spaces do not mean the simple-tab renderer is unused.
Imported lists provide useful basic support without claiming exact editor indentation.

TextArt uses one ellipse renderer: a circle is the equal-axis case. Old and new MCFs
still obtain geometry differently. For current MCFs, the top inset scales with font
size, not box size: the original 490-unit box / 18-point calibration otherwise lets
large lettering rise above its area. Changing this anchor translates the curve;
it must not change its radii, direction, or character angles. `IndentMargin` reduces
the radii while retaining the centre. TextArt backgrounds and extra synthetic font effects require separate
evidence and scope.

Per-user fonts and operating-system fonts are different sources. The test environment
suppresses automatic per-user discovery; system font loading is opt-in.
Missing-font substitution is shared by calendars and albums. An active repository-root
`additional_fonts.txt` could silently influence many albums, which is why the supplied
example has a distinct filename. See [font configuration](../README.md#additional_fontstxt).

## Calendars

The MCF often stores a layout name without its semantics. Calendar resources provide
the base point sizes, alignment, padding, colours, language names, and event definitions;
the MCF percentages modify that style. Do not derive font size from the edited box or
attach special behaviour to a layout name's `(1)` or `(2)` suffix.

Portable tests map editor-faithful names to small fixture layouts and schemas.
The actual installed files remain authoritative in normal use.
Language-selected resources supply holidays and names; a missing resource must not
invent a national holiday calendar.

Preserve XML order for multiple captions. `free` and `show` events have different
holiday/emphasis roles. Wrap captions to their measured cell width; moving them does
not cure an overflow caused by missing wrapping. A personal-event thumbnail can replace
the date number instead of competing for space beside it. Image lookup prefers the
real MCF resource before a configured fixture fallback. Reuse the normal font
substitution mechanism.

## Shared decoration and shadow geometry

Decoration opacity multiplies existing alpha after cropping, masking, and corner
processing. Replacing alpha would discard transparency already in the image.
A passepartout's frame shares the photograph's opacity rather than becoming a
separately opaque overlay.

Images, clip art, and text use a common silhouette-shadow model.
Stored angles are page-relative; compensate for area rotation rather than inventing
different direction rules for masks, corners, and clip art.

Open-arrow fixtures revealed that protrusion expands silhouette bounds rather than
dilating every opaque stroke. `Utstikk` / `Überstand` is not the original object's
stroke width, and the exact CEWE algorithm remains empirical.
The calibrated spread, blur, and distance factors are documented beside the code in
[decorations/shadows.py](../decorations/shadows.py). Check that source before tuning;
validate against open and solid shapes, rotations, corners, and parameter series.
Moving a shadow cannot correct a silhouette that extends too far beyond both ends.
Check whether an apparent border is part of the photograph before changing decoration
geometry.

Text shadows use alpha from the actual laid-out ReportLab text, rendered through a
temporary transparent PDF and PyMuPDF. This preserves wrapping, fonts, spans, outlines,
and rotation without a simplified Pillow text implementation.
Minor accepted softness/darkness differences are specific visual judgments, not a
blanket permission to replace approved output.

## PDF additions without visual changes

Bookmarks, contents links, page labels, and web links should add navigation without
changing printed appearance. Their destination mapping uses actual output pages so
selections and double-page spreads remain correct.

Web links are added after rendering because introducing link markup changed wrapping.
Slash break opportunities still need checks with real fonts and long, styled URLs.
Group wrapped hits so a reader does not list each line as a separate logical link.
Pixel comparisons cannot prove that invisible annotations work; inspect their objects
and targets too.

Old generated index pictures can be saved back into a CEWE album. Recognize them from
the actual output stem and replace them with fresh index output, retaining recognition
of the former unnumbered PNG convention. The numbering and margin options are documented
in the [index user guide](../README.md#indexing-an-album-not-available-in-the-cewe-editor).

Photo-location links are opt-in and small by default to avoid accidental activation
while scrolling or zooming on touch devices. A URL template avoids provider-specific
code. Adding missing location metadata to the original photograph is preferable to
maintaining a second location database in the converter.

## Resource authoring and platform boundaries

When an authored CLP resource fails, establish that it follows CEWE's canvas conventions
before changing a renderer that already handles delivered resources.
The [CLP format notes](../clipart/CLP_FILE_FORMAT.md) own the encoding and authoring details.
Validate an original resource in the editor, then use identical portable fixture assets.

Windows CEWE discovery uses file associations because retailer branding makes directory
names unreliable. Explicit valid configuration takes precedence. Integration must leave
the editor's file associations intact and account for PyInstaller's same-name
bootloader process when detecting an Explorer launch.
Automatic logging includes named non-propagating loggers, otherwise important messages
would disappear from the album-side log.

A frozen executable has no source checkout to query for provenance, so its build
captures the Git description. The version constant is in a dependency-free module
so CI can read it before installing the full converter environment.
See [version numbering](DEVELOPER_GUIDE.md#version-numbering) and the
[build guide](build_a_compiled_version.md) for the maintained procedures.

## Revisiting decisions

These choices describe the current design rather than permanently excluding alternatives.
Bring a concrete use case, evidence, and regression coverage when proposing a change.
Keep superseded investigations in [history](history/README.md), not in the current
instructions. Avoid treating a local test count, old tool version, or transient CI
failure as a permanent project invariant.
