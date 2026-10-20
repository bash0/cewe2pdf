# cewe2pdf

A program (a set of python scripts) to turn cewe photobooks into pdf documents.
The CEWE pdf export is achieved by interpreting the mcf xml-files
and compiling a pdf document which looks like the cewe photo book.

There are many capabilities in the Cewe album editor which are not supported by `cewe2pdf`, so an exact conversion cannot be guaranteed. The script is mostly based on reverse-engineering and guessing. It is not meeting any official specifications, so don't be surprised if one or another feature doesn't work. However, improvements are always appreciated!

The regression fixtures cover multiple editor versions, but not every version or product.
When an older album fails, try opening and saving a copy in the installed CEWE editor
before converting it. Keep the original album as a backup.

Python 3.12 is the supported development and test version. Newer Python versions may work, but are not part of the automated test baseline. Older versions will probably fail because of missing Python features. The code is expected to work on Windows, MacOS and Linux.


tags: mcf2pdf, mcf_to_pdf, CEWE Fotobuch als pdf speichern, Fotobuch nach pdf exportieren, cewe Fotobuch pdf, mcf in pdf umwandeln, aus CEW-Fotobuch ein pdf machen, cewe Fotobuch pdf

## Documentation

Start with the installation and usage sections below. The following guides provide
more detail for users, contributors, and coding assistants.

