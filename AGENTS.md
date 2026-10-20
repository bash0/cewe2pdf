# cewe2pdf programming guidance

This file gives coding assistants the project's working conventions. Read it before editing. The [README documentation map](README.md#documentation) is the entry point to the other guides.
[PROJECT_CONTEXT.md](documents/PROJECT_CONTEXT.md) explains important implementation decisions.
[DEVELOPER_GUIDE.md](documents/DEVELOPER_GUIDE.md) describes the architecture and test workflow;
[README.md](README.md) documents installation, configuration, supported features, and cleanup.

## Workspace and review

- Work in the checkout or task worktree authorized by the programmer. Establish the intended workspace before editing or cleaning files.
- Follow the programmer's review and version-control workflow. Do not stage, commit, push, merge, or publish without authorization.
- When working in an isolated worktree, keep changes and generated output there. Do not synchronize another checkout automatically.
- Report the resulting behaviour, verification performed, and any unresolved failures or limitations.
- Keep personal paths, account details, conversation transcripts, and machine-specific setup out of shared guidance.

## Platforms and file integrity

- Support normal Python execution on Windows, Linux, and macOS. Windows Explorer integration is a separate, platform-specific feature.
- Use Python 3.12 and an isolated environment installed from requirements-pinned.txt. Verify the selected interpreter rather than assuming a particular environment name or installation path.
- Respect repository attributes and a programmer's explicit checkout conventions. Otherwise preserve each text file's existing line endings; avoid unrelated LF/CRLF changes.
- CRLF may be a local Windows preference; it is not a requirement for Linux/macOS contributors. Keep shell scripts compatible with their target platform.
- Preserve PDFs, images, fonts, databases, and other binary resources byte-for-byte unless intentionally changing them. Never apply text newline conversion to them.
- Use platform-aware paths and resource discovery. Do not hard-code a contributor's home directory, CEWE installation, font folders, or temporary directory.
- Keep Windows-only imports and operations guarded. Tests for Windows path handling must also work on Linux CI.
- Close files and database connections before reopening, replacing, or cleaning them; Windows locking can expose mistakes hidden on other platforms.

## Coding conventions

- Prefer f-strings, including log messages, and follow the existing naming style.
- Prefer explicit conditions and product dispatch over clever shorthand. Avoid chained comparisons where separate conditions are clearer.
- Use one indentation level for continuation lines rather than aligning them beneath an earlier expression.
- Use descriptive domain names; retain familiar module names when moving code.
- Explain undocumented CEWE conventions, empirical calibration, ownership, and non-obvious Python mechanisms in focused comments.
- Use the existing flake8 and pylint configuration. Fix meaningful findings; use narrow, explained suppressions for deliberate boundaries rather than restructuring solely to satisfy a metric.
- Avoid unrelated formatting changes, renaming for consistency, and architectural rewrites of working code.

## Implementation approach

- Make small, reviewable changes. Preserve the public convertMcf behaviour unless deliberately changing it.
- Derive behaviour from MCF structure, installed CEWE resources, and controlled editor comparisons. Establish a general rule before introducing special cases or calibration factors.
- Installed resources are the main real-user scenario. Portable test resources must exercise the same loading/rendering mechanisms.
- Reuse shared rendering, font, and resource mechanisms before adding alternatives.
- Keep prepared resources, rendering settings, per-conversion mutable state, and optional indexing distinct. Do not introduce conversion-time mutable globals.
- Keep the developer and user documentation aligned with changes in behaviour.

## Verification and approved results

- Run tests from the repository root using the intended environment.
- For code changes, run focused tests and relevant flake8/pylint checks, then the full pytest suite to establish regression safety. Documentation-only changes need appropriate content/link checks.
- Use python -m pytest -rs for a full run without the helper's stop-at-first-failure behaviour. Report incomplete runs as incomplete.
- Add feature coverage to an existing relevant MCF when it strengthens the integrated regression; otherwise use a dedicated fixture directory.
- Use portable fixture fonts/resources. New tests should run through pytest and directly as Python files, including from an IDE.
- Inspect actual rendered PDFs. Add structural assertions for invisible features such as annotations, bookmarks, and page labels.
- The programmer reviews and approves replacement PDFs after visual comparison. An assistant may generate candidates but must not promote them merely to make tests pass.
- Keep pixel comparisons exact by default. Any necessary tolerance belongs in the individual test/page, with measured limits and an explanation.
- Use the term "approved result" for accepted reference output.

## Generated output and cleanup

- Follow the current README cleanup procedure; review candidate paths before removal.
- Protect previous_result_pdfs and album image/resource directories, including names containing Dateien.
- Never clean with a broad recursive PDF or PNG deletion.
- On Windows, use the documented Recycle Bin method. On other platforms, use the documented platform-specific discovery and agree on removal where a reversible method is unavailable.
- Keep a candidate PDF when the programmer requests it for inspection.
