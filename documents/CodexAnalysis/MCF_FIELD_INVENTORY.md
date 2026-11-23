# MCF field inventory

Corpus snapshot of all tracked test albums at commit `c6af821`, 23 November 2026.
Handling notes also record subsequent findings and the drawing-order diagnostic.
Read the [analysis and category definitions](MCF_DATA_AUDIT.md) before treating
an ignored field as a missing feature. This inventory covers 206 XML fields
and 62 embedded HTML/CSS fields; Used does not certify every value or interaction.

Visible candidate means a possible visual effect, not a demonstrated feature
users can create in CEWE. Native editor workflows are the primary implementation
scope; individual pasted-formatting features need an explicit scope decision.
Hand-written MCF probes do not establish either. See the
[implementation scope](MCF_DATA_AUDIT.md#implementation-scope).

`N` counts occurrences across the 41 source XML documents, including three
MCFX payloads. Example page numbers below are raw MCF `pagenr` values:
areas for an odd album page can be stored in the preceding even-page record.
Examples link to the tracked container; an MCFX link names its embedded payload.
Actual text contents, source-image filenames, UUIDs and personal paths are not reproduced.

## XML fields

### fotobook

Context: `/fotobook`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@art_id` | 41 | Ignored; Print production | Detailed article identifier or display name; productname and bundlesize drive conversion. [ceweInfo.py](../../ceweInfo.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@article_name` | 40 | Ignored; Print production | Detailed article identifier or display name; productname and bundlesize drive conversion. [ceweInfo.py](../../ceweInfo.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@externalProjectId` | 41 | Ignored; Editor bookkeeping | Project/container identity or format/version metadata; precise mode semantics unverified. [conversionSetup.py](../../conversionSetup.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@folderID` | 41 | Ignored; Editor bookkeeping | Project/container identity or format/version metadata; precise mode semantics unverified. [conversionSetup.py](../../conversionSetup.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@imagedir` | 41 | Used; Rendering | Image directory, product dispatch/fallback, or calendar start date. [albumConversionSession.py](../../albumConversionSession.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@isDataMcf` | 41 | Ignored; Editor bookkeeping | Project/container identity or format/version metadata; precise mode semantics unverified. [conversionSetup.py](../../conversionSetup.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@productname` | 41 | Used; Rendering | Image directory, product dispatch/fallback, or calendar start date. [ceweInfo.py](../../ceweInfo.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@startdatecalendarium` | 41 | Used; Rendering | Image directory, product dispatch/fallback, or calendar start date. [calendars/areas.py](../../calendars/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@useSpineLogo` | 36 | Excluded; Intentional omission | CEWE spine branding is deliberately omitted; this saved switch is not an outstanding feature request. [pageElements.py](../../pageElements.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@version` | 41 | Ignored; Editor bookkeeping | Project/container identity or format/version metadata; precise mode semantics unverified. [conversionSetup.py](../../conversionSetup.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |

### fotobook CalendarEvents CalendarEvent DateTime

Context: `/fotobook/CalendarEvents/CalendarEvent/DateTime`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `#text` | 2 | Used; Rendering | Personal-event caption, date, recurrence or thumbnail lookup. [calendars/entries.py](../../calendars/entries.py). | [sq21](../../tests/testCalendar/sq21/sq21.mcf) |

### fotobook CalendarEvents CalendarEvent Image

Context: `/fotobook/CalendarEvents/CalendarEvent/Image`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `#text` | 1 | Used; Rendering | Personal-event caption, date, recurrence or thumbnail lookup. [calendars/entries.py](../../calendars/entries.py). | [sq21](../../tests/testCalendar/sq21/sq21.mcf) |

### fotobook CalendarEvents CalendarEvent LastChanged

Context: `/fotobook/CalendarEvents/CalendarEvent/LastChanged`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `#text` | 2 | Ignored; Editor bookkeeping | Event identity or last-modified tracking. [calendars/entries.py](../../calendars/entries.py). | [sq21](../../tests/testCalendar/sq21/sq21.mcf) |

### fotobook CalendarEvents CalendarEvent Name

Context: `/fotobook/CalendarEvents/CalendarEvent/Name`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `#text` | 2 | Used; Rendering | Personal-event caption, date, recurrence or thumbnail lookup. [calendars/entries.py](../../calendars/entries.py). | [sq21](../../tests/testCalendar/sq21/sq21.mcf) |

### fotobook CalendarEvents CalendarEvent Recurrent

Context: `/fotobook/CalendarEvents/CalendarEvent/Recurrent`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `#text` | 2 | Used; Rendering | Personal-event caption, date, recurrence or thumbnail lookup. [calendars/entries.py](../../calendars/entries.py). | [sq21](../../tests/testCalendar/sq21/sq21.mcf) |

### fotobook CalendarEvents CalendarEvent UUID

Context: `/fotobook/CalendarEvents/CalendarEvent/UUID`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `#text` | 2 | Ignored; Editor bookkeeping | Event identity or last-modified tracking. [calendars/entries.py](../../calendars/entries.py). | [sq21](../../tests/testCalendar/sq21/sq21.mcf) |

### fotobook addOns addOn

Context: `/fotobook/addOns/addOn`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@ordertxt` | 15 | Ignored; Print production | Order/flyleaf option. PDF endpaper policy instead uses insideCoverWhite. [backgrounds.py](../../backgrounds.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@priceClass` | 15 | Ignored; Print production | Order/flyleaf option. PDF endpaper policy instead uses insideCoverWhite. [backgrounds.py](../../backgrounds.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@variant` | 15 | Ignored; Print production | Order/flyleaf option. PDF endpaper policy instead uses insideCoverWhite. [backgrounds.py](../../backgrounds.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |

### fotobook articleConfig

Context: `/fotobook/articleConfig`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@normalpages` | 41 | Used; Rendering | normalpages supplies album count; totalpages supplies calendar/card count. [albumConversionSession.py](../../albumConversionSession.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@pagenaming` | 41 | Uncertain; Uncertain | Observed 1, 2 and 16; likely product page-naming convention, not the visible pagenumbering record. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@productvariant` | 2 | Ignored; Print production | Special finish or binding/product variant; exact switch semantics not fully established. | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@productvariant_visiblename` | 2 | Ignored; Print production | Special finish or binding/product variant; exact switch semantics not fully established. | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@spotColor` | 1 | Ignored; Print production | Special finish or binding/product variant; exact switch semantics not fully established. | [testClipart](../../tests/testClipart/testClipart.mcf) |
| `@totalpages` | 41 | Used; Rendering | normalpages supplies album count; totalpages supplies calendar/card count. [albumConversionSession.py](../../albumConversionSession.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |

### fotobook colorSchemata calendararea

Context: `/fotobook/colorSchemata/calendararea`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@colorschema` | 2 | Used; Rendering | Embedded scheme name selected by XPath, or default/per-cell colour override. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@deprecated` | 2 | Ignored; Editor bookkeeping | Compatibility marker; only no occurs. Active scheme selected by name. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |

### fotobook colorSchemata calendararea border

Context: `/fotobook/colorSchemata/calendararea/border`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@applySpotColor` | 1 | Ignored; Print production | Entire embedded border record is ignored; only a transparent colour occurs. Extension deliberately deferred pending real user demand. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@color` | 1 | Deferred; Deferred capability | Entire embedded border record is ignored; only a transparent colour occurs. Extension deliberately deferred pending real user demand. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@enabled` | 1 | Deferred; Deferred capability | Entire embedded border record is ignored; only a transparent colour occurs. Extension deliberately deferred pending real user demand. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@gap` | 1 | Deferred; Deferred capability | Entire embedded border record is ignored; only a transparent colour occurs. Extension deliberately deferred pending real user demand. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@position` | 1 | Deferred; Deferred capability | Entire embedded border record is ignored; only a transparent colour occurs. Extension deliberately deferred pending real user demand. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@width` | 1 | Deferred; Deferred capability | Entire embedded border record is ignored; only a transparent colour occurs. Extension deliberately deferred pending real user demand. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |

### fotobook colorSchemata calendararea cell

Context: `/fotobook/colorSchemata/calendararea/cell`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@textcolor` | 6 | Used; Rendering | Embedded scheme name selected by XPath, or default/per-cell colour override. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@type` | 6 | Used; Rendering | Embedded scheme name selected by XPath, or default/per-cell colour override. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |

### fotobook colorSchemata calendararea celldefault

Context: `/fotobook/colorSchemata/calendararea/celldefault`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@bgcolor` | 2 | Used; Rendering | Embedded scheme name selected by XPath, or default/per-cell colour override. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@textcolor` | 2 | Used; Rendering | Embedded scheme name selected by XPath, or default/per-cell colour override. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |

### fotobook creationHistory

Context: `/fotobook/creationHistory`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@clientId` | 23 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@clientVersion` | 23 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@creationDate` | 23 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |

### fotobook extra imageQuality

Context: `/fotobook/extra/imageQuality`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@version` | 40 | Ignored; Editor bookkeeping | Version of probable quality-assessment cache, not a rendering algorithm selection. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |

### fotobook extra lastTextFormat

Context: `/fotobook/extra/lastTextFormat`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@Alignment` | 41 | Ignored; Editor bookkeeping | Last-used editor text controls, not the effective formatting of any rendered area. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@IndentMargin` | 41 | Ignored; Editor bookkeeping | Last-used editor text controls, not the effective formatting of any rendered area. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@VerticalIndentMargin` | 41 | Ignored; Editor bookkeeping | Last-used editor text controls, not the effective formatting of any rendered area. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@backgroundColor` | 41 | Ignored; Editor bookkeeping | Last-used editor text controls, not the effective formatting of any rendered area. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@font` | 41 | Ignored; Editor bookkeeping | Last-used editor text controls, not the effective formatting of any rendered area. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@foregroundColor` | 41 | Ignored; Editor bookkeeping | Last-used editor text controls, not the effective formatting of any rendered area. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@hasOutline` | 41 | Ignored; Editor bookkeeping | Last-used editor text controls, not the effective formatting of any rendered area. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@hyphenation` | 40 | Ignored; Editor bookkeeping | Last-used editor text controls, not the effective formatting of any rendered area. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@letterSpacing` | 40 | Ignored; Editor bookkeeping | Last-used editor text controls, not the effective formatting of any rendered area. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@lineHeight` | 40 | Ignored; Editor bookkeeping | Last-used editor text controls, not the effective formatting of any rendered area. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@outlineColor` | 1 | Ignored; Editor bookkeeping | Last-used editor text controls, not the effective formatting of any rendered area. | [testTextOutlines](../../tests/testTextOutlines/testTextOutlines.mcf) |
| `@outlineWidth` | 1 | Ignored; Editor bookkeeping | Last-used editor text controls, not the effective formatting of any rendered area. | [testTextOutlines](../../tests/testTextOutlines/testTextOutlines.mcf) |

### fotobook fotoRelationships foto

Context: `/fotobook/fotoRelationships/foto`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@id` | 55 | Ignored; Editor bookkeeping | Copy/modified-image provenance; renderer opens the selected image filename rather than replaying this history. [imageareas.py](../../imageareas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |

### fotobook fotoRelationships foto foto

Context: `/fotobook/fotoRelationships/foto/foto`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@id` | 28 | Ignored; Editor bookkeeping | Copy/modified-image provenance; renderer opens the selected image filename rather than replaying this history. [imageareas.py](../../imageareas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@nature` | 28 | Ignored; Editor bookkeeping | Copy/modified-image provenance; renderer opens the selected image filename rather than replaying this history. [imageareas.py](../../imageareas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |

### fotobook fotoRelationships foto foto foto

Context: `/fotobook/fotoRelationships/foto/foto/foto`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@id` | 2 | Ignored; Editor bookkeeping | Copy/modified-image provenance; renderer opens the selected image filename rather than replaying this history. [imageareas.py](../../imageareas.py). | [testImageOperations](../../tests/testImageOperations/test_imageOperations.mcf) |
| `@nature` | 2 | Ignored; Editor bookkeeping | Copy/modified-image provenance; renderer opens the selected image filename rather than replaying this history. [imageareas.py](../../imageareas.py). | [testImageOperations](../../tests/testImageOperations/test_imageOperations.mcf) |

### fotobook fotoRelationships foto foto foto foto

Context: `/fotobook/fotoRelationships/foto/foto/foto/foto`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@id` | 2 | Ignored; Editor bookkeeping | Copy/modified-image provenance; renderer opens the selected image filename rather than replaying this history. [imageareas.py](../../imageareas.py). | [testImageOperations](../../tests/testImageOperations/test_imageOperations.mcf) |
| `@nature` | 2 | Ignored; Editor bookkeeping | Copy/modified-image provenance; renderer opens the selected image filename rather than replaying this history. [imageareas.py](../../imageareas.py). | [testImageOperations](../../tests/testImageOperations/test_imageOperations.mcf) |

### fotobook fotoRelationships foto foto foto foto foto

Context: `/fotobook/fotoRelationships/foto/foto/foto/foto/foto`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@id` | 1 | Ignored; Editor bookkeeping | Copy/modified-image provenance; renderer opens the selected image filename rather than replaying this history. [imageareas.py](../../imageareas.py). | [testTabs](../../tests/testTabs/testTabs.mcf) |
| `@nature` | 1 | Ignored; Editor bookkeeping | Copy/modified-image provenance; renderer opens the selected image filename rather than replaying this history. [imageareas.py](../../imageareas.py). | [testTabs](../../tests/testTabs/testTabs.mcf) |

### fotobook holidays

Context: `/fotobook/holidays`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@features` | 4 | Used; Rendering | Calendar language, holiday/features, week-heading or week-number suffix. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@language` | 4 | Used; Rendering | Calendar language, holiday/features, week-heading or week-number suffix. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@province` | 4 | Deferred; Deferred capability | Likely regional holiday selector; empty and not read. Extension deliberately deferred pending real user demand. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@weekHeadline` | 4 | Used; Rendering | Calendar language, holiday/features, week-heading or week-number suffix. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |
| `@weekText` | 4 | Used; Rendering | Calendar language, holiday/features, week-heading or week-number suffix. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf) |

### fotobook page

Context: `/fotobook/page`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@designStyleID` | 1098 | Ignored; Editor bookkeeping | Style/template provenance; final positions and actual artwork are used. [pageElements.py](../../pageElements.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@designStyleTemplateName` | 179 | Ignored; Editor bookkeeping | Style/template provenance; final positions and actual artwork are used. [pageElements.py](../../pageElements.py). | [testClipartColorReplacement](../../tests/testClipartColorReplacement/test_clipart_colorreplacement.mcf), pagenr 0 |
| `@pagenr` | 1175 | Used; Rendering | Page selection, pairing and cover/product roles, including XPath selectors. [cewePageResolver.py](../../cewePageResolver.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@rotation` | 1175 | Uncertain; Uncertain | Page-level rotation field ignored; all observed values zero. CEWE documents object and editing-view rotation, but the XML field meaning is unconfirmed. [pages.py](../../pages.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@type` | 1175 | Used; Rendering | Page selection, pairing and cover/product roles, including XPath selectors. [cewePageResolver.py](../../cewePageResolver.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |

### fotobook page area

Context: `/fotobook/page/area`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@areatype` | 1255 | Partial; Rendering | Used for product/calendar recognition and clip-art dispatch; other drawing is selected by child tags. No spine-logo path. [pageElements.py](../../pageElements.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@association` | 64 | Ignored; Editor bookkeeping | Layout association or content-membership marker; does not rerun a layout. [pageElements.py](../../pageElements.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |
| `@backgroundcolor` | 35 | Used; Rendering | Text-area background, including alpha; not textFormat backgroundColor. [texts/backgrounds.py](../../texts/backgrounds.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 3 |
| `@layoutContent` | 11 | Ignored; Editor bookkeeping | Layout association or content-membership marker; does not rerun a layout. [pageElements.py](../../pageElements.py). | [testClipartColorReplacement](../../tests/testClipartColorReplacement/test_clipart_colorreplacement.mcf), pagenr 2 |

### fotobook page area calendararea

Context: `/fotobook/page/area/calendararea`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@colorschema` | 100 | Used; Rendering | Calendar schema, layout, font, size adjustments or holiday switch. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |
| `@font` | 100 | Used; Rendering | Calendar schema, layout, font, size adjustments or holiday switch. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |
| `@fontsize_percentage` | 100 | Used; Rendering | Calendar schema, layout, font, size adjustments or holiday switch. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |
| `@fontsize_percentage_holiddays` | 100 | Used; Rendering | Calendar schema, layout, font, size adjustments or holiday switch. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |
| `@height` | 100 | Duplicate; Duplicate representation | Nested dimensions ignored; parent area/position supplies drawing bounds. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |
| `@layoutschema` | 100 | Used; Rendering | Calendar schema, layout, font, size adjustments or holiday switch. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |
| `@optimizedSize` | 100 | Uncertain; Editor bookkeeping | Likely a layout optimisation/preset hint; exact meaning of 600cm2 is unverified. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |
| `@show_holiday` | 100 | Used; Rendering | Calendar schema, layout, font, size adjustments or holiday switch. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |
| `@width` | 100 | Duplicate; Duplicate representation | Nested dimensions ignored; parent area/position supplies drawing bounds. [calendars/areas.py](../../calendars/areas.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |

### fotobook page area clipart

Context: `/fotobook/page/area/clipart`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@designElementId` | 87 | Used; Rendering | Clip-art lookup; ID zero is skipped after clipartarea dispatch. [clipart/areas.py](../../clipart/areas.py). | [testClipart](../../tests/testClipart/testClipart.mcf), pagenr 0 |

### fotobook page area clipart ClipartConfiguration

Context: `/fotobook/page/area/clipart/ClipartConfiguration`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@applySpotColor` | 86 | Ignored; Print production | Likely per-element special-finish flag; ordinary RGB substitutions still apply. [clipart/catalog.py](../../clipart/catalog.py). | [testClipart](../../tests/testClipart/testClipart.mcf), pagenr 0 |

### fotobook page area clipart ClipartConfiguration colors color

Context: `/fotobook/page/area/clipart/ClipartConfiguration/colors/color`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@source` | 39 | Used; Rendering | Mirror reflection or RGB/alpha replacement colour mapping. [clipart/catalog.py](../../clipart/catalog.py). | [testClipartColorReplacement](../../tests/testClipartColorReplacement/test_clipart_colorreplacement.mcf), pagenr 2 |
| `@target` | 39 | Used; Rendering | Mirror reflection or RGB/alpha replacement colour mapping. [clipart/catalog.py](../../clipart/catalog.py). | [testClipartColorReplacement](../../tests/testClipartColorReplacement/test_clipart_colorreplacement.mcf), pagenr 2 |

### fotobook page area decoration

Context: `/fotobook/page/area/decoration`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@alpha` | 13 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [imageareas.py](../../imageareas.py). | [testGeoLinks](../../tests/testGeoLinks/testGeoLinks.mcf), pagenr 2 |

### fotobook page area decoration border

Context: `/fotobook/page/area/decoration/border`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@applySpotColor` | 195 | Ignored; Print production | Likely special-finishing switch on a border; not read. [decorations/borders.py](../../decorations/borders.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@color` | 195 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/borders.py](../../decorations/borders.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@enabled` | 195 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/borders.py](../../decorations/borders.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@gap` | 195 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/borders.py](../../decorations/borders.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@position` | 195 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/borders.py](../../decorations/borders.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@width` | 195 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/borders.py](../../decorations/borders.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |

### fotobook page area decoration corners

Context: `/fotobook/page/area/decoration/corners`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@enabled` | 33 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/corners.py](../../decorations/corners.py). | [testCorners](../../tests/testCorners/testCorners.mcf), pagenr 2 |

### fotobook page area decoration corners corner

Context: `/fotobook/page/area/decoration/corners/corner`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@length` | 132 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/corners.py](../../decorations/corners.py). | [testCorners](../../tests/testCorners/testCorners.mcf), pagenr 2 |
| `@shape` | 132 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/corners.py](../../decorations/corners.py). | [testCorners](../../tests/testCorners/testCorners.mcf), pagenr 2 |
| `@where` | 132 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/corners.py](../../decorations/corners.py). | [testCorners](../../tests/testCorners/testCorners.mcf), pagenr 2 |

### fotobook page area decoration cwtextart

Context: `/fotobook/page/area/decoration/cwtextart`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@direction` | 33 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [texts/art.py](../../texts/art.py). | [testTextArt](../../tests/testTextArt/test_textart.mcf), pagenr 2 |
| `@enabled` | 33 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [texts/art.py](../../texts/art.py). | [testTextArt](../../tests/testTextArt/test_textart.mcf), pagenr 2 |
| `@widthAngle` | 33 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [texts/art.py](../../texts/art.py). | [testTextArt](../../tests/testTextArt/test_textart.mcf), pagenr 2 |

### fotobook page area decoration shadow

Context: `/fotobook/page/area/decoration/shadow`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@shadowAngle` | 124 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/shadows.py](../../decorations/shadows.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@shadowBlurNew` | 124 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/shadows.py](../../decorations/shadows.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@shadowDistance` | 124 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/shadows.py](../../decorations/shadows.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@shadowEnabled` | 124 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/shadows.py](../../decorations/shadows.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@shadowIntensity` | 124 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/shadows.py](../../decorations/shadows.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@shadowWidthInMM` | 124 | Used; Rendering | Decoration opacity, border, enabled shadow, corner geometry or TextArt control. corner/where is selected via XPath. [decorations/shadows.py](../../decorations/shadows.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |

### fotobook page area designElementIDs

Context: `/fotobook/page/area/designElementIDs`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@clipart` | 81 | Duplicate; Duplicate representation | Catalogue/template ID copy; actual background, image or clipart child record drives lookup. [pageElements.py](../../pageElements.py). | [testClipart](../../tests/testClipart/testClipart.mcf), pagenr 0 |
| `@passepartout` | 23 | Duplicate; Duplicate representation | Catalogue/template ID copy; actual background, image or clipart child record drives lookup. [pageElements.py](../../pageElements.py). | [testClipartColorReplacement](../../tests/testClipartColorReplacement/test_clipart_colorreplacement.mcf), pagenr 0 |

### fotobook page area image

Context: `/fotobook/page/area/image`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@filename` | 184 | Used; Rendering | Selected image file or passepartout resource ID. [imageareas.py](../../imageareas.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@passepartoutDesignElementId` | 23 | Used; Rendering | Selected image file or passepartout resource ID. [imageareas.py](../../imageareas.py). | [testClipartColorReplacement](../../tests/testClipartColorReplacement/test_clipart_colorreplacement.mcf), pagenr 0 |
| `@useABK` | 184 | Ignored; Print production | Very likely automatic image correction; stored pixels are used without CEWE lab enhancement. [imageareas.py](../../imageareas.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |

### fotobook page area image ClipartConfiguration

Context: `/fotobook/page/area/image/ClipartConfiguration`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@applySpotColor` | 23 | Ignored; Print production | Likely per-element special-finish flag; ordinary RGB substitutions still apply. [clipart/catalog.py](../../clipart/catalog.py). | [testClipartColorReplacement](../../tests/testClipartColorReplacement/test_clipart_colorreplacement.mcf), pagenr 0 |
| `@mirror` | 5 | Used; Rendering | Mirror reflection or RGB/alpha replacement colour mapping. [clipart/catalog.py](../../clipart/catalog.py). | [testClipartColorReplacement](../../tests/testClipartColorReplacement/test_clipart_colorreplacement.mcf), pagenr 0 |

### fotobook page area image ClipartConfiguration colors color

Context: `/fotobook/page/area/image/ClipartConfiguration/colors/color`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@source` | 60 | Used; Rendering | Mirror reflection or RGB/alpha replacement colour mapping. [clipart/catalog.py](../../clipart/catalog.py). | [testClipartColorReplacement](../../tests/testClipartColorReplacement/test_clipart_colorreplacement.mcf), pagenr 0 |
| `@target` | 60 | Used; Rendering | Mirror reflection or RGB/alpha replacement colour mapping. [clipart/catalog.py](../../clipart/catalog.py). | [testClipartColorReplacement](../../tests/testClipartColorReplacement/test_clipart_colorreplacement.mcf), pagenr 0 |

### fotobook page area image cutout

Context: `/fotobook/page/area/image/cutout`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@left` | 184 | Used; Rendering | Source crop position and scale. [imageareas.py](../../imageareas.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@scale` | 184 | Used; Rendering | Source crop position and scale. [imageareas.py](../../imageareas.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@top` | 184 | Used; Rendering | Source crop position and scale. [imageareas.py](../../imageareas.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |

### fotobook page area image quality

Context: `/fotobook/page/area/image/quality`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@jpeg` | 163 | Ignored; Editor bookkeeping | Probable cached assessment score, not established as an editing-filter instruction. [imageareas.py](../../imageareas.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@noise` | 178 | Ignored; Editor bookkeeping | Probable cached assessment score, not established as an editing-filter instruction. [imageareas.py](../../imageareas.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@resolution` | 163 | Ignored; Editor bookkeeping | Probable cached assessment score, not established as an editing-filter instruction. [imageareas.py](../../imageareas.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@sharpness` | 178 | Ignored; Editor bookkeeping | Probable cached assessment score, not established as an editing-filter instruction. [imageareas.py](../../imageareas.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@summarized` | 163 | Ignored; Editor bookkeeping | Probable cached assessment score, not established as an editing-filter instruction. [imageareas.py](../../imageareas.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |
| `@texture` | 178 | Ignored; Editor bookkeeping | Probable cached assessment score, not established as an editing-filter instruction. [imageareas.py](../../imageareas.py). | [a4p](../../tests/testCalendar/a4p/a4p.mcf), pagenr 1 |

### fotobook page area imagebackground

Context: `/fotobook/page/area/imagebackground`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@backgroundPosition` | 9 | Duplicate; Duplicate representation | Side/spread hint is not read; positioned area and page pairing determine placement. [imageareas.py](../../imageareas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 10 |
| `@filename` | 9 | Used; Rendering | Selected image file or passepartout resource ID. [imageareas.py](../../imageareas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 10 |
| `@useABK` | 9 | Ignored; Print production | Very likely automatic image correction; stored pixels are used without CEWE lab enhancement. [imageareas.py](../../imageareas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 10 |

### fotobook page area imagebackground cutout

Context: `/fotobook/page/area/imagebackground/cutout`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@left` | 9 | Used; Rendering | Source crop position and scale. [imageareas.py](../../imageareas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 10 |
| `@scale` | 9 | Used; Rendering | Source crop position and scale. [imageareas.py](../../imageareas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 10 |
| `@top` | 9 | Used; Rendering | Source crop position and scale. [imageareas.py](../../imageareas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 10 |

### fotobook page area position

Context: `/fotobook/page/area/position`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@height` | 1255 | Used; Rendering | Area dimensions, centre/placement and rotation. [pageElements.py](../../pageElements.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@left` | 1255 | Used; Rendering | Area dimensions, centre/placement and rotation. [pageElements.py](../../pageElements.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@rotation` | 1255 | Used; Rendering | Area dimensions, centre/placement and rotation. [pageElements.py](../../pageElements.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@top` | 1255 | Used; Rendering | Area dimensions, centre/placement and rotation. [pageElements.py](../../pageElements.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@width` | 1255 | Used; Rendering | Area dimensions, centre/placement and rotation. [pageElements.py](../../pageElements.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@zposition` | 1255 | Used; Diagnostics | Warns on decreasing known numeric z-values; equal values allowed, unavailable values skipped. Painting retains XML order. [pageElements.py](../../pageElements.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |

### fotobook page area smartlayout

Context: `/fotobook/page/area/smartlayout`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@isAutoGenerated` | 53 | Ignored; Editor bookkeeping | Editor layout generation, spacing or association list; final positioned areas are rendered. [pageElements.py](../../pageElements.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |

### fotobook page area smartlayout associations association

Context: `/fotobook/page/area/smartlayout/associations/association`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `#text` | 64 | Ignored; Editor bookkeeping | Editor layout generation, spacing or association list; final positioned areas are rendered. [pageElements.py](../../pageElements.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |

### fotobook page area smartlayout spacing

Context: `/fotobook/page/area/smartlayout/spacing`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@horizontal` | 192 | Ignored; Editor bookkeeping | Editor layout generation, spacing or association list; final positioned areas are rendered. [pageElements.py](../../pageElements.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |

### fotobook page area text

Context: `/fotobook/page/area/text`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `#html` | 614 | Used; Rendering | Qt HTML content and supported formatting, detailed separately below. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@applySpotColor` | 614 | Ignored; Print production | Likely special-finish participation for text; ordinary text is drawn. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@areaTextType` | 614 | Ignored; Editor bookkeeping | Text role label; actual contents/geometry/style are rendered, indexing uses configured formatting. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |

### fotobook page area text outline

Context: `/fotobook/page/area/text/outline`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@color` | 9 | Used; Rendering | Effective area-wide text outline; positive width without visible colour does not draw an outline. [texts/outlines.py](../../texts/outlines.py). | [testTextOutlines](../../tests/testTextOutlines/testTextOutlines.mcf), pagenr 2 |
| `@width` | 614 | Used; Rendering | Effective area-wide text outline; positive width without visible colour does not draw an outline. [texts/outlines.py](../../texts/outlines.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |

### fotobook page area text textFormat

Context: `/fotobook/page/area/text/textFormat`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@Alignment` | 614 | Partial; Rendering | Only vertical alignment read here; horizontal alignment uses HTML paragraph align. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@IndentMargin` | 614 | Used; Rendering | Applied to all four frame sides if no legacy wrapper table; vertical centring removes vertical padding. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@VerticalIndentMargin` | 614 | Visible candidate; Rendering | Ignored. A new centred zero-edge-distance box saves 50 while lastTextFormat saves 0; no independently adjustable margin or visible effect established. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@backgroundColor` | 614 | Duplicate; Duplicate representation | Not read here. Font/foreground/line height use HTML; area background and text/outline have separate effective records. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@font` | 614 | Duplicate; Duplicate representation | Not read here. Font/foreground/line height use HTML; area background and text/outline have separate effective records. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@foregroundColor` | 614 | Duplicate; Duplicate representation | Not read here. Font/foreground/line height use HTML; area background and text/outline have separate effective records. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@hasOutline` | 614 | Duplicate; Duplicate representation | Not read here. Font/foreground/line height use HTML; area background and text/outline have separate effective records. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@hyphenation` | 611 | Visible candidate; Rendering | Ignored and only zero occurs; CEWE automatic hyphenation semantics not established. [texts/markup.py](../../texts/markup.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@letterSpacing` | 611 | Used; Rendering | Area-wide character spacing in MCF units. [texts/spacing.py](../../texts/spacing.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@lineHeight` | 611 | Duplicate; Duplicate representation | Not read here. Font/foreground/line height use HTML; area background and text/outline have separate effective records. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@outlineColor` | 6 | Duplicate; Duplicate representation | Not read here. Font/foreground/line height use HTML; area background and text/outline have separate effective records. [texts/areas.py](../../texts/areas.py). | [testTextOutlines](../../tests/testTextOutlines/testTextOutlines.mcf), pagenr 2 |
| `@outlineWidth` | 6 | Duplicate; Duplicate representation | Not read here. Font/foreground/line height use HTML; area background and text/outline have separate effective records. [texts/areas.py](../../texts/areas.py). | [testTextOutlines](../../tests/testTextOutlines/testTextOutlines.mcf), pagenr 2 |

### fotobook page background

Context: `/fotobook/page/background`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@alignment` | 1175 | Used; Rendering | Image resource, source-window alignment or empirical hue/fading transform. [backgrounds.py](../../backgrounds.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@designElementId` | 2242 | Used; Rendering | Image resource, source-window alignment or empirical hue/fading transform. [backgrounds.py](../../backgrounds.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@fading` | 21 | Used; Rendering | Image resource, source-window alignment or empirical hue/fading transform. [backgrounds.py](../../backgrounds.py). | [testColourBackgrounds](../../tests/testColourBackgrounds/testColourBackgrounds.mcf), pagenr 1 |
| `@hue` | 21 | Used; Rendering | Image resource, source-window alignment or empirical hue/fading transform. [backgrounds.py](../../backgrounds.py). | [testColourBackgrounds](../../tests/testColourBackgrounds/testColourBackgrounds.mcf), pagenr 1 |
| `@layout` | 1067 | Ignored; Editor bookkeeping | Layout-template record; painted background selected by presence of alignment. [backgrounds.py](../../backgrounds.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@rotation` | 1175 | Partial; Rendering | Read to warn about unsupported nonzero rotation; only zero occurs. [backgrounds.py](../../backgrounds.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@templatename` | 1067 | Ignored; Editor bookkeeping | Layout-template record; painted background selected by presence of alignment. [backgrounds.py](../../backgrounds.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@type` | 1175 | Partial; Rendering | Type 1 supported; unsupported types are diagnosed. Only type 1 occurs. [backgrounds.py](../../backgrounds.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |

### fotobook page bundlesize

Context: `/fotobook/page/bundlesize`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@height` | 1175 | Used; Rendering | Page/spread dimensions and product geometry diagnostics. [pages.py](../../pages.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@width` | 1175 | Used; Rendering | Page/spread dimensions and product geometry diagnostics. [pages.py](../../pages.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |

### fotobook page designElementIDs

Context: `/fotobook/page/designElementIDs`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@background` | 1175 | Duplicate; Duplicate representation | Catalogue/template ID copy; actual background, image or clipart child record drives lookup. [pageElements.py](../../pageElements.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@content` | 4 | Duplicate; Duplicate representation | Catalogue/template ID copy; actual background, image or clipart child record drives lookup. [pageElements.py](../../pageElements.py). | [a4l](../../tests/testCalendar/a4l/a4l.mcf), pagenr 0 |
| `@layout` | 1067 | Duplicate; Duplicate representation | Catalogue/template ID copy; actual background, image or clipart child record drives lookup. [pageElements.py](../../pageElements.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@styles_v2` | 599 | Duplicate; Duplicate representation | Catalogue/template ID copy; actual background, image or clipart child record drives lookup. [pageElements.py](../../pageElements.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |

### fotobook pagenumbering

Context: `/fotobook/pagenumbering`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@bgcolor` | 36 | Used; Rendering | Page-number format, font, colour, background, placement or label substitution; position zero disables it. [pageNumbering.py](../../pageNumbering.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@fontbold` | 36 | Used; Rendering | Page-number format, font, colour, background, placement or label substitution; position zero disables it. [pageNumbering.py](../../pageNumbering.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@fontfamily` | 36 | Used; Rendering | Page-number format, font, colour, background, placement or label substitution; position zero disables it. [pageNumbering.py](../../pageNumbering.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@fontitalics` | 36 | Used; Rendering | Page-number format, font, colour, background, placement or label substitution; position zero disables it. [pageNumbering.py](../../pageNumbering.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@fontsize` | 36 | Used; Rendering | Page-number format, font, colour, background, placement or label substitution; position zero disables it. [pageNumbering.py](../../pageNumbering.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@format` | 36 | Used; Rendering | Page-number format, font, colour, background, placement or label substitution; position zero disables it. [pageNumbering.py](../../pageNumbering.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@margin` | 36 | Used; Rendering | Page-number format, font, colour, background, placement or label substitution; position zero disables it. [pageNumbering.py](../../pageNumbering.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@position` | 36 | Used; Rendering | Page-number format, font, colour, background, placement or label substitution; position zero disables it. [pageNumbering.py](../../pageNumbering.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@textcolor` | 36 | Used; Rendering | Page-number format, font, colour, background, placement or label substitution; position zero disables it. [pageNumbering.py](../../pageNumbering.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@textstring` | 36 | Used; Rendering | Page-number format, font, colour, background, placement or label substitution; position zero disables it. [pageNumbering.py](../../pageNumbering.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@verticalMargin` | 36 | Used; Rendering | Page-number format, font, colour, background, placement or label substitution; position zero disables it. [pageNumbering.py](../../pageNumbering.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |

### fotobook pagenumbering outline

Context: `/fotobook/pagenumbering/outline`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@width` | 36 | Deferred; Deferred capability | Native page-number outlines are confirmed but deliberately not implemented until needed. Backgrounds already use pagenumbering/bgcolor. [pageNumbering.py](../../pageNumbering.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |

### fotobook project

Context: `/fotobook/project`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@createdWithHPSVersion` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@createdWithHPSVersionBuild` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@multiPurposeText` | 40 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@projectID` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@projectIDCreatedEpoch` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |

### fotobook ruler guide

Context: `/fotobook/ruler/guide`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@lineColor` | 7 | Ignored; Editor bookkeeping | Editor ruler guideline colour, direction or position; not printed content. | [testTabs](../../tests/testTabs/testTabs.mcf) |
| `@orientation` | 7 | Ignored; Editor bookkeeping | Editor ruler guideline colour, direction or position; not printed content. | [testTabs](../../tests/testTabs/testTabs.mcf) |
| `@position` | 7 | Ignored; Editor bookkeeping | Editor ruler guideline colour, direction or position; not printed content. | [testTabs](../../tests/testTabs/testTabs.mcf) |

### fotobook savingVersion

Context: `/fotobook/savingVersion`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@compatibilityVersion` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@downCastedByVersion` | 17 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@programversion` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@programversionBuild` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@savetime` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |

### fotobook statistics

Context: `/fotobook/statistics`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@assistantUsed` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@countPauses` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@elapsedTimeGross` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@elapsedTimeNet` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@fotosAdded` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@fotosRemoved` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@pauseTime` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |
| `@sessionsUsed` | 41 | Ignored; Editor bookkeeping | Project/save/client provenance, identity, time or usage counter; not page paint data. | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf) |

## Embedded HTML and CSS fields

Styles are inventoried by HTML tag and property. A parsed style dictionary
does not imply that every property is applied.

### HTML body style

Context: `HTML/body/style`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `font-family` | 614 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `font-size` | 614 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `font-style` | 614 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `font-weight` | 614 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `letter-spacing` | 589 | Duplicate; Duplicate representation | Ignored HTML equivalent; XML textFormat/letterSpacing supplies area-wide spacing. [texts/spacing.py](../../texts/spacing.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |

### HTML li style

Context: `HTML/li/style`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `-qt-block-indent` | 8 | Visible candidate; Rendering | Paragraph/list indentation or spacing ignored; nonzero top/bottom paragraph margins occur. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `background-color` | 8 | Ignored; Deferred formatting | Run/list-item background is not emitted. The checked editor Background control colours the whole text box, already supported; no per-run creation path established. [texts/markup.py](../../texts/markup.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `color` | 8 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `line-height` | 8 | Used; Rendering | Paragraph/list line spacing; does not imply paragraph margin support. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `margin-bottom` | 8 | Visible candidate; Rendering | Paragraph/list indentation or spacing ignored; nonzero top/bottom paragraph margins occur. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `margin-left` | 8 | Visible candidate; Rendering | Paragraph/list indentation or spacing ignored; nonzero top/bottom paragraph margins occur. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `margin-right` | 8 | Visible candidate; Rendering | Paragraph/list indentation or spacing ignored; nonzero top/bottom paragraph margins occur. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `margin-top` | 8 | Visible candidate; Rendering | Paragraph/list indentation or spacing ignored; nonzero top/bottom paragraph margins occur. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `text-indent` | 8 | Visible candidate; Rendering | Paragraph/list indentation or spacing ignored; nonzero top/bottom paragraph margins occur. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |

### HTML meta

Context: `HTML/meta`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@charset` | 521 | Ignored; Editor bookkeeping | Qt HTML metadata or stylesheet boilerplate; no CSS cascade engine is applied. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@content` | 614 | Ignored; Editor bookkeeping | Qt HTML metadata or stylesheet boilerplate; no CSS cascade engine is applied. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@name` | 614 | Ignored; Editor bookkeeping | Qt HTML metadata or stylesheet boilerplate; no CSS cascade engine is applied. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |

### HTML ol style

Context: `HTML/ol/style`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `-qt-list-indent` | 1 | Visible candidate; Rendering | List margins and Qt list indent ignored; current marker indent derives from font size. Margins only zero. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `margin-bottom` | 1 | Visible candidate; Rendering | List margins and Qt list indent ignored; current marker indent derives from font size. Margins only zero. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `margin-left` | 1 | Visible candidate; Rendering | List margins and Qt list indent ignored; current marker indent derives from font size. Margins only zero. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `margin-right` | 1 | Visible candidate; Rendering | List margins and Qt list indent ignored; current marker indent derives from font size. Margins only zero. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `margin-top` | 1 | Visible candidate; Rendering | List margins and Qt list indent ignored; current marker indent derives from font size. Margins only zero. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |

### HTML p

Context: `HTML/p`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `@align` | 162 | Used; Rendering | Paragraph horizontal alignment. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |

### HTML p style

Context: `HTML/p/style`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `-qt-block-indent` | 715 | Visible candidate; Rendering | Paragraph/list indentation or spacing ignored; nonzero top/bottom paragraph margins occur. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `-qt-paragraph-type` | 35 | Ignored; Editor bookkeeping | Empty-paragraph marker; actual paragraph/text nodes are processed. [texts/areas.py](../../texts/areas.py). | [testClipart](../../tests/testClipart/testClipart.mcf), pagenr 0 |
| `-qt-stroke-color` | 5 | Duplicate; Duplicate representation | Per-span/paragraph stroke settings are not applied; effective area outline comes from text/outline. Cap/join values constant. [texts/outlines.py](../../texts/outlines.py). | [testDecorations](../../tests/testDecorations/test_decorations.mcf), pagenr 4 |
| `-qt-stroke-linecap` | 5 | Duplicate; Duplicate representation | Per-span/paragraph stroke settings are not applied; effective area outline comes from text/outline. Cap/join values constant. [texts/outlines.py](../../texts/outlines.py). | [testDecorations](../../tests/testDecorations/test_decorations.mcf), pagenr 4 |
| `-qt-stroke-linejoin` | 5 | Duplicate; Duplicate representation | Per-span/paragraph stroke settings are not applied; effective area outline comes from text/outline. Cap/join values constant. [texts/outlines.py](../../texts/outlines.py). | [testDecorations](../../tests/testDecorations/test_decorations.mcf), pagenr 4 |
| `-qt-stroke-width` | 5 | Duplicate; Duplicate representation | Per-span/paragraph stroke settings are not applied; effective area outline comes from text/outline. Cap/join values constant. [texts/outlines.py](../../texts/outlines.py). | [testDecorations](../../tests/testDecorations/test_decorations.mcf), pagenr 4 |
| `color` | 6 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testDecorations](../../tests/testDecorations/test_decorations.mcf), pagenr 4 |
| `font-family` | 3 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testEmptyPageOne](../../tests/testEmptyPageOne/test_emptyPageOne.mcf), pagenr 2 |
| `font-size` | 3 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `line-height` | 467 | Used; Rendering | Paragraph/list line spacing; does not imply paragraph margin support. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `margin-bottom` | 715 | Visible candidate; Rendering | Paragraph/list indentation or spacing ignored; nonzero top/bottom paragraph margins occur. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `margin-left` | 715 | Visible candidate; Rendering | Paragraph/list indentation or spacing ignored; nonzero top/bottom paragraph margins occur. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `margin-right` | 715 | Visible candidate; Rendering | Paragraph/list indentation or spacing ignored; nonzero top/bottom paragraph margins occur. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `margin-top` | 715 | Visible candidate; Rendering | Paragraph/list indentation or spacing ignored; nonzero top/bottom paragraph margins occur. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `text-indent` | 715 | Visible candidate; Rendering | Paragraph/list indentation or spacing ignored; nonzero top/bottom paragraph margins occur. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |

### HTML span style

Context: `HTML/span/style`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `-qt-stroke-color` | 709 | Duplicate; Duplicate representation | Per-span/paragraph stroke settings are not applied; effective area outline comes from text/outline. Cap/join values constant. [texts/outlines.py](../../texts/outlines.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `-qt-stroke-linecap` | 709 | Duplicate; Duplicate representation | Per-span/paragraph stroke settings are not applied; effective area outline comes from text/outline. Cap/join values constant. [texts/outlines.py](../../texts/outlines.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `-qt-stroke-linejoin` | 709 | Duplicate; Duplicate representation | Per-span/paragraph stroke settings are not applied; effective area outline comes from text/outline. Cap/join values constant. [texts/outlines.py](../../texts/outlines.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `-qt-stroke-width` | 709 | Duplicate; Duplicate representation | Per-span/paragraph stroke settings are not applied; effective area outline comes from text/outline. Cap/join values constant. [texts/outlines.py](../../texts/outlines.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `background-color` | 29 | Ignored; Deferred formatting | Run/list-item background is not emitted. The checked editor Background control colours the whole text box, already supported; no per-run creation path established. [texts/markup.py](../../texts/markup.py). | [testFontSubstitution](../../tests/testFontSubstitution/testfontsubstitution.mcf), pagenr 2 |
| `color` | 943 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `font-family` | 168 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testEmptyPageOne](../../tests/testEmptyPageOne/test_emptyPageOne.mcf), pagenr 0 |
| `font-size` | 153 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testFontSubstitution](../../tests/testFontSubstitution/testfontsubstitution.mcf), pagenr 2 |
| `font-style` | 120 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testEmptyPageOne](../../tests/testEmptyPageOne/test_emptyPageOne.mcf), pagenr 0 |
| `font-weight` | 235 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `text-decoration` | 15 | Used; Rendering | Effective HTML font/foreground properties, including inherited values and underline. [texts/markup.py](../../texts/markup.py). | [testTabs](../../tests/testTabs/testTabs.mcf), pagenr 2 |

### HTML style

Context: `HTML/style`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `#stylesheet` | 614 | Ignored; Editor bookkeeping | Qt HTML metadata or stylesheet boilerplate; no CSS cascade engine is applied. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |
| `@type` | 614 | Ignored; Editor bookkeeping | Qt HTML metadata or stylesheet boilerplate; no CSS cascade engine is applied. [texts/areas.py](../../texts/areas.py). | [testBackgroundAlignment](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf), pagenr 0 |

### HTML table style

Context: `HTML/table/style`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `-qt-table-type` | 89 | Ignored; Editor bookkeeping | Qt root-table marker; wrapper table presence is recognised without reading this attribute. [texts/areas.py](../../texts/areas.py). | [testClipart](../../tests/testClipart/testClipart.mcf), pagenr 0 |
| `margin-bottom` | 89 | Used; Rendering | Legacy text-box wrapper margin, distinct from paragraph or list margins. [texts/areas.py](../../texts/areas.py). | [testClipart](../../tests/testClipart/testClipart.mcf), pagenr 0 |
| `margin-left` | 89 | Used; Rendering | Legacy text-box wrapper margin, distinct from paragraph or list margins. [texts/areas.py](../../texts/areas.py). | [testClipart](../../tests/testClipart/testClipart.mcf), pagenr 0 |
| `margin-right` | 89 | Used; Rendering | Legacy text-box wrapper margin, distinct from paragraph or list margins. [texts/areas.py](../../texts/areas.py). | [testClipart](../../tests/testClipart/testClipart.mcf), pagenr 0 |
| `margin-top` | 89 | Used; Rendering | Legacy text-box wrapper margin, distinct from paragraph or list margins. [texts/areas.py](../../texts/areas.py). | [testClipart](../../tests/testClipart/testClipart.mcf), pagenr 0 |

### HTML td style

Context: `HTML/td/style`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `border` | 89 | Visible candidate; Rendering | Cell border not interpreted; only none occurs in wrapper cells. [texts/areas.py](../../texts/areas.py). | [testClipart](../../tests/testClipart/testClipart.mcf), pagenr 0 |

### HTML ul style

Context: `HTML/ul/style`.

| Field | N | Handling and category | Interpretation and code evidence | Example |
| --- | ---: | --- | --- | --- |
| `-qt-list-indent` | 1 | Visible candidate; Rendering | List margins and Qt list indent ignored; current marker indent derives from font size. Margins only zero. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `margin-bottom` | 1 | Visible candidate; Rendering | List margins and Qt list indent ignored; current marker indent derives from font size. Margins only zero. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `margin-left` | 1 | Visible candidate; Rendering | List margins and Qt list indent ignored; current marker indent derives from font size. Margins only zero. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `margin-right` | 1 | Visible candidate; Rendering | List margins and Qt list indent ignored; current marker indent derives from font size. Margins only zero. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |
| `margin-top` | 1 | Visible candidate; Rendering | List margins and Qt list indent ignored; current marker indent derives from font size. Margins only zero. [texts/lists.py](../../texts/lists.py). | [testLists](../../tests/testLists/testlists.mcf), pagenr 0 |

## Embedded HTML elements

These 14 tag types were also inspected, including tags without attributes.
They are structural observations, not additional attribute/CSS field rows.

| HTML tag | N | Handling |
| --- | ---: | --- |
| `body` | 614 | Used text container and inherited font/style defaults. |
| `br` | 75 | Used line breaks. |
| `head` | 614 | Metadata container; not drawn. |
| `html` | 614 | Parsed rich-text envelope. |
| `li` | 8 | Used flat list item; selected formatting only. |
| `meta` | 1135 | Ignored Qt/encoding metadata. |
| `ol` | 1 | Used flat ordered list; selected formatting only. |
| `p` | 715 | Used paragraph content, alignment and selected styles. |
| `span` | 1004 | Used text runs and selected inherited styles; backgrounds/strokes classified above. |
| `style` | 614 | Ignored stylesheet boilerplate; no CSS cascade engine. |
| `table` | 89 | Legacy root wrapper: margins read, descendant paragraphs rendered; not a general table layout engine. |
| `td` | 89 | Root-wrapper cell; descendant paragraphs reached, cell border not interpreted. |
| `tr` | 89 | Root-wrapper row; descendant paragraphs reached, row layout not interpreted independently. |
| `ul` | 1 | Used flat unordered list; selected formatting only. |

## Structural containers

Containers with no attributes or direct text are not additional field rows.
Their child records can still be used:

| Element path | N | Role |
| --- | ---: | --- |
| `/fotobook/CalendarEvents` | 4 | Used personal-event collection. |
| `/fotobook/CalendarEvents/CalendarEvent` | 2 | Used event record; individual child text fields classified above. |
| `/fotobook/addOns` | 40 | Ignored order-option collection. |
| `/fotobook/colorSchemata` | 2 | Used embedded calendar schemes. |
| `/fotobook/extra` | 41 | Ignored editor defaults and assessment metadata. |
| `/fotobook/fotoRelationships` | 41 | Ignored copy/edit provenance graph. |
| `/fotobook/page/area/clipart/ClipartConfiguration/colors` | 34 | Used replacement-colour collection. |
| `/fotobook/page/area/image/ClipartConfiguration/colors` | 6 | Used passepartout replacement-colour collection. |
| `/fotobook/page/area/smartlayout/associations` | 53 | Ignored editor-layout association collection. |
| `/fotobook/ruler` | 32 | Ignored editor guideline collection; often empty. |
| `/fotobook/userfeedback` | 41 | Ignored; empty in the audited fixtures. |

## Source containers

All tracked `.mcf` and `.mcfx` files under `tests/` are included. No sample
of fixture directories or selection of feature albums was substituted.

- [tests/testBackgroundAlignment/testBackgroundAlignment.mcf](../../tests/testBackgroundAlignment/testBackgroundAlignment.mcf)
- [tests/testCalendar/a4l/a4l.mcf](../../tests/testCalendar/a4l/a4l.mcf)
- [tests/testCalendar/a4p/a4p.mcf](../../tests/testCalendar/a4p/a4p.mcf)
- [tests/testCalendar/a5l/a5l.mcf](../../tests/testCalendar/a5l/a5l.mcf)
- [tests/testCalendar/sq21/sq21.mcf](../../tests/testCalendar/sq21/sq21.mcf)
- [tests/testClipart/testClipart.mcf](../../tests/testClipart/testClipart.mcf)
- [tests/testClipartColorReplacement/test_clipart_colorreplacement.mcf](../../tests/testClipartColorReplacement/test_clipart_colorreplacement.mcf)
- [tests/testColourBackgrounds/testColourBackgrounds.mcf](../../tests/testColourBackgrounds/testColourBackgrounds.mcf)
- [tests/testCorners/testCorners.mcf](../../tests/testCorners/testCorners.mcf)
- [tests/testDecorations/test_decorations.mcf](../../tests/testDecorations/test_decorations.mcf)
- [tests/testEmptyPageOne/test_emptyPageOne.mcf](../../tests/testEmptyPageOne/test_emptyPageOne.mcf)
- [tests/testFontSubstitution/testfontsubstitution.mcf](../../tests/testFontSubstitution/testfontsubstitution.mcf)
- [tests/testGeoLinks/testGeoLinks.mcf](../../tests/testGeoLinks/testGeoLinks.mcf)
- [tests/testImageExtractor/test_imageExtractor.mcfx (embedded data.mcf)](../../tests/testImageExtractor/test_imageExtractor.mcfx)
- [tests/testImageOperations/test_imageOperations.mcf](../../tests/testImageOperations/test_imageOperations.mcf)
- [tests/testImages/testImages.mcf](../../tests/testImages/testImages.mcf)
- [tests/testIndex/test_index.mcf](../../tests/testIndex/test_index.mcf)
- [tests/testIndexLarge/test_indexLarge.mcf](../../tests/testIndexLarge/test_indexLarge.mcf)
- [tests/testIndexMultipage/test_indexMultipage.mcf](../../tests/testIndexMultipage/test_indexMultipage.mcf)
- [tests/testIndexOnlyBookmarks/testIndexOnlyBookmarks.mcf](../../tests/testIndexOnlyBookmarks/testIndexOnlyBookmarks.mcf)
- [tests/testLetterSpacing/testLetterSpacing.mcf](../../tests/testLetterSpacing/testLetterSpacing.mcf)
- [tests/testLineHeight/testLineHeight.mcf](../../tests/testLineHeight/testLineHeight.mcf)
- [tests/testLists/testlists.mcf](../../tests/testLists/testlists.mcf)
- [tests/testMcfxExtraction/McfOriginals/testMcfxExtraction.mcf](../../tests/testMcfxExtraction/McfOriginals/testMcfxExtraction.mcf)
- [tests/testMcfxExtraction/testMcfxExtraction.mcfx (embedded data.mcf)](../../tests/testMcfxExtraction/testMcfxExtraction.mcfx)
- [tests/testMemoryCards/testMemoryCards.mcf](../../tests/testMemoryCards/testMemoryCards.mcf)
- [tests/testNoCewe/testNoCewe.mcf](../../tests/testNoCewe/testNoCewe.mcf)
- [tests/testPageNumbers/test_pagenumbers.mcf](../../tests/testPageNumbers/test_pagenumbers.mcf)
- [tests/testShadows/test_shadows.mcf](../../tests/testShadows/test_shadows.mcf)
- [tests/testTabs/testTabs.mcf](../../tests/testTabs/testTabs.mcf)
- [tests/testTextArt/test_textart.mcf](../../tests/testTextArt/test_textart.mcf)
- [tests/testTextBox/testTextBox.mcf](../../tests/testTextBox/testTextBox.mcf)
- [tests/testTextLinks/testTextLinks.mcf](../../tests/testTextLinks/testTextLinks.mcf)
- [tests/testTextOutlines/testTextOutlines.mcf](../../tests/testTextOutlines/testTextOutlines.mcf)
- [tests/testTextShrinkVAlign/testTextShrinkVAlign.mcf](../../tests/testTextShrinkVAlign/testTextShrinkVAlign.mcf)
- [tests/testTextWrapVAlignBorder/test_textwrapvalignborder.mcf](../../tests/testTextWrapVAlignBorder/test_textwrapvalignborder.mcf)
- [tests/testTransparency/testTransparency.mcf](../../tests/testTransparency/testTransparency.mcf)
- [tests/testUnsupportedChars/testUnsupportedChars.mcf](../../tests/testUnsupportedChars/testUnsupportedChars.mcf)
- [tests/testbackgrounds/allblackbackgrounds.mcf](../../tests/testbackgrounds/allblackbackgrounds.mcf)
- [tests/unittest_fotobook/unittest_fotobook.mcf](../../tests/unittest_fotobook/unittest_fotobook.mcf)
- [tests/unittest_fotobook/unittest_fotobook.mcfx (embedded data.mcf)](../../tests/unittest_fotobook/unittest_fotobook.mcfx)
