# cewe2pdf

A program (a set of python scripts) to turn cewe photobooks into pdf documents.
The CEWE pdf export is achieved by interpreting the mcf xml-files
and compiling a pdf document which looks like the cewe photo book.

There are many capabilities in the Cewe album editor which are not supported by `cewe2pdf`, so an exact conversion cannot be guaranteed. The script is mostly based on reverse-engineering and guessing. It is not meeting any official specifications, so don't be surprised if one or another feature doesn't work. However, improvements are always appreciated!

The current tests run with albums created with the 8.0 version of the editor. We don't explicitly test that files from older versions of the editor still work (though code to handle them may still be there) so the safest bet to recreate a pdf from an old album file is surely to load it into the latest album editor and save it again.

Python 3.12 is the supported development and test version. Newer Python versions may work, but are not part of the automated test baseline. Older versions will probably fail because of missing Python features. The code is expected to work on Windows, MacOS and Linux.

You will need underlying Cairographics (<https://www.cairographics.org/>) support installed on your machine for the handling of clip art. How you get this will depend on your platform, but if you have the GTK+ toolkit installed (<https://www.gtk.org/docs/installations/>) that should do it.

In August 2026 the code was significantly rearranged into smaller files, to isolate functionality and make maintenance a little easier. Several improvements were made at the same time. The suite of pixel comparison suites was also extended. The code from cewe2pdf.py is basically still there and should be recognizable once you find the file in which it now lives. The work was done with the aid of OpenAI's Codex AI engine, which turned out to be very effective. Codex downloaded its own copy of the source structure from GitHub to the local machine, complete with tests, so that it could make its suggested changes first and run the test suite before making a final change proposal for whatever modification had been suggested.  

tags: mcf2pdf, mcf_to_pdf, CEWE Fotobuch als pdf speichern, Fotobuch nach pdf exportieren, cewe Fotobuch pdf, mcf in pdf umwandeln, aus CEW-Fotobuch ein pdf machen, cewe Fotobuch pdf

## Install

### 1. Obtain the repository

Clone or download this repository into a folder of your choice. The supported
development and test interpreter is Python 3.12. The following instructions
create an isolated Python environment so that cewe2pdf's dependencies do not
alter the rest of your Python installation.

### 2. Create a Python environment

The normal, reproducible installation uses `requirements-pinned.txt`. It pins
the versions which the project tests in GitHub Actions. `requirements.txt` is
the hand-maintained list of direct dependencies; it is not the file to install
for an ordinary development or user environment.

On Windows, using the standard Python distribution, run PowerShell in the
repository directory:

```
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-pinned.txt
```

Conda is an equally valid alternative. For example, from an Anaconda Prompt:

```
conda create --name cewe2pdf312 python=3.12
conda activate cewe2pdf312
python -m pip install --upgrade pip
python -m pip install -r requirements-pinned.txt
```

There is no need to mix Conda and Pip packages manually, or to apply the old
Pillow/WebP workaround previously described here.

On macOS or Linux, create and activate a virtual environment in the repository
directory:

```
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-pinned.txt
```

Use the name supplied by your platform if it calls the interpreter `python3`
rather than `python3.12`.

### 3. Install the Cairo runtime

Cairo is used by CairoSVG to render CEWE clip art. It is not supplied by Pip,
so source-code installations need a platform Cairo runtime as well as the
Python packages above. CairoSVG is currently imported while cewe2pdf starts,
so install the runtime even if the particular album has no clip art.

- **Windows:** installing the [GTK 3 runtime/toolkit](https://www.gtk.org/docs/installations/)
  is sufficient. Ensure its `bin` directory, containing `libcairo-2.dll`, is
  on `PATH` when running cewe2pdf from source. Do not copy DLLs into the
  Windows system directories.
- **macOS:** with Homebrew, run `brew install cairo`.
- **Debian/Ubuntu:** run `sudo apt install libcairo2`.
- **Fedora:** run `sudo dnf install cairo`.

Other distributions provide an equivalent Cairo runtime package. The private
Windows standalone executable described below bundles the Cairo DLLs; its
recipient does not need to install Cairo or Python.

### 4. Configure the CEWE installation (optional, but highly recommended!)

Locate the directory where the CEWE album software is installed. On Linux it
can be recognised by its many `.so` files and directories such as `Resources`.
Create a `cewe2pdf.ini` file alongside the album file and set `cewe_folder` to
that directory. This gives the most faithful results, including CEWE-delivered
backgrounds, clipart, passepartouts and fonts.

If CEWE is not installed, configuration is not required for a best-effort
conversion. cewe2pdf will use locally installed fonts and the images contained
with the album. It reports each unavailable CEWE background, clipart or
passepartout and leaves that decoration out of the PDF.

## Configuration files

### cewe2pdf.ini
If a ``cewe_folder.txt`` (see below) file is not found, then the program looks for files called ``cewe2pdf.ini``, first in the current directory and then in the album directory, reading both if it finds both. Later entries override previous entries of the same name. 

For normal use (i.e. actually creating a pdf album, rather than testing the code) the most reasonable strategy is to place a ``cewe2pdf.ini`` file with the album file, setting everything you need there, out of the way of future updates to the program repository.

For full CEWE resource support, specify the location of the CEWE installation folder in ``cewe2pdf.ini``. If you do not have CEWE installed on your machine you should specify an empty entry, `cewe_folder =`, but then the album itself must not have used resources which are supplied by CEWE - fonts, backgrounds, clip arts, etc.

``cewe2pdf.ini`` can also
* provide a list of locations for additional background images, cliparts, passepartouts (frames)
* define how the additional fonts you have specified (see below) are organised into families so that bold and italic texts are shown correctly
* define non-standard line spacing (linescale) for any fonts that need it
* define output resolution for the pdf
* and more
  
The contents might, for example, look like this:
```
[DEFAULT]
cewe_folder = C:\Program Files\Elkjop fotoservice_6.3\elkjop fotoservice

# Define font families where the defaults don't work properly. Take a good look
# at the full font diagnostics if you suspect issues with the choice of fonts
fontFamilies =
 FranklinGothic,FranklinGothic,FranklinGothic Medium,Franklin Gothic Book Italic,FranklinGothic Medium Italic

# Define the output resolutions, the default 300 is ok for printing, 150 for screen display only
pdfImageResolution = 150
pdfBackgroundResolution = 150

# Search shared operating-system font folders as well as CEWE and local fonts.
# Disabled by default because system fonts vary between machines.
#loadSystemFonts = True

# specify default leading (1.1 = 10% of the font size as leading is standard in the code, where we leave
# it unaltered for backward compatibility, but 1.15 works best when line spacing is used, see issue 182)
defaultLineScale = 1.15

# Define line scale (line spacing, essentially) for fonts where the default 1.1 (110%) is not acceptable
fontLineScales =
	Crafty Girls: 1.43

# For an album with outer edge page numbering, force the number to the right on all
# pages rather than keeping the original left on even, right on odd page placement
singlePageNumberPosition = right

# Define how the inside cover pages are processed in a keepDoublePages run
#  Default False, if True then the inside cover pages on a keepDoublePages run will be white (as CEWE)
#  rather than matching the background of the facing pages (i.e. the first and last usable pages)
#  This has no effect on a single page width run, where the inside cover pages are simply omitted
insideCoverWhite = False

# Shadows were implemented in May 2025 (except blur) but can be turned off
# Default False, if True then no shadows are created on objects
noShadows = False

# These possibilities are seldom needed in the latest versions of the program
#extraBackgroundFolders =
#	${PROGRAMDATA}/hps/${KEYACCOUNT}/addons/447/backgrounds/v1/backgrounds
#	tests/Resources/photofun/backgrounds
#extraClipArts =
#	63488, ${LOCALAPPDATA}/CEWE/hps/${KEYACCOUNT}/photofun/decorations/63488/rect_cream/rect_cream.clp
#	121285, ${LOCALAPPDATA}/CEWE/hps/${KEYACCOUNT}/photofun/decorations/121285/12089-clip-gold-gd/12089-clip-gold-gd.clp
#passepartoutFolders=${PROGRAMDATA}/hps

# Define the numbers of logging messages of various levels that are "usual" for your
# installation. This allows the program to tell you if there are differences in a run
# and therefore give you a hint that something needs your attention.
#expectedLoggingMessageCounts =
#	cewe2pdf.config: WARNING[32], INFO[669]
#	root:            ERROR[2], WARNING[4], INFO[38]
```
#### Advanced CEWE resource lookup

During development when we don't want to use resources from the local CEWE installation, you can set some related values in cewe2pdf.ini
* ``hpsFolder``: overrides the location of CEWE’s HPS/account-resource hierarchy.
* ``keyaccount``: selects the account folder within that hierarchy.

### additional_fonts.txt
The code knows where to find the fonts delivered with the Cewe software. It
also looks in the current user's local font folder, unless the
``IGNORELOCALFONTS`` environment variable is set (as it is for the regression
test run).

If the album uses other fonts (including those provided by the host operating system) you
should use the separate optional
configuration file ``additional_fonts.txt``. It contains one line per font file
or font directory to be added; both `.ttf` and `.otf` files are read.

Alternatively, set ``loadSystemFonts = True`` in ``cewe2pdf.ini`` to search the
shared operating-system font folders (for example ``C:\\Windows\\Fonts``).
This is disabled by default because the available fonts differ between
machines.

To find a potential ``additional_fonts.txt`` the code searches, in order, the album directory, the current directory and the location of the program itself; it uses only the **first** such file found.

For normal use (i.e. actually creating a pdf album, rather than testing the code) the most reasonable strategy is to place an ``additional_fonts.txt`` file with the album file, out of the way of future updates to the program repository. The repository supplies a commented ``additional_fonts.example.txt`` which you can copy and adapt. It is deliberately not called ``additional_fonts.txt``, so it is never used as implicit configuration.

Example for Windows font file and directory paths:
```
C:\Windows\Fonts\BOD_R.TTF
C:\Windows\Fonts\
```
Example for linux font file and directory paths:
```
/usr/share/fonts/truetype/lato/Lato-Heavy.ttf
/home/myusername/.local/share/fonts/
```
### cewe_folder.txt (deprecated)
Go to the directory where cewe2pdf is installed and create a text file there with filename ``cewe_folder.txt``
and use a text editor to write the installation directory of the CEWE software into the text file.
For example, if you have the software branded for the company DM, called "dm-Fotowelt", then the file ``cewe_folder.txt`` might contain:
```
C:\Program Files\dm\dm-Fotowelt\dm-Fotowelt.exe
```
Save the file and close it. Alternatively - indeed, preferably, if you want full functionality! - use more extensive configuration by using ``cewe2pdf.ini`` instead of ``cewe_folder.txt``, as described below

## Album files
### .mcf
`.mcf` is the format that Cewe has used for many years for albums, until the introduction of the newer `.mcfx` format around 2023. This is the format around which `cewe2pdf` has been developed; the file content is XML. There is always a folder `<album>_mcf-Dateien` associated with a `.mcf` file, containing the images used in the album.

### .mcfx
If your CEWE software uses `.mcfx` files for your projects, you can specify the file name directly on the command line. The `.mcfx` file format is actually an sql database containing a single `.mcf` file and the related image files. `cewe2pdf` will create a temporary directory, unpack the the `.mcfx` there, process the result, and then delete the temporary directory again 

### .xmcf
If your CEWE software uses `.xmcf` files for your projects, you can simply still use this. The `.xmcf` file format is just an archive of the `*.mcf` file, the `<album>_mcf-Dateien` folder and a few other files. Right click the `.xmcf` file and your os should give you an open to open the archive. Copy the relevant files out of it, and you should be all set for the next steps.

## Feature implementations

### Border decorations

Borders are supported for image, text and clip-art areas. The colour, width,
gap and the four CEWE positions (`centered`, `insideWithGap`, `outside` and
`outsideWithGap`) are supported.

For ordinary rectangular areas the historic ReportLab `Table` rendering is
retained, partly to preserve the established regression-test output. Borders
on objects with supported convex and bevelled image corners instead use the same shaped
path as the image, so that the border follows the corner rather than the
original rectangle.

### Shadow decorations

The CEWE angle, distance, intensity, expansion (`shadowWidthInMM`) and blur
settings are interpreted from the MCF. Their visual effect is based on
measurements from the album editor, rather than an official CEWE specification,
so our shadows are a best-effort approximation.
Image shadows use a transparent alpha silhouette of the rendered image. They
therefore follow supported corner decorations and transparent image content.

The legacy rectangular shadow renderer remains for non-image callers. Shadows
on text areas are not implemented and produce a warning. Set `noShadows = True`
in `cewe2pdf.ini` to suppress all shadows.

### Corner decorations

cewe2pdf renders the `default`, `convex`, `bevelled`, `notched`, and `concave`
corner decorations used by the CEWE album editor. Unknown corner shapes remain
square and the run logs a warning.

### Text effects

Most text settings are supported, including font family, size, bold, italic, colour.

#### Line height

Line height is supported. 

CEWE's explicit CSS `line-height` percentage in the HTML stored in the text
area is supported. The renderer bases the percentage on ReportLab's natural
line box for the selected font so that 100% and larger values behave
consistently. The editor's `textFormat` element is used for several area-wide
settings, but is not the source of this line-height implementation.

#### Outlines

Text areas with a visible `<outline>` element are rendered with a fill and
stroke. Colour and width are supported, including rotated and italic text. Outline
is generally only useful on large text, for example banner headings. 

`textFormat.hasOutline` is only an editor flag; an outline is visible only when
the MCF also supplies a positive width and a non-transparent colour.

#### Letter spacing

The area-wide `textFormat.letterSpacing` setting is supported. Per-span letter
spacing and wrapping-aware measurement are not implemented, so heavily spaced
text near the edge of a narrow frame deserves visual checking.

#### Tabs

Literal tabs in a simple single line left-aligned paragraph imitate CEWE's 8 mm
tab stops. The direct tab renderer preserves per-span font family, bold,
italic, size, colour and underline, as well as area-wide outlines and letter
spacing.

It is not a general replacement for ReportLab paragraph layout. Paragraphs
with line breaks, nested markup, tables, lists, non-left alignment, or text
which would run beyond the frame fall back to the older non-breaking-space
approximation. Tabbed text does not wrap across tab stops.

The text-area background is drawn separately from the text itself. CEWE can
store its opacity in the `#AARRGGBB` background colour and/or in a decoration
`alpha` attribute; cewe2pdf combines both values. This preserves translucent
text panels over a page background while leaving the text opaque.

#### Text Art

Text art objects are supported, but combination with backgrounds and outlines has not been tested.

#### Bullet and numbered lists

These are not something you can create in the album editor, but if you make them in, for example, Google Docs, and paste them into the album, then it will actually render them. We also render them, though not in _exactly_ the same way as they are in the album editor

### Indexing an album (not available in the CEWE editor)

It is possible to ask cewe2pdf to generate an index for the album, where index terms are selected using a combination of of font and font size used in a text area. The index is initially generated as a separate pdf file with black text on white background. The index pdf is used to create an index image file, a png in which the background is transparent. That png image is then merged into the album pdf, being placed on any page containing an index marker identifier.

This feature may be useful in, for example, an album which represents a day-by-day record of some period of time. The headings for each day in the album can be specified in a font/fontsize combination which is not used for any other purpose in the album, and the index will then present a short day-by-day summary with page number references.

It is normal to allow cewe2pdf to delete the index pdf but to retain the index png. That allows you to manually insert the index png onto the index page in the album editor, and thus have it as part of the album which is sent for quality printing (if you do that!). If you rerun the album pdf generation, creating a new index png to be merged into the album, the merge process will remove any old index png from the index page before adding the new one (based on best-effort recognition of the image in the pdf!)

The page on which the index is to be placed is recognised by the presence of a text on the page. The text is identified with a regular expression defined in the .ini file, and would often be a visible text such as "Contents". If you don't want a visible text, you can always set the colour of the text to "None". Other things on the index page (photos, clip-art, text, etc) are left undisturbed and should be visible since the background of the index image is transparent.

There are a host of index configuration options which can be specified in a separate section of the .ini file. No indexing will take place unless there is an __INDEX__ section and the __indexing__ value is __True__
```
[INDEX]
indexing = False
indexEntryFonts =
	Arial Rounded MT Bold, 15
indexFont = Helvetica
indexFontSize = 12
lineSpacing = 1.1
pageWidth = 210
pageHeight = 291 # A4 is 297. 291 is the size of the paper in a 30x30 album
indexMarkerRegex = ^Contents$
topMargin = 5
bottomMargin = 0
leftMargin = 7
rightMargin = 7
deleteIndexPdf = True
deleteIndexPng = False
```
__indexEntryFonts__ specifies one or more font / font sizw combinations which will be used to recognise index terms in the album

__indexFont, indexFontSize, lineSpacing, pageWidth, pageHeight__ determine how the index entries are formatted on the index pdf page

__indexMarkerRegex__ specifies the regular expression against which all text items in the album are tested. Any page with a matching text will be used for insertion of the index png

__topMargin__ etc determine the placement of the index png on the index page. The image is scaled appropriately to fit.

__deleteIndexPdf__ etc determine whether or not the generated files are deleted after the album pdf has been updated.

There are also margin settings for the creation of the index pdf, __pdfTopMargin__ etc. These may be useful if you intend to keep and use the generated index pdf, but default to 1 so that the pdf page is filled and the image margins are the most important.

#### Large index limitations
The current code only handles a single index page. If there are more index terms than fit on a single page, the index pdf will be correct, but the index image will only take the first page.


## Acceptable products
The program was developed to handle CEWE photo books - photograph albums - and is absolutely **not** guaranteed to handle other products from the same editor such as calendars, cards, invitations, etc. Feeding *cewe2pdf* with one of these is at best unlikely to create the right result, and indeed is more likely to cause it to crash unpredictably.

Despite the above warning, changes in Nov 2024 should allow mcf files for the Photo Pairs game to be handled correctly. The resulting 6x6cm pages can be printed using Acrobat, using multiple sheets to a page with, for example, 4 across and 6 down on an A4 sheet. Print two copies, glue them to carton, cut them out and you have your memory game.

## Using the program
You should now have 

* a program directory containing all the python code needed, the most important being `cewe2pdf.py`.
* one or more album directories each containing
  - one or more `*.mcf` or `.mcfx` album files
    * a directory named `<album>_mcf-Datein` for each album, if you are using `*.mcf`
  - a `cewe2pdf.ini` configuration file (or maybe the now deprecated `cewe_folder.txt`)
  - optionally, an `additional_fonts.txt` configuration file

It is not really a good idea to place your album files in the same directory as the program. Keep them separate so there is no confusion in keeping your version of the program up to date with your Github repository version.

### Usage

Run `cewe2pdf.py` with the name of your album file and an equivalent pdf file will be created beside the album file.
Example:
```
python cewe2pdf.py c:\path\to\my\files\my_nice_fotobook.mcf
```
### Command line options
`cewe2pdf` supports the following options, shown if you run ```python cewe2pdf.py --help```
```
usage: cewe2pdf.py [-h] [--keepDoublePages] [--pages PAGES]
                   [--tmp-dir MCFXTMP] [--appdata-dir APPDATA] [--version]
                   [--outFile OUTFILE] [inputFile]

Convert a photo-book from .mcf/.mcfx file format to .pdf

positional arguments:
  inputFile             Just one mcf(x) input file must be specified (default: None)

options:
  -h, --help            show this help message and exit
  --keepDoublePages     Each page in the .pdf will be a double-sided page, instead of a normal single page. (default: False)
  --pages PAGES         Page numbers to render, e.g. 1,2,4-9 (default: None, which of course processes all the pages). These refer to the inside page numbers as you see them in the album editor - the first user editable inside page is number 1. If you want the front cover, then ask for page 0. Asking for the back cover explicitly will not work!
  --tmp-dir MCFXTMP     Directory for .mcfx file extraction (default: None)
  --appdata-dir APPDATA
                         Directory for persistent app data, eg ttf fonts converted from otf fonts (default: None)
  --version             Show version and build identification, then exit
  --outFile OUTFILE     The name of the output file, rather than the default
                        <inputFile>.pdf (default: None)

Example:
   python cewe2pdf.py c:\path\to\my\files\my_nice_fotobook.mcf
```

## Development

For a newcomer-oriented overview of the modules, data ownership and regression
test structure, see the [Developer guide](DEVELOPER_GUIDE.md).

### Python dependencies

The project has three dependency files with distinct jobs:

- `requirements.txt` is maintained by hand. It lists the direct runtime,
  test and lint dependencies, with the ranges the project supports.
- `requirements-pinned.txt` is the generated lock file for that normal Python
  environment. It pins those packages and their dependencies to the exact
  versions which have been tested. Do not edit it by hand.
- `requirements-winexe.txt` is a small, exact Windows-only overlay on the
  pinned file. It supplies PyInstaller and its dependencies for developers
  building `cewe2pdf.exe`.

For a new development or test environment, install the lock file:

```
python -m pip install -r requirements-pinned.txt
```

GitHub Actions uses `requirements-pinned.txt` for linting and tests, and
`requirements-winexe.txt` for its separate Windows executable build. Therefore,
when a direct dependency is added or its supported range is changed in
`requirements.txt`, regenerate the pinned file, run the full tests and the
Windows executable build, and commit the related files together:

```
pip-compile --output-file=requirements-pinned.txt requirements.txt
```

After regenerating `requirements-pinned.txt`, preserve its PyInstaller-free
purpose: update `requirements-winexe.txt` only when a PyInstaller build
dependency changes. `pip-tools` is used only to maintain the lock file, rather
than to run or build cewe2pdf. The current lock was generated with Python 3.12,
pip 24.3.1 and pip-tools 7.5.1; use that combination in a separate tool
environment when regenerating it.

### Overall program structure

The conversion is deliberately split into a small orchestration layer and
specialist rendering modules:

1. `conversionSetup.py` opens the `.mcf` or `.mcfx` album, reads its
   configuration, and resolves the fonts, clip art, backgrounds and
   passepartouts needed for the run.
2. `cewe2pdf.py` creates the ReportLab canvas and the `RenderContext`, which
   contains shared rendering settings and resources. It then asks
   `pages.py` to render the requested pages.
3. `pages.py` understands CEWE's cover, inside-cover and paired-page layout.
   For each output page it draws the background and calls back to
   `processElements` for the page areas.
4. The area handlers render the individual objects: `imageareas.py`,
   `textareas.py` and `clipartareas.py`. Supporting modules handle details
   such as borders, shadows, corners, page numbers and indexes.

MCF positions and sizes are measured in tenths of a millimetre. ReportLab
uses points, so the conversion factor is carried in `RenderContext` as
`mcf_to_reportlab`. A page area's origin is translated to its centre before
it is rotated, allowing the individual handlers to draw their contents around
`(0, 0)`.

The text stored in an MCF is HTML-like rather than a direct ReportLab format.
`textareas.py` translates the useful CEWE formatting into ReportLab
paragraphs. Small text-size adjustments may be made when ReportLab's font
metrics would otherwise make the text overflow its CEWE frame.

The project deliberately uses pixel-level regression tests. When a rendering
change is intentional, visually verify the new PDF before replacing an
approved PDF in a test's `previous_result_pdfs` directory.

### Version numbering

Each conversion logs a user-facing program version and Git build
identification. The user-facing version is the manually maintained
`PROGRAM_VERSION` constant in `programversion.py`, currently in `m.n` form.
Incrementing `m` or `n` is intentionally a maintainer judgement, based on the
significance of the changes being merged into `bash0/cewe2pdf` master.

To display this information without converting an album, use:

```
python cewe2pdf.py --version
```

The same option is available from the standalone executable:

```
dist\cewe2pdf.exe --version
```

After the tests succeed for a commit pushed to canonical `bash0/cewe2pdf`
master, the GitHub workflow creates a tag of the form
`cewe2pdf-v<m.n>-build-<GitHub-run-number>`. Tags identify the exact tested
commit without making an automatic commit to master. They can be seen in the GitHub web 
interface on the code tab:

<img width="382" height="420" alt="image" src="https://github.com/user-attachments/assets/a512c662-dc21-4ad1-99d2-229c25f71894" />

Forks and branches run the
same checks but do not create canonical tags; fetch upstream tags to make their
nearest canonical build available locally.

The log can therefore look like either:

```
>>> cewe2pdf version 1.0; Git identification: cewe2pdf-v1.0-build-178-0-g844e6d0
>>> cewe2pdf version 1.0; Git identification: cewe2pdf-v1.0-build-178-3-g844e6d0-dirty
>>> cewe2pdf version 1.0; Git identification: a046aed-dirty
```

The first form means that the working tree is exactly at the specified build. 
The second form means that the working tree is 3 builds later than the specified build. 
The third means that no matching build tag is available locally;
`a046aed` and `g844e6d0` is abbreviated commit IDs. 
`dirty` is a diagnostic indication that
the working tree has uncommitted changes, so it is not an approved reproducible
build. A source archive without `.git` metadata logs that Git identification
is unavailable. PyInstaller captures the Git description while building a
standalone executable and bundles it, so a normally built executable retains
the identification of its source build.

To reproduce an approved canonical build, clone the canonical repository,
fetch its tags, and check out the reported build tag:

```
git clone https://github.com/bash0/cewe2pdf.git
cd cewe2pdf
git fetch --tags
git checkout cewe2pdf-v1.0-build-184
```

This gives the exact source commit which passed the canonical test workflow.
Developers working in a fork can instead fetch the same tags from their
`upstream` remote.

### Standalone executable

The project does not publish executable releases. A Windows developer may build
an executable privately for a friend after preparing the normal environment
and then installing the Windows-only overlay:

```
python -m pip install -r requirements-pinned.txt
python -m pip install -r requirements-winexe.txt
```

Cairo must be available on the build machine (the GTK+ toolkit/runtime is
sufficient); the finished EXE bundles the required Cairo DLLs, so its recipient
does not need GTK, Cairo, MSYS2 or Python.

Build the checked-in specification file:
```
python -m PyInstaller cewe2pdf.spec --clean
```
The executable is written to `dist/cewe2pdf.exe`. The specification explicitly
includes the dynamically imported OpenCV and NumPy components needed by the
indexing code; do not replace it with a direct `--onefile` invocation. You can
run pytest from the working directory, use `runalltests.py`, or run individual
test files.
### Test verification using pixel level result comparison with compare-pdf
We have a local copy of the compare-pdf code from https://github.com/Formartha/compare-pdf. This code can be used from our automated unit test code to do pixel-by-pixel comparison of the pdf pages that have been generated with a previous (approved) version. This strategy has been implemented for several of the tests, and it is therefore important that each test has an "approved" result pdf with which any new version is compared (see below)

In addition compare_pdf can be used from the command line to see details of the differences. Just change to our tests/compare-pdf directory and run the command
```
pip install .
```
Then you can call compare_pdf from the command line to show the two pdfs side by side, or as a diff image.
```
compare_pdf --pdf <path_to_pdf1> --pdf <path_to_pdf2> ... [--showdiffs={sidebyside|diffimage}]
```
_--showdiffs=sidebyside_ lets you do a visual comparison, but often the differences are subtle and difficult to see (a different font for text is a typical subtle difference!). In that case _diffimage_ will show you where the pixels differ and often give you a good enough hint to understand what has changed. 
### Conventions for naming and retaining approved result pdfs
In each test directory where pixel comparison forms part of the test, it is necessary to keep an approved version (maybe several) to compare against. These are kept in a folder conventionally named _previous_result_pdfs_, and are conventionally named as the original mcf name with a suffix containing the date (yyyymmdd) and a style letter ("S" for single side pdfs, "D" for double side pdfs). The test programs create output files using this naming convention in their own directory. If a new version is different from the latest version in _previous_result_pdfs_ __AND__ is deemed to be correct by the developer, then the new test output(s) can be moved to _previous_result_pdfs_ and checked in there, thus becoming the basis against which future test results will be compared.
### Testing using programmed variations of the .mcf file
The _testPageNumbers_ tests show how you can use python in your test code to modify the xml of the .mcf file. This allows you to make variations of your test without having specifically designed album files. When combined with pixel by pixel comparison this allows quite extensive regression tests to be created.
### Hints
Tests using compare-pdf originally used the modification time to sort result pdfs and choose the latest approved version. This doesn't work on github, and we now use the file naming convention to sort the files. For interest, however, there is no touch(1) command on Windows, and powershell must be used to change the timestamp for a file, like this:
```
(Get-ChildItem .\testalbum.mcf.20250326.pdf).LastWriteTime = New-object DateTime 2025,03,26,19,00,00
```
### Cleaning up temporary files 
Running tests during development can leave temporary output files lying around. Cleaning these away is a bit tricky, because it's important not to delete the approved result pdfs. On Windows you can locate these files with a powershell command like this:
```
$pattern = '^(test|unittest|allblack)[A-Za-z0-9._-]*\.mcf\.\d{8}[DS]\.(pdf|idx\.png)$'
Get-ChildItem -Recurse -File |
Where-Object {
    $_.FullName -notmatch '\\previous_result_pdfs\\' -and
    $_.Name -match $pattern
}
```
and then delete them (via the recycle bin) with
```
Add-Type -AssemblyName Microsoft.VisualBasic

Get-ChildItem -Recurse -File |
Where-Object {
    $_.FullName -notmatch '\\previous_result_pdfs\\' -and
    $_.Name -match $pattern
} |
ForEach-Object {
    [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(
        $_.FullName,
        'OnlyErrorDialogs',
        'SendToRecycleBin'
    )
}
```
If you want a dry run first, just replace the DeleteFile section with:
```
Write-Output "Would delete: $($_.FullName)"
```
Finding the files on Linux is rather easier :-):
```
find . -type f -name "*.pdf" \
  ! -path "*/previous_result_pdfs/*" \
  | grep -E "/[^/]*[0-9]{8}[DS]\.pdf$"
```
You can of course make the pattern matching a little more cautious if you want to be absolutely sure you don't delete something important!
