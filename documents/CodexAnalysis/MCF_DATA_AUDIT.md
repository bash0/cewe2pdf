# Unused MCF data and possible missing features

Ignored MCF data provides investigation leads, not an implementation backlog.
The target is output that users can create through CEWE's editor. This audit
identifies unused paragraph-spacing and vertical-margin data, but does not
demonstrate native editor controls for those settings. A controlled background
colour check instead confirmed whole-text-box behaviour, which the converter
already supports. Most other unused data describes editing history, layout
provenance, cached assessments or print production.

The corpus snapshot is from commit `c6af821`, checked on 23 November 2026;
handling notes also record subsequent findings and the drawing-order diagnostic.
It covers all 38 tracked `.mcf` fixtures and the MCF payload in each of the
three tracked `.mcfx` fixtures under `tests/`. The inventory contains 198 XML
attribute paths, seven XML text-content paths, one embedded-HTML payload path,
and 62 HTML attribute/CSS declaration paths. These are distinct fields by context,
not counts of independent features. Related MCF and MCFX fixtures can repeat the
same examples.

The [complete field inventory](MCF_FIELD_INVENTORY.md) records each field's
occurrence count, classification, code evidence and an example fixture. Counts
are a snapshot, not constraints on future fixtures. Personal source paths and
image metadata values are not reproduced.

## Implementation scope

A new feature needs a reproducible example from an accepted CEWE workflow and
an observable mismatch in the converted output. Native editor controls are the
primary scope. Selected pasted formatting can be included deliberately, as with
the existing bullet-list support; this does not imply general support for every
HTML feature that CEWE's underlying Qt engine can display.

Hand-written MCF variants and generic Qt documentation can establish how a field
is parsed or rendered, but cannot establish that users can create it in CEWE.
Even retaining a setting when saving imported or hand-written HTML is weaker
evidence than creating it through the editor. Where no supported creation path
is known, defer implementation rather than manufacturing a fixture in XML.

## Scope and interpretation

The inventory uses tracked fixtures, including `testMcfxExtraction/McfOriginals`,
and reads the MCFX databases without extracting or modifying their contents.
Ignored local copies, generated scratch albums, Python-generated test variations,
and attributes appearing only in installed CEWE resources are outside this count.
Embedded Qt HTML is included: inspecting only the outer XML would miss useful
formatting omissions.

Code inspection follows the conversion/session setup, page resolver, area
dispatch, and image, text, clip-art, decoration and calendar renderers. A matching
attribute name somewhere in Python is insufficient evidence: for example,
`position/@width` is used, while `calendararea/@width` is not. Conversely,
`corner/@where` and several page selectors are used through XPath expressions.
An ignored attribute may still be present in the parsed XML tree; "used" here
means that the converter interprets it for output, routing or diagnostics.

The categories distinguish:

| Category | Meaning |
| --- | --- |
| Used | Interpreted by the current converter; not a claim of exact CEWE fidelity. |
| Partial | Only part of the setting or its possible contexts are interpreted. |
| Visible candidate | Ignored data with a possible visual effect; not proof of a feature users can create. An accepted editor workflow and a visible mismatch are needed before implementation. |
| Duplicate representation | Ignored here, with an effective representation used elsewhere. This is often harmless. |
| Editor bookkeeping | Editing defaults, identifiers, provenance, layout assistance or cached assessments. |
| Print production | Manufacturing, material, enhancement or special-finishing settings. |
| Deferred formatting | Rich-text properties without an established native creation path; pasted formatting is considered only by deliberate scope choice. |
| Deferred capability | A confirmed or potential extension deliberately postponed until needed; its confirmation status is described in the relevant section. |
| Intentional omission | A saved option deliberately excluded from PDF output, rather than an outstanding feature request. |
| Uncertain | Insufficient evidence to assign a precise meaning or visible effect. |

Meaning confidence and code-handling confidence differ. It is possible to know
that a field is ignored without knowing exactly what CEWE intends it to do.

## Rendering data and creation workflows

### Paragraph spacing and indentation