| What you want to do | Where to look |
| --- | --- |
| Install, configure, and run the converter | [Installation](#install), [configuration](#configuration-files), and [usage](#using-the-program) in this README |
| Understand supported features and products | [Feature implementations](#feature-implementations) and [acceptable products](#acceptable-products) |
| Start development or understand the architecture | [Developer guide](documents/DEVELOPER_GUIDE.md) |
| Understand implementation decisions and CEWE conventions | [Project context](documents/PROJECT_CONTEXT.md) |
| Give a coding assistant the project programming conventions | [Programming guidance](AGENTS.md) |
| Set up and test Linux using WSL | [Linux/WSL guide](documents/TestingOnWSL.md) |
| Build or install a standalone executable | [Build and Windows integration guide](documents/build_a_compiled_version.md) |
| Work with tests and approved PDFs | [Test workflow and cleanup](tests/README.md), and [compare-pdf interface](tests/compare-pdf/README.md) |
| Understand or author clip art and passepartout resources | [CLP file format and authoring notes](clipart/CLP_FILE_FORMAT.md) |
| Consult superseded setups and investigations | [Historical documentation](documents/history/README.md) |

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
The program looks for files called ``cewe2pdf.ini``, first in the current directory and then in the album directory, reading both if it finds both. Later entries override previous entries of the same name.

For normal use (i.e. actually creating a pdf album, rather than testing the code) the most reasonable strategy is to place a ``cewe2pdf.ini`` file with the album file, setting everything you need there, out of the way of future updates to the program repository.

For full CEWE resource support, specify the location of the CEWE installation folder in ``cewe2pdf.ini``. Without an installation, set `cewe_folder =` to select reduced-resource conversion;
missing delivered fonts may be substituted and missing decorations omitted.

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

# Defaults are 150 dpi; use 300 for higher-resolution photo output
pdfImageResolution = 150
pdfBackgroundResolution = 150

# Search shared operating-system font folders as well as CEWE and local fonts.
# Disabled by default because system fonts vary between machines.
#loadSystemFonts = True

# Default line scale: 1.15 means 15% leading relative to the font size
defaultLineScale = 1.15

# Override line scale for individual fonts when the default is unsuitable
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

# Disable shadows on images, clip art, and text
# Default False, if True then no shadows are created on objects
noShadows = False

# Optional PDF document properties.  If title is omitted, the input filename
# (without .mcf or .mcfx) remains the PDF title.
[PDF_METADATA]
title = My photo album
author = Your name

# Make the top-left 10 mm of photographs with EXIF GPS coordinates clickable,
# opening their position in Google Maps. This is disabled by default because
# location may be sensitive personal data. ``urlTemplate`` supports
# {latitude} and {longitude}; replace it to use another map service.
[PDF_GEO_LINKS]
enabled = True
hotspotSizeMm = 10
urlTemplate = https://www.google.com/maps?q={latitude},{longitude}

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
#### Missing-font substitutions

To choose a replacement when a requested font is unavailable, add name pairs to
`cewe2pdf.ini`:

```ini
[DEFAULT]
missingFontSubstitutions =
    Courier PS: Courier
    Times New Roman: Times-Roman
```

Each replacement must be a loaded font or a built-in ReportLab base font.
Unavailable replacements are reported and ignored. Font metrics can differ, so
substitution may change wrapping even when the requested appearance is similar.

## Album files
### .mcf
`.mcf` is the format that Cewe has used for many years for albums, until the introduction of the newer `.mcfx` format around 2023. This is the format around which `cewe2pdf` has been developed; the file content is XML. There is always a folder `<album>_mcf-Dateien` associated with a `.mcf` file, containing the images used in the album.

### .mcfx
If your CEWE software uses `.mcfx` files for your projects, you can specify the file name directly on the command line. The `.mcfx` file format is actually a SQLite database containing a single `.mcf` file and the related image files. `cewe2pdf` will create a temporary directory, unpack the `.mcfx` there, process the result, and then delete the temporary directory again

### .xmcf
If your CEWE software uses `.xmcf` files for your projects, you can simply still use this. The `.xmcf` file format is just an archive of the `*.mcf` file, the `<album>_mcf-Dateien` folder and a few other files. Right click the `.xmcf` file and your os should offer to open the archive. Copy the relevant files out of it, and you should be all set for the next steps.

## Feature implementations

### Border decorations

Borders are supported for image, text and clip-art areas. The colour, width,
gap and the four CEWE positions (`centered`, `insideWithGap`, `outside` and
`outsideWithGap`) are supported.

For ordinary rectangular areas the historic ReportLab `Table` rendering is
retained, partly to preserve the established regression-test output. Borders
on objects with supported image corners instead use the same shaped
path as the image, so that the border follows the corner rather than the
original rectangle.

### Shadow decorations

The CEWE angle, distance, intensity, expansion (`shadowWidthInMM`) and blur
settings are interpreted from the MCF. Their visual effect is based on
measurements from the album editor, rather than an official CEWE specification,
so our shadows are a best-effort approximation.
Image shadows use a transparent alpha silhouette of the rendered image. They
therefore follow supported corner decorations and transparent image content.

Clip-art and text shadows also use their visible alpha silhouettes rather than a
rectangle around the area. Set `noShadows = True` in `cewe2pdf.ini` to suppress shadows.

### Corner decorations

cewe2pdf renders the `default`, `convex`, `bevelled`, `notched`, and `concave`
corner decorations used by the CEWE album editor. Unknown corner shapes remain
square and the run logs a warning.

### Transparency

Opacity set in the editor is supported for photographs and clip art, including
existing transparent pixels. A photograph's passepartout frame shares its opacity.
For text panels, see [text backgrounds](#text-backgrounds).

### Text effects

Most text settings are supported, including font family, size, bold, italic, colour.

#### Line height

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

#### Text backgrounds

The text-area background is drawn separately from the text itself. CEWE can
store its opacity in the `#AARRGGBB` background colour and/or in a decoration
`alpha` attribute; cewe2pdf combines both values. This preserves translucent
text panels over a page background while leaving the text opaque.

#### Text Art

Curved Text Art follows circular or elliptical geometry, including its inside margin.
Area-wide positive and negative letter spacing is supported in both directions;
the spacing is included when centring the lettering on the curve.
TextArt backgrounds and shadows are not implemented; combinations with further effects need visual checking.

#### Bullet and numbered lists

These are not something you can create in the album editor, but if you make them in, for example, Google Docs, and paste them into the album, then it will actually render them. We also render them, though not in _exactly_ the same way as they are in the album editor

### Indexing an album (not available in the CEWE editor)

It is possible to ask cewe2pdf to generate an index for the album, where index terms are selected using a combination of font and font size used in a text area. The index is initially generated as a separate pdf file with black text on white background. The index pdf is used to create an index image file, a png in which the background is transparent. That png image is then merged into the album pdf, being placed on any page containing an index marker identifier.

This feature may be useful in, for example, an album which represents a day-by-day record of some period of time. The headings for each day in the album can be specified in a font/fontsize combination which is not used for any other purpose in the album, and the index will then present a short day-by-day summary with page number references. If there are too many entries for one index page, cewe2pdf creates multiple index images and places them on successive marked album pages. Index headings also provide bookmarks and clickable contents rows; see [PDF navigation](#pdf-navigation-and-links).

It is normal to allow cewe2pdf to delete the index PDF but to retain the index PNGs. They are consistently named `album.idx.1.png`, `album.idx.2.png`, and so on, even if there is only one page. That allows you to manually insert the index PNG onto the index page in the album editor, and thus have it as part of the album which is sent for quality printing (if you do that!). If you rerun the album PDF generation, cewe2pdf recognises and omits any earlier generated index image saved into the CEWE album before merging the newly generated replacement.

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
# Optional PDF-reader navigation root; defaults to Contents.
outlineTitle = Contents
# Margins within each generated index-PDF page; these determine how many
# entries fit before a new index page is generated.
pdfTopMargin = 1
pdfBottomMargin = 1
pdfLeftMargin = 1
pdfRightMargin = 1
# Margins for placement of the completed index image on the album page.
topMargin = 5
bottomMargin = 0
leftMargin = 7
rightMargin = 7
deleteIndexPdf = True
deleteIndexPng = False
```
__indexEntryFonts__ specifies one or more font / font size combinations which will be used to recognise index terms in the album

__indexFont, indexFontSize, lineSpacing, pageWidth, pageHeight__ determine how the index entries are formatted on the index pdf page. Increasing __indexFontSize__ or __lineSpacing__ makes fewer entries fit on each index page.

__indexMarkerRegex__ specifies the regular expression against which all text items in the album are tested. Any page with a matching text will be used for insertion of the index png

__pdfTopMargin__, __pdfBottomMargin__, __pdfLeftMargin__ and __pdfRightMargin__ define the usable area within each generated index PDF page. In particular, increase __pdfBottomMargin__ (or __pdfTopMargin__) to start a new index page sooner. These settings determine the number of entries in each generated PNG.

__topMargin__ etc determine the placement of the completed index PNG on the album page. The image is scaled appropriately to fit. They do not affect the number of entries which it contains.

__deleteIndexPdf__ etc determine whether or not the generated files are deleted after the album pdf has been updated.

#### Large index limitations
The index may span multiple pages. Add one index-marker page to the album for each expected index image; images are placed on matching pages in PDF order. If there are too few or too many marker pages for the generated index images, cewe2pdf logs an error or warning respectively.

### PDF navigation and links

Page labels are available independently of indexing: readers can show `Cover`,
editable content-page numbers, or spread labels such as `2-3` after a double-page
selection. Indexing additionally supplies bookmarks under `Contents` and clickable
index rows pointing to actual output pages.

Literal `http://` and `https://` addresses in ordinary text become clickable links,
retaining their editor colour and typography, including wrapped addresses.
Optional photograph-location links and document title/author values are configured
in [PDF_GEO_LINKS and PDF_METADATA](#cewe2pdfini).

These features depend on reader support. They do not change printed appearance.

### Calendars

Basic CEWE wall-calendar layouts are supported: the year and month headings,
the `OneWeekPerRow` month grid, and the landscape `OneRow` strip.  CEWE stores
only the chosen layout name in the MCF; the base sizes, alignment, borders and
padding for its individual cells are defined by the installation's
`Resources/calendar_layout.xml`.  The MCF's `fontsize_percentage` and
`fontsize_percentage_holiddays` values are adjustments to those fixed point
sizes, not sizes derived from the edited calendar rectangle.

Without a CEWE installation, unsupported calendar layouts fall back to the
built-in defaults where possible.  A project can also provide compatible local
definitions and map editor names to them in an optional `[CALENDAR]` section:

```
[CALENDAR]
layoutSubstitutions =
    OneWeekPerRow (2), my-local-week-grid
schemaSubstitutions =
    editor-colours, my-local-colours
```

The local layout and colour resources use the same filenames and XML shape as
CEWE's files, under `Resources/`.  This is primarily useful for regression
tests and for deliberately self-contained calendar projects.


## Acceptable products
The program was developed to handle CEWE photo books - photograph albums - and
is absolutely **not** guaranteed to handle every other product from the same
editor.  Calendars have the limited support described above; cards and
invitations are still unlikely to create the right result and may fail.

CEWE Photo Pairs (MEM3) is explicitly supported. The resulting 6x6cm pages can be printed using Acrobat, using multiple sheets to a page with, for example, 4 across and 6 down on an A4 sheet. Print two copies, glue them to carton, cut them out and you have your memory game.

## Using the program
You should now have

* a program directory containing all the python code needed, the most important being `cewe2pdf.py`.
* one or more album directories each containing
  - one or more `*.mcf` or `.mcfx` album files
    * a directory named `<album>_mcf-Dateien` for each album, if you are using `*.mcf`
  - optionally, a `cewe2pdf.ini` configuration file
  - optionally, an `additional_fonts.txt` configuration file

It is not really a good idea to place your album files in the same directory as the program. Keep them separate so there is no confusion in keeping your version of the program up to date with your Github repository version.

### Usage

Run `cewe2pdf.py` with the name of your album file and an equivalent pdf file will be created beside the album file.
Example:
```
python cewe2pdf.py c:\path\to\my\files\my_nice_fotobook.mcf
```
### Command line options

Run `python cewe2pdf.py --help` for the current arguments. Common options are:

| Option | Purpose |
| --- | --- |
| `--keepDoublePages` | Keep each album spread together rather than splitting it into individual PDF pages |
| `--pages cover,1-12,15` | Render selected editable content pages and covers |
| `--outFile output.pdf` | Choose the output filename |
| `--tmp-dir directory` | Choose the MCFX extraction directory |
| `--appdata-dir directory` | Choose persistent application data storage |
| `--version` | Show program version and available Git build identification |
| `--install`, `--uninstall` | Manage the Windows executable's Explorer command; see the [build/integration guide](documents/build_a_compiled_version.md#windows-explorer-installation-and-use) |

### Selecting pages

`--pages` accepts positive editable content-page numbers, inclusive ranges, and `cover`,
for example `--pages cover,1-12,15`. CLI zero is rejected. For albums, `cover` selects
both outer covers in single-page output or their complete spread in double-page output.

With `--keepDoublePages`, selecting either member selects the complete physical spread.
Page 1 includes its front endpaper; the final content page includes its back endpaper.
Duplicate requests are rendered once, in natural album order.
Calendar `cover` selects the front cover; Photo Pairs has no cover and rejects it.

## Development

Use the [developer guide](documents/DEVELOPER_GUIDE.md) for architecture, dependency
maintenance, logging, linting, and version numbering.
[Project context](documents/PROJECT_CONTEXT.md) explains non-obvious implementation choices;
[AGENTS.md](AGENTS.md) gives coding assistants the working conventions.
The [test guide](tests/README.md) owns test execution, fixture approval, comparison, and cleanup.

### Standalone executable

The project does not publish executable releases. For a private build, use the
[Windows/Linux build guide](documents/build_a_compiled_version.md).
It also explains [Windows Explorer installation and use](documents/build_a_compiled_version.md#windows-explorer-installation-and-use).
Source environment setup remains in [Install](#install).

### Cleaning up temporary files

Follow the [test-output cleanup procedure](tests/README.md#cleaning-up-temporary-files).
It owns the current discovery patterns and reviewed removal steps.
