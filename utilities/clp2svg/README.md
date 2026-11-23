# clp2svg

Extract the SVG artwork stored in CEWE CLP files. The utility uses Python's
standard library; no additional packages are needed.

Run from the repository root. To extract one file:

```text
python -m utilities.clp2svg.clp2svg artwork.clp
```

This writes `artwork.svg` in the current directory. Choose an output filename
with `-o`, or extract several files into an existing directory with `-d`:

```text
python -m utilities.clp2svg.clp2svg artwork.clp -o extracted.svg
python -m utilities.clp2svg.clp2svg artwork.clp frame.clp -d output
```

Existing output files are overwritten. Input CLP files are unchanged.
For the encoding and resource conventions, see the
[CLP file format and authoring notes](../../clipart/CLP_FILE_FORMAT.md).
