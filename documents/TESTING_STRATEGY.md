# Testing strategy and overview

cewe2pdf uses both approved PDF pixel comparisons and coded focused tests of behaviour
that pixel changes cannot reliably reveal. The additional tests provide useful protection
against regressions, although some are redundant or tied too closely to the current
implementation. The aim should be to improve the evidence supplied by the suite,
not to maximise its test count.

This document explains the strategy and records an assessment of the existing
coverage. The [test workflow](../tests/README.md) remains the authority for running tests,
fixture conventions, approving PDFs, and cleaning generated output.

## What each kind of test protects

| Test approach | Main purpose | Important limitation |
| --- | --- | --- |
| Approved PDF pixel comparison | Detect changes to rendered pages, including interactions between features | Agreement with an approved result does not establish that the result matches CEWE, only that the code generates the same visual result as it generated the last time the result pdf was approved; invisible PDF behaviour can change without changing pixels |
| PDF structure and interaction checks | Verify links, destinations, bookmarks, page labels, and other nonvisual output | A correct target alone does not establish that a clickable area is in the right place |
| Focused rendering checks | Check a particular effect, geometry, transparency, or graphics-state property using a small rendered example | A synthetic example covers fewer interactions than a complete album |
| Behavioural tests of parsing, resources, and conversion logic | Protect product rules, configuration choices, font fallback, extraction, and failure handling | Mocked dependencies and isolated helpers do not establish that the complete conversion works |
| Platform and executable checks | Exercise operating-system integration and packaged execution | A simulated Windows API or a successful executable smoke test covers only part of the platform behaviour |

These categories overlap. A test without an approved PDF comparison may still
render a real PDF, inspect pixels, load real resources, or extract an actual database.

## Assessment of the existing suite

A static review on 21 October 2026 counted 163 test functions representing
265 cases after parameterisation. Of these, 34 cases were identified as entering
the approved PDF comparison helpers; the other 231 included structural PDF checks,
small rendering tests, and tests of conversion logic. These are a dated inventory,
not a target or a permanent division of the suite.

Parameterisation accounts for a significant number of test cases. For example, the TextArt
spacing module contained ten test functions representing 75 cases. Multiple inputs
can cheaply exercise a useful boundary or mathematical property. The number of cases
alone says little about maintenance cost or the independence of their evidence.

### Particularly useful protection

- [Index tests](../tests/testIndex/test_index.py) inspect actual PDF navigation and page
  labels alongside the approved rendering. Pixel comparison cannot detect a link
  pointing to the wrong page.
- [Font family resolution tests](../tests/testFontSubstitution/test_fontFamilyResolution.py)
  use a supplied font to verify fallback within a family and reject stale registry
  mappings. This protects a real failure mode without requiring a private installed font.
- [Letter spacing layout tests](../tests/testLetterSpacing/test_spacingLayout.py) check
  wrapping, negative spacing, styled fragments, explicit breaks, and difficult words.
  These give a more precise diagnosis than a changed album page alone.
- [Calendar tests](../tests/testCalendar/test_calendar.py) protect resource interpretation,
  locale choices, dates, and product rules as well as rendered output.
- [MCFX extraction tests](../tests/testMcfxExtraction/test_McfxExtraction.py) exercise archive
  and database handling, including regression cases that can prevent conversion
  before there is any PDF to compare.
- [TextArt shadow tests](../tests/testTextArt/test_textartShadow.py) include actual rendering
  and failure handling. Transparency, mask bounds, and preservation of foreground
  text are useful observable properties.

Such tests can help a new contributor understand an intended rule and locate a
regression quickly. Their value is strongest when the expectation comes from a
known bug, a documented product rule, an independently derived property, or a
controlled CEWE comparison.

### Where the tests are over-specified or redundant

Some tests constrain the implementation more than the user-visible contract.
Exact diagnostic wording is usually less important than reporting the right
problem with enough context. Exact sequences of mocked helper calls can also make
a harmless refactor fail, even when the resulting PDF remains correct. Assertions
about a warning's presence or a necessary ordering relationship are often sufficient.

