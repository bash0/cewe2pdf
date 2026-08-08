# MCF feature classification

This is a conservative code-reading pass over the 22 audited album documents.
“Implemented” means the current parser has an identifiable handler; it does not
claim pixel-perfect equivalence with the Album Editor.  “Needs review” is used
where an XML attribute occurs but has no direct parser reference.

## Visual area types

| MCF feature | Found | Status | Evidence / note |
| --- | ---: | --- | --- |
| `imagearea` / `image` | 126 | Implemented | `cewe2pdf.py` dispatches every `image` element in an area to `processAreaImageTag`. |
| `imagebackgroundarea` / `imagebackground` | 2 | Implemented | The same dispatch explicitly processes `imagebackground` elements. |
| `textarea` / `text` | 366 | Implemented | Every `text` element is passed to `processAreaTextTag`. |
| `spinetextarea` / `text` | 21 | Implemented | It has a normal `text` child, which uses the same text dispatch as a text area. |
| `clipartarea` / `clipart` | 46 | Implemented | `clipartarea` is explicitly dispatched to `processAreaClipartTag`. |
| `spinelogoarea` / `clipart` | 3 | Intentionally ignored | It contains `clipart`, but the clipart dispatch is conditional on `areatype == 'clipartarea'`. Project policy is to omit commercial spine branding from generated PDFs. |
| `smartlayoutarea` / `smartlayout` | 26 | Structural/editor metadata | These areas have no image, text, or clipart child. The renderer does not act on `smartlayout`; that is probably correct because it describes the editor's layout assistance rather than a page object. |

## Decorations

| MCF feature | Found | Status | Evidence / note |
| --- | ---: | --- | --- |
| `border` | 116 | Implemented | `processDecorationBorders` handles the five observed positions: centered, inside, insideWithGap, outside, outsideWithGap. |
| `shadow` | 73 | Implemented | `shadows.py` is used for both conventional and corner-aware shadows. |
| `corners` with `default`, `convex`, `bevelled` | 3 / 118 / 5 corners | Implemented | `corners.py` applies convex and bevelled masks/paths; default leaves a square corner. |
| `corners` with `notched` | 1 corner | Warned and ignored | `CornerShape.Notched` is known, but the mask logs that it is not implemented. This is deliberate. |
| `corners` with `concave` | 1 corner | Warned and ignored | `concave` is not in `CornerShape`, so it becomes `Unknown` and is warned about. It occurs in `tests/testCorners/testCorners.mcf`. |
| `cwtextart` | 22 | Implemented | Text areas dispatch this to `processTextArt` / `textart.handleTextArt`. |
| `decoration/@alpha` | 4 | Needs review | The attribute occurs on a decoration rather than a specific decoration child. It needs an example-based visual check before deciding whether it affects rendering. |

## Text and clipart attributes

| MCF feature | Found | Status | Evidence / note |
| --- | ---: | --- | --- |
| `textFormat/@Alignment` | 387 | Implemented | Used for vertical alignment in `processAreaTextTag`. |
| `textFormat/@IndentMargin` | 387 | Implemented | Used when no legacy margin table provides the setting. |
| `textFormat/@VerticalIndentMargin` | 387 | Explicitly ignored | The code comments that its effect is not yet understood and does not use it. |
| `textFormat/@hyphenation` | 381 | Needs review | Found in the MCF corpus, but no direct parser reference was found. |
| `textFormat/@letterSpacing` | 381 | Needs review | Found in the MCF corpus, but no direct parser reference was found. |
| `textFormat/@lineHeight` | 381 | Needs review | Found in the MCF corpus, but no direct parser reference was found. |
| `outline` | 409 | Implemented | Text-outline handling is present; seven outlines use width 1, the remainder are width 0. |
| `ClipartConfiguration/@mirror` | 4 | Implemented | `clipArt.py` reads x, y, and both mirror values. |
| `ClipartConfiguration/colors/color` | 60 image and 17 clipart entries | Implemented | `clipArt.py` handles the configuration and colour-replacement information. |
| `pagenumbering` | 22 | Implemented | The book-level element is passed to `pageNumbering.py`. |

## Non-rendering metadata

The audit also found book/article/project/version/history/statistics data,
`designElementIDs`, `bundlesize`, and editor quality settings.  These are not
automatically omissions: they identify the product or assist the editor rather
than necessarily describing visible PDF content.  They should be considered
only when a concrete visual discrepancy points to one of them.

## Recommended next investigation

`lineHeight` is the best remaining candidate for a new feature. Create a small
test book that varies only this attribute, and compare the CEWE rendering with
the PDF before choosing its conversion to ReportLab leading. Hyphenation and
letter spacing are lower-value and can remain out of scope unless a real album
reveals a visible discrepancy.
