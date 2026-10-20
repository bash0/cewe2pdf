# cewe2pdf programming guidance

Read this file before editing. Use the [README documentation map](README.md#documentation) to find the user guide, architecture, test workflow, and implementation rationale.

## Workspace and review

- Work only in the checkout or task worktree authorized by the programmer. Keep generated output there.
- Follow the programmer's review workflow; do not stage, commit, push, merge, publish, or synchronize another checkout without authorization.
- Report the resulting behaviour, verification performed, and unresolved failures or limitations. An incomplete test run is not a passing suite.
- Keep private conversation transcripts, personal paths, and account details out of shared documentation.

## Coding conventions

- Prefer f-strings, including logging, and follow existing names.
- Prefer explicit conditions and product dispatch; avoid chained comparisons where separate conditions are clearer.
- Use one indent level for continuation lines rather than aligning beneath an earlier expression.
- Explain undocumented CEWE conventions, empirical calibration, ownership, and non-obvious Python mechanisms in focused comments.
- Use descriptive domain names; avoid unrelated formatting, consistency renames, and architectural rewrites of working code.
- Follow the repository's flake8/pylint configuration. Use narrow, explained suppressions rather than distorting a design to satisfy a metric.

## Platforms and file integrity

- Support normal Python execution on Windows, Linux, and macOS. Guard Windows-only imports and integration.
- Verify the interpreter and use the [supported environment setup](README.md#install); do not assume a particular local environment name or path.
- Write shared Markdown as UTF-8. Follow repository attributes and explicit local text-file conventions; otherwise preserve existing line endings.
- CRLF is a local Windows preference, not a requirement for all contributors. Avoid unrelated newline changes and preserve binary resources byte-for-byte.
- Use platform-aware paths and resource discovery. Close temporary files and database connections before reopening, replacing, or cleaning them.

## Changes and verification

- Make small, reviewable changes. Preserve established `convertMcf` behaviour unless deliberately changing it.
- Derive behaviour from MCF structure, resources, and controlled editor comparisons. Establish a general rule before adding special cases or calibration factors.
- Reuse shared rendering, font, and resource mechanisms. Respect the [architecture and ownership boundaries](documents/DEVELOPER_GUIDE.md#conversion-model); avoid conversion-time mutable globals.
- Follow the [test workflow](tests/README.md), including focused checks, linting, and full regression verification for code changes. Documentation-only changes need encoding, link, and content checks.
- Generate candidate PDFs for review; the programmer approves replacement results. Never promote a candidate simply to make tests pass.
- Follow the [cleanup procedure](tests/README.md#cleaning-up-temporary-files), protecting approved results and album resources. Preserve outputs requested for inspection.

## Documentation ownership

Keep detailed information in its authoritative home and link to it:
- [README](README.md): installation, configuration, usage, and supported features.
- [Developer guide](documents/DEVELOPER_GUIDE.md): architecture, dependency maintenance, diagnostics, and versioning.
- [Tests](tests/README.md): execution, fixture conventions, approval, and cleanup.
- [Build guide](documents/build_a_compiled_version.md): executable builds and Windows integration.
- [Project context](documents/PROJECT_CONTEXT.md): rationale behind non-obvious implementation choices.
- [History](documents/history/README.md): superseded notes, not current instructions.

Update the relevant document when changing behaviour. Format-specific notes stay beside their implementation.