Some TextArt geometry tests verify agreement between production helpers or preserve
historical formulae. These can protect an established invariant, but they do not
independently prove the CEWE interpretation. If two helpers share the same mistaken
assumption, their agreement can still pass. Independently derived geometric
properties remain valuable; representative cases should be chosen for distinct
behaviour rather than an arbitrary target count.

The [system font discovery tests](../tests/testFontDoesNotExist/test_fontDoesNotExist.py)
also depend partly on fonts installed on the host. Controlled directories and
supplied fonts would make ordinary regression checks more reproducible. Discovery
against the real operating system is useful as an explicitly identified integration
check.

## Improvements worth prioritising

These are recommendations from the review, not claims that the coverage already
exists or instructions to expand the suite indiscriminately.

1. **Protect the PDF comparator itself.** The
   [tolerance tests](../tests/testComparePdf/test_comparePdf.py) exercise acceptance at the
   configured limits, but the rejection example independently exceeds only the
   per-channel limit. Add separate failures for pixel count and combined RGB
   difference. A fault in the comparison tool can weaken many rendering tests.
2. **Check link placement as well as targets.** The
   [text link tests](../tests/testTextLinks/test_links.py) check annotation count and URI.
   Add a meaningful check that the clickable rectangle covers the intended text,
   including a wrapped URL. A misplaced annotation can pass both the current
   structural assertions and pixel comparison.
3. **Exercise conversion ownership through complete conversions.** A small number
   of tests should run consecutive conversions with different configurations and
   check that state does not leak between them. Failure-path checks should establish
   that resources are released and a later conversion can succeed. Isolated setup
   tests do not establish these end-to-end properties.
4. **Verify important settings in the produced PDF.** For example, checking title
   and author in a setup object is weaker than also reading them from a converted
   PDF. Prefer a few representative checks over duplicating every configuration
   assignment in a test.

Simplifying redundant assertions while adding these checks would improve confidence
more than retaining every existing test and adding a large new collection.

## Choosing tests for future changes

Before adding a test, identify the fault it should catch and the evidence behind
the expected result. A useful test should fail if that fault is introduced and
remain valid when the implementation is refactored without changing behaviour.

- For visible rendering changes, use a controlled MCF example and an approved PDF
  comparison. Confirm the intended result against CEWE or other independent evidence
  before approval.
- For invisible PDF behaviour, inspect the actual PDF objects and relevant geometry.
- For parsing and product rules, use small realistic inputs with explicit expected
  outcomes, including meaningful boundary or failure cases.
- For a repaired bug, retain the smallest practical reproduction. Use a complete
  conversion when the bug depends on interactions or conversion state.
- Use mocks to isolate unrelated effects or inject failures. Keep the behaviour
  being tested real wherever practical.
- Assert exact messages or internal call sequences only when that precision is
  itself a requirement, and explain why.
- Keep portable regressions independent of private resources and host fonts.
  Identify checks that intentionally require an installed application or platform.

Existing tests should be judged by the same criteria. Remove duplication and relax
incidental constraints when they obstruct legitimate changes. Preserve distinct
regressions and useful boundary cases even when they occupy only a few lines.

## What a passing suite means

A passing suite is evidence that the behaviours still work in the tested environment -
that nothing has been inadvertently broken by a change. It is of course not proof of
complete CEWE compatibility, complete platform coverage, or correct behaviour for every
album.

Approved visual comparisons remain the main safeguard for rendering fidelity. There is 
no substitute for a human checking the result pdf against the presentation in the
CEWE album editor. 

When we improve the implementation in some way, we should expect that some of the existing
approved PDFs may have to be replaced with new ones. A comparison failure always indicates
the "size" of the pixel difference, helping in the assessment of whether the change is
what we expected. The comparison tool can also be used post "failure" to visualise the
differences between two pdfs in a way which most pdf comparison tools cannot. There is one
known case of an "expected" pixel level difference between pdfs generated from the same
input on different platforms, caused by rendering software differences; the comparator can
be configured to "accept" this difference, but it is still important to understand the
reason for the difference and to ensure that it is not a regression.

Focused behavioural and structural tests complement the pixel comparison tests by catching
invisible faults, exercising failures, and making regressions easier to diagnose. Keeping
both, with selective simplification and a few stronger integration checks, is a sounder
strategy than relying exclusively on either approach.
