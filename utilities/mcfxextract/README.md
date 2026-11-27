# mcfxextract

Extract a CEWE `.mcfx` archive without generating a PDF. This utility uses only
Python's standard library; installed CEWE software, fonts and PDF packages are
not required. Run it from the cewe2pdf repository root with Python 3.12:

```powershell
python -m utilities.mcfxextract.mcfxextract "C:\Albums\Holiday.mcfx"
python -m utilities.mcfxextract.mcfxextract "C:\Albums\Holiday.mcfx" -o "C:\Temp\Holiday"
```

On Linux or macOS, use the same module command with your own paths. By default,
`Holiday.mcfx` extracts into a new sibling directory called `Holiday`. An explicit
`-o` selects a different directory. The destination must not already exist, even
if empty. There is no overwrite or merge mode. Exit status is 0 on success and 1
on extraction failure (2 for command-line syntax errors).

The archive is opened as a read-only SQLite database. Every embedded file is
extracted, including the MCF document (normally `data.mcf`), photos, retained
originals/intermediate edits, backups and opaque resources. Stored filenames and
subdirectories are retained; Windows path separators are interpreted on all
platforms. Unsafe, duplicate or conflicting paths are rejected. Nothing is
filtered merely because no page displays it.

Only the main MCF document is shortened after its closing `</fotobook>` tag to
remove native binary padding. Its XML is otherwise unchanged. Other embedded
files are preserved byte-for-byte. The summary reports the number of files and
actual extracted bytes, excluding discarded document padding. File modification
times are extraction times; archive timestamps are not restored.

The utility does not rename photos, impose page order on them, rewrite the MCF's
`imagedir` or construct a new named MCF/Dateien pair. Native archives normally use
an empty `imagedir` and place resources beside `data.mcf`. Any different stored
layout is extracted as-is. Inspect the MCF before moving its resources elsewhere.

Validation happens before output creation. An I/O error during extraction can
leave a partial output directory; inspect it and choose a fresh destination when
retrying. The source archive is never modified.

The shared reader is `infrastructure.mcfx_archive.extract_mcfx`. The converter's
`mcfx.unpackMcfx` wrapper uses it with its historical timestamp cache and
temporary-directory ownership; the standalone utility always requires a new
output directory. Neither path changes the process working directory.

This is container extraction, unlike an ordered photo export: sequence/year
prefixes, selecting only displayed photos and a graphical progress/cancel UI
are outside this utility's scope.