Paragraph `margin-top` and `margin-bottom` occur with both `0px` and `12px`.
The renderer reads paragraph `line-height`, but does not transfer paragraph
margins or `text-indent` to its ReportLab paragraph styles. List margins and
Qt list indentation also are not interpreted; list-marker indentation is
calculated from the font size instead. See
[`processTextParas`](../../texts/areas.py) and
[`processTextLists`](../../texts/lists.py).

These properties have actual layout meanings in
[Qt's supported rich-text HTML subset](https://doc.qt.io/qt-6/richtext-html-subset.html).
This establishes the properties' generic meaning, not their availability in
CEWE's UI. Changing paragraph margins from zero to 30 in a controlled rendering
probe produced identical pixels. The supported `line-height` control changed
the output. Nonzero examples occur in MCF page records 2, 4 and 6 of
[testShadows](../../tests/testShadows/test_shadows.mcf), and record 4 of
[testTextBox](../../tests/testTextBox/testTextBox.mcf).

The `testTextBox` example originated as hand-written font-inheritance HTML in
commits `a7ea594` and `d9ce149`, without paragraph margins. Commit `1edd08f`,
which saved it through the editor, introduced the `12px` top/bottom margins.
This is consistent with the default paragraph margins in
[Qt's HTML importer](https://raw.githubusercontent.com/qt/qtbase/5.15/src/gui/text/qtexthtmlparser.cpp).
It does not demonstrate a CEWE UI control for paragraph spacing. The visible
line-spacing and text-box edge-distance controls are separate settings.

Wrapper-table margins are a separate case: the four margins on the legacy
`body/table` wrapper are already read. Likewise, the newer XML `IndentMargin`
is read and applied to all four text-frame sides when no wrapper table exists.
Those are not evidence of support for paragraph-level margins.

**Creation path not established:** the inspected text panel exposes line spacing
and text-box padding, not paragraph spacing before/after. Defer this lead unless
a native creation path is found or a particular formatted-paste workflow is
deliberately brought into scope. Hand-written margin variants would not establish
that it is a CEWE feature the converter should implement.

### Text background highlighting

`span/style/background-color` occurs as `#ffffff` and `transparent`, including in
[testFontSubstitution](../../tests/testFontSubstitution/testfontsubstitution.mcf),
[testLists](../../tests/testLists/testlists.mcf) and
[unittest_fotobook](../../tests/unittest_fotobook/unittest_fotobook.mcf).
The text converter preserves font, foreground colour, bold, italic and underline
but does not emit a span background. See
[`AppendSpanStart`](../../texts/markup.py). A probe changing a span background from
transparent to red produced identical pixels.

A controlled editor check selected three words and changed Background in the
text panel. The complete text box acquired the colour, rather than just the
selected words. Text colour, by contrast, can apply to selected text. Selection
therefore does not give these adjacent controls the same scope.

The observed Background behaviour matches the supported whole-area background
in [`getTextBackground`](../../texts/backgrounds.py), which comes from
`area/@backgroundcolor`. It does not demonstrate a missing span-highlighting
feature. The XML `textFormat/@backgroundColor` is another unused representation,
not the source currently used to paint the area.

**Deferred:** the tested native control does not create per-span backgrounds.
Qt's support for the HTML property and its presence in old rich text do not
justify implementing it. Pasted highlighting would require a separate scope
decision. This check also does not establish a per-span outline workflow;
effective text outlines in the converter remain area-wide.

### Vertical text margins

`text/textFormat/@VerticalIndentMargin` is explicitly ignored by
[`processAreaTextTag`](../../texts/areas.py). Observed values are `0`, `2`, `4`, `5`
and `50`. For example, [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf)
contains text with `IndentMargin="0"` and `VerticalIndentMargin="50"`.
Changing the vertical value alone from zero to 80 did not change a controlled
rendering; changing `IndentMargin` did.

A native-editor follow-up created a new text box rather than copying an old one.
With vertical centring and the visible edge distance set to 0.0 mm, both the old
and new boxes were saved with `IndentMargin="0"` and `VerticalIndentMargin="50"`.
The same album's `extra/lastTextFormat` stored a vertical value of `0`, so this
is not explained by simply copying that saved editor default. Value `50` also
occurs with top/default and bottom alignment and several different
`IndentMargin` values in the corpus. It is not specific to vertical centring.

This confirms that native creation can generate the field, but not that it is
an independently adjustable margin or causes a visible effect. Its value may be
an internal/default serialisation detail; that interpretation remains unproven.

The name suggests a separate vertical inset, but its units, activation conditions
and relationship to centred/bottom-aligned text remain empirical questions.
The existing code applies `IndentMargin` to every side and removes top/bottom
padding for vertical centring. It would be premature simply to apply the second
number as padding without an editor comparison.

**Creation path to check:** identify an editor control that changes this value
independently of `IndentMargin`. Without such a workflow, its presence alone
does not justify new vertical-padding behaviour.

### Page number outlines

`pagenumbering/outline/@width` is not read. Normal page-number font, colour,
background, positioning, number format and text substitution are read by
[`PageNumberingInfo` and `addPageNumber`](../../pageNumbering.py). Using
`TextEffectsParagraph` does not itself supply an outline: its paragraph style
is never assigned a page-number outline.

Some fixtures have width `1` even with page numbering enabled, including
[testIndex](../../tests/testIndex/test_index.mcf). However, these records contain
no outline colour, and other fixtures retain width `1` while numbering is off.
Those retained values alone do not prove that a visible outline was requested.
However, a separate native-editor check confirmed that CEWE allows both outlines
and backgrounds on page numbers. Ordinary text-area outlines already use their
separate `text/outline` record, and page-number backgrounds are already drawn
from `pagenumbering/@bgcolor`.

**Deliberately deferred:** page-number outlines will not be implemented until
a concrete need is demonstrated. This is a confirmed editor capability, not an
unexplained field or an outstanding creation-path investigation. Revisit it
when a real use case needs the outline; no new rendering work is planned now.

### Embedded calendar borders and regional holidays

The embedded `colorSchemata/calendararea/border` record is ignored by
[`_calendarCellStyles`](../../calendars/areas.py), although the scheme's default and
per-cell colours are read. The sole observed embedded border has transparent
colour `#00000000`; it does not establish a currently visible error. Installed
schema grid colours and per-cell border colours are separate supported data.

`holidays/@province` is ignored and is empty in all four calendar fixtures.
Calendar language, holiday-feature switches, week headings, week suffixes and
personal entries are already interpreted. Regional holidays are a plausible
extension, but this corpus provides no nonempty province identifier or expected
regional result. An editor example would be required before interpreting its
enum if this work is resumed.

**Deliberately deferred:** embedded custom-scheme borders and regional holiday
selection will not be implemented until a real user need is demonstrated.
Further calendar work is low priority; see the
[calendar rationale](../PROJECT_CONTEXT.md#calendars).

### Spine logo

`fotobook/@useSpineLogo` has both `0` and `1`, but is not read. Five stand-alone
fixtures contain `area[@areatype='spinelogoarea']` with a placeholder
`clipart designElementId="0"`. The area dispatcher only sends `clipartarea`
objects to the clip-art renderer, which itself skips design ID zero. There is
no special CEWE spine-logo drawing path. See
[`processElements`](../../pageElements.py) and
[`processAreaClipartTag`](../../clipart/areas.py).

**Intentional omission:** CEWE's spine branding is deliberately not implemented.
The saved switch and placeholder do not represent an outstanding feature request.
Reusing normal clip-art lookup for ID zero would not establish a missing user
artwork resource.

### Drawing order

The converter paints areas in saved XML order. All audited drawable-area
sequences agree with nondecreasing numeric `position/@zposition`, so the number
does not currently demonstrate a fixture failure. A probe changing only two
overlapping images' numeric z-values left the output unchanged; reversing their
XML order changed the visible top image.

[`processElements`](../../pageElements.py) now checks this convention after resolving
the source MCF page. It warns at the first decrease in each rendering pass,
identifying the output page, source `pagenr`, area index and adjacent known
z-values. Equal values are allowed. Missing, nonnumeric or nonfinite values are
skipped by this optional diagnostic; they do not introduce a new conversion
failure. The check does not sort areas or modify the source XML.

This warning is intended to flag a possible change in CEWE's saving convention.
If it appears, use the source album and editor to establish which ordering is
authoritative before changing the renderer. A paired source page can be checked
when rendering each physical half of a single-page PDF.
The [focused tests](../../tests/testCewePageResolver/test_areaDrawingOrder.py) cover
normal/tied values, unavailable metadata, the warning and retained XML drawing
order in both PDF styles.

### Page rotation

`page/@rotation` is also ignored, but every observed value is zero. Its exact
meaning is not established. Area `position/@rotation` is already implemented.
Background rotation is different again: the renderer reads it to warn about
unsupported nonzero rotation; every fixture stores zero.

The CEWE documentation checked describes
[rotating photos and operating on groups](https://www.cewe.de/inspiration/cewe-fotobuch-fotos-genau-platzieren-und-anpassen.html),
and separately describes
[rotating the editing view when selecting spine text](https://www.cewe.co.uk/blog/creative-tips/cewe-photobook-cover-design-tips.html).
The [Creator Software guide](https://www.cewe.co.uk/tutorials/photo-books/creator-software-guide.html)
also distinguishes the book's portrait/landscape format, selected at creation.
These descriptions do not define the MCF page-level rotation field or establish
a command for rotating an entire printed page. Remembered viewing rotation is
a possible explanation for the field, not a confirmed interpretation.

A native rotate-view action followed by a save and print-preview comparison
could establish whether the field records editor state or affects output.
Neither page-level rotation nor rotated image backgrounds are newly reproduced
rendering bugs in this corpus.

## Duplicate representations and partial handling

| Saved data not interpreted directly | Effective data currently used | Consequence |
| --- | --- | --- |
| `textFormat/@font`, `@foregroundColor` | Qt HTML body/paragraph/span font and colour | No XML-only formatting fallback; does not mean that font or colour support is absent. |
| `textFormat/@lineHeight` | HTML paragraph/list `line-height` | Changing only the XML value does nothing; the corresponding HTML setting does work. |
| Horizontal parts of `textFormat/@Alignment` | HTML paragraph `align` | XML vertical alignment is read. XML horizontal alignment alone does not change the output. |
| `textFormat/@hasOutline`, `@outlineColor`, `@outlineWidth`; span `-qt-stroke-*` | `text/outline/@color` and `@width` | Area-wide outlines work. Individual span stroke differences are not interpreted. A flag or stored default alone need not request a visible outline. |
| HTML body `letter-spacing` | `textFormat/@letterSpacing` | Area-wide letter spacing works; the HTML duplicate is ignored. Per-span spacing is not established by these fixtures. |
| `page/designElementIDs/*`; `area/designElementIDs/*` | Actual `background`, `image` and `clipart` records | Changing only a duplicate/catalogue ID does not select different artwork. |
| Calendar area's own `width` and `height` | Parent `area/position` geometry | The nested dimensions are not the bounds used for drawing. Their exact editor role remains uncertain. |
| `imagebackground/@backgroundPosition` | Area coordinates and the paired-page resolver | The label is not read, but its left/right/spread placement can already be represented in the area geometry. |

`textFormat/@hyphenation` is another unused control, but only `0` occurs.
ReportLab's existing embedded-hyphen handling is not an implementation of an
arbitrary CEWE hyphenation setting. A nonzero editor example would be needed to
establish any missing behaviour.

These distinctions prevent false positives: missing direct reads of duplicate
records do not establish missing visible features. The current converter does
interpret frame mirroring, selected clip-art replacement alpha, photo crops,
area opacity, passepartout geometry, shadows, borders, corners, TextArt and
background hue/fading. Those are not unused merely because a related editor
record is ignored.

## Editor bookkeeping and cached assessments

| Ignored family | Likely purpose and confidence | Why it is normally safe to ignore for PDF output |
| --- | --- | --- |
| `project`, `savingVersion`, `creationHistory`; root `folderID`, `externalProjectId`, `isDataMcf`, `version` | Project identity, authoring/save compatibility and provenance. Broad role is clear; precise semantics of every version/mode flag are not established. | Not page paint instructions. `externalProjectId` is empty here. |
| `statistics/*`, `userfeedback` | Usage/session counts, elapsed editing time and feedback container. High confidence for named counters. | Not visual content. `userfeedback` is empty in these fixtures. |
| `extra/lastTextFormat/*` | Last-used editor text controls. High confidence from its location. | Distinct from each area's actual text formatting; even matching attribute names are not read in this location. |
| `extra/imageQuality/@version`; `image/quality/*` | Probable cached quality assessment and assessor version. Individual numeric scales are not documented. | `noise` and `sharpness` under `quality` should not automatically be interpreted as requested noise-reduction or sharpening filters. |
| `fotoRelationships/foto/@id`, nested `@nature` | Original/copy/modified-image provenance. Observed relation names describe copy history. | The renderer opens the selected `image/@filename`. When a modified photo is already stored there, replaying its edit history could apply the effect twice. |
| `area/@association`, `@layoutContent`, `smartlayout/*` | Links, spacing and generation state used by editor layouts. High confidence in the broad role. | Saved final area positions and crops are already available; conversion does not rerun the layout assistant. |
| `page/@designStyleID`, `@designStyleTemplateName`; background `@layout`, `@templatename` | Template/style provenance and layout references. High confidence. | Layout-only background records are not the painted image background. |
| `ruler/guide/*` | Editor guide position, direction and colour. High confidence. | Guidelines are editing aids, not printed page content. |
| `CalendarEvent/UUID`, `LastChanged` | Identity and modification bookkeeping. High confidence. | Event name, date, recurrence and optional image are already used. |
| `calendararea/@optimizedSize`, embedded scheme `@deprecated` | Likely layout preset/compatibility hints. Medium confidence. | Actual area bounds, active scheme name and cell styles are used; neither flag is interpreted. |
| `text/@areaTextType` | Content/title/headline/spine role hint. Medium confidence. | Actual text, position and formatting are rendered; indexing uses configured visible formatting rather than this label. |

CEWE documents an editor quality warning based on print resolution, supporting
the assessment interpretation of the resolution-related fields. That does not
define the other quality numbers or their algorithms.
[CEWE image-quality guide](https://www.cewe.de/inspiration/in-5-schritten-bildqualitaet-pruefen.html)

`fotoRelationships` can contain effect-like references as well as filenames.
This audit does not establish that every possible CEWE editing operation is
baked into a selected bitmap, only that the stored provenance graph is not
itself replayed by the converter. Test a particular operation before classifying
its absence as harmless or as a missing effect.

## Print production settings

| Ignored field | Interpretation and confidence | Effect on the current PDF |
| --- | --- | --- |
| `image/@useABK`, `imagebackground/@useABK` | Very likely per-image automatic image correction. CEWE documents AIC as a print-process colour enhancement, but does not publish this XML switch's schema. | Stored pixels are used without emulating CEWE's lab enhancement. |
| `articleConfig/@spotColor`; `applySpotColor` on text, frames, clip art and borders | `spotColor="gold_foil"` occurs in `testClipart`. This strongly supports a relationship to special finishes; the exact per-element enablement rules remain unverified. | No separate foil/varnish production layer. Ordinary artwork colours and colour replacements are still rendered. |
| Root `art_id`, `article_name`; `articleConfig/@productvariant`, `@productvariant_visiblename` | Article/SKU and manufacturing options; observed variant is a silver spiral binding. | Product style and page geometry instead come from `productname`, page structure and `bundlesize`. Binding is not drawn as a physical mockup. |
| `addOns/addOn/@ordertxt`, `@priceClass`, `@variant` | Order options; observed variant is `flyleafcolor:white`. | Does not override the deliberate PDF endpaper policy controlled by `insideCoverWhite`. |

CEWE describes automatic image correction as applied during print processing
after upload, and describes optional highlights for selected text, clip art and
frames. These sources support the feature categories, not every internal XML
attribute's exact semantics.
[CEWE AIC and highlights FAQ](https://www.cewe.co.uk/service/faqs.html)

## Uncertain and unexercised fields

`articleConfig/@pagenaming` is ignored. Its observed values are `1`, `2` and `16`;
their association with album/calendar/card products suggests a product page-naming
convention, but an exact mapping has not been established. It is not the
`pagenumbering` record used to draw visible page numbers.

The empty `externalProjectId`, `project/@multiPurposeText` and holiday province,
zero-only page/background rotations and disabled-only XML hyphenation do not
provide positive examples of their nondefault behaviour. Likewise, a stylesheet
can mention checkbox markers or horizontal rules without those elements being
used by the saved text. These are places to seek new editor examples, not
evidence that the current fixtures display those features incorrectly.

## Selecting further work

1. Prioritise a visible mismatch produced through CEWE's normal editor controls,
   as in the passepartout-mirroring example.
2. For an inventory lead, first establish which editor action creates or changes
   it. A field's name or retained default is insufficient.
3. Investigate a specific pasted-text feature only when supporting that workflow
   is deliberately chosen. Do not use arbitrary imported HTML as a substitute
   for finding a native control.

Paragraph margins are deferred under this criterion. The audit confirms that
the renderer ignores them, but does not yet establish an in-scope feature gap.
Span highlighting is also deferred: the checked Background control affects the
whole text box, and that behaviour is already implemented. The separate
vertical-margin field still requires a user-controlled variation and a visible
mismatch, despite its presence in newly created native text boxes.

Page-number outlines have a confirmed native creation path, but are deliberately
deferred until demonstrably needed. Their background-colour counterpart is
already supported.

Embedded calendar borders and regional holidays are also deliberately deferred
until real user demand emerges. CEWE's spine logo is intentionally omitted,
rather than pending investigation or implementation.

Investigate drawing-order warnings, nonzero rotations and XML-only text
fallbacks when a real example exposes a mismatch. Physical finishing
needs an output-policy decision as well as implementation evidence. Cached
quality scores, edit history and layout bookkeeping should not become rendering
work solely because their attributes are currently unused.

## Verification and limitations

All 41 source XML documents were parsed. Every observed XML and HTML/CSS field
is classified in the accompanying inventory; empty structural containers are
listed separately. The 69 outer XML element paths and 14 embedded HTML tag
types were also checked, including tags without attributes. Literal-read
searches were followed by inspection of the
actual call paths, dictionary-style formatting reads and XPath selectors.

Fourteen small rendering probes exercised the current production functions:
nine changes to ignored fields produced identical raster pixels, while five
controls using supported settings or XML drawing order changed pixels. These
probes confirm converter behaviour; they do not establish CEWE's intended
semantics or a user-accessible creation path, and are not implementation
justification by themselves. They used scratch data and did not modify source
fixtures or approved PDFs. The drawing-order diagnostic and its focused tests
were added subsequently; it reports anomalous numeric order without changing
painting order.

| Probe change | Raster result |
| --- | --- |
| XML `VerticalIndentMargin`: 0 to 80 | Identical |
| XML `textFormat/font`: 12 to 36 point | Identical |
| XML `textFormat/foregroundColor`: black to red | Identical |
| XML `textFormat/lineHeight`: 100 to 200 | Identical |
| XML `textFormat/Alignment`: left to right, with no HTML alignment override | Identical |
| HTML span background: transparent to red | Identical |
| HTML paragraph top/bottom margins: 0 to 30 | Identical |
| HTML body letter spacing: 0 to 20px | Identical |
| Numeric z-order of two overlapping images: reversed while XML order stays fixed | Identical |
| Control: XML `IndentMargin`: 0 to 80 | Changed |
| Control: XML `letterSpacing`: 0 to 10 | Changed |
| Control: HTML paragraph line height: 100% to 200% | Changed |
| Control: HTML font size: 12 to 20 point | Changed |
| Control: XML order of the overlapping images: reversed | Changed |

This is not a schema specification, a proof of all branch coverage, or a survey
of every CEWE feature. Resource XML/SVG metadata and test-generated cases can
contain additional settings beyond this saved-MCF corpus. Even a field marked
Used can have unsupported values or interactions. The existing approved-PDF
workflow remains necessary for any subsequent implementation.
