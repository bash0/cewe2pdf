# cewe2pdf

A program (a set of python scripts) to turn cewe photobooks into pdf documents.
The CEWE pdf export is achieved by interpreting the mcf xml-files
and compiling a pdf document which looks like the cewe photo book.

There are many capabilities in the Cewe album editor which are not supported by `cewe2pdf`, so an exact conversion cannot be guaranteed. The script is mostly based on reverse-engineering and guessing. It is not meeting any official specifications. So don't be surprised if one or another feature doesn't work. However, improvements are always appreciated!

You will need underlying Cairographics (<https://www.cairographics.org/>) support installed on your machine for the handling of clip art. How you get this will depend on your platform, but if you have the GTK+ toolkit installed (<https://www.gtk.org/docs/installations/>) that should do it. 

tags: mcf2pdf, mcf_to_pdf, CEWE Fotobuch als pdf speichern, Fotobuch nach pdf exportieren, cewe Fotobuch pdf, mcf in pdf umwandeln, aus CEW-Fotobuch ein pdf machen, cewe Fotobuch pdf

## Install - Windows

Download or clone this cewe2pdf repository into a folder of your choice.

The easiest way to start this Python script, is to install the latest python version.
Then from the start-menu open your python promt and install the dependencies

```
pip install packages lxml reportlab pillow pillow_heif cairosvg fonttools pyyaml
```

If you have installed the Anaconda Python distribution, there is one catch:
Currently, there is a problem with the pillow image library in Anaconda, that prevents it from loading .webp images on Windows.
This will give the error:
`"image file could not be identified because WEBP support not installed"`.

To fix this, you can do the following steps.

Press Windows Start button and start the "Anaconda prompt"

Make sure you have all the dependencies installed by executing:

```
conda install lxml
conda uninstall reportlab pillow
pip install reportlab pillow fonttools pyyaml
```

For Windows you can avoid the need to build Cairo graphics yourself by using vcpkg (https://learn.microsoft.com/en-gb/vcpkg/get_started/overview and https://vcpkg.io/en/). 
For users just seeking a 'cairo.dll' to add to %WINDIR%\System32, you could also take a look at [this project](https://github.com/preshing/cairo-windows) for binary releases.

## Install - MacOS

Download the repository into a folder of your choice.

Install the packages listed in `requirements.txt` into a Python environment.

Install `cairo`, for example using the `brew` package manager. If you dont have `brew`installed, please do so [https://brew.sh/](https://brew.sh/). Then run

```
brew install cairo
```

as shown here [https://formulae.brew.sh/formula/cairo](https://formulae.brew.sh/formula/cairo).

Follow the steps outlined for Linux on linking to the software (most likely it will be installed in `/Applications`) and creating the font file. The standard directory for fonts on MacOS is `~/Library/Fonts/`.

## Install - Linux

Download the repository into a folder of your choice. Ensure the python dependencies are installed.
On Fedora :
```
sudo dnf install python3-lxml python3-reportlab python-cairosvg fonttools python3-pyyaml
```
On Debian:
```
sudo apt install python3-cairosvg python3-fonttools python3-lxml python3-packaging python3-pillow python3-reportlab python3-yaml
```
Locate the directory where your CEWE album software is installed. You can recognize it by the many `.so` files and some subdirs like `Resources`).
Put this directory name into a configuration file ``cewe2pdf.ini`` (or, I guess, the now deprecated ``cewe_folder.txt``)

## Configuration files

### cewe2pdf.ini
If a ``cewe_folder.txt`` (see below) file is not found, then the program looks for files called ``cewe2pdf.ini``, first in the current directory and then in the album directory, reading both if it finds both. Later entries override previous entries of the same name. 

For normal use (i.e. actually creating a pdf album, rather than testing the code) the most reasonable strategy is to place a ``cewe2pdf.ini`` file with the album file, setting everything you need there, out of the way of future updates to the program repository.

In ``cewe2pdf.ini`` you **must** specify the location of the cewe folder. You can also
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

# Define line scale (line spacing, essentially) for fonts where the default 1.1 (110%) is not acceptable
fontLineScales =
	Crafty Girls: 1.43

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

### additional_fonts.txt
The code knows where to find the fonts delivered with the Cewe software, but if you use non-Cewe fonts then you must specify the location of those fonts. For historical reasons configuration of fonts is done with a separate (optional) configuration file, ``additional_fonts.txt``. The file should contain one line per font file or font directory to be added. Both `.ttf` or `.otf` files are read.

To find a potential ``additional_fonts.txt`` the code searches, in order, the album directory, the current directory and the location of the program itself; it uses only the **first** such file found.

For normal use (i.e. actually creating a pdf album, rather than testing the code) the most reasonable strategy is to place an ``additional_fonts.txt`` file with the album file, out of the way of future updates to the program repository. You can prevent the program from using fonts defined in the code repository versions of the file by providing an empty ``additional_fonts.txt`` next to your album file.

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

## Using the program
You should now have 

* a program directory containing all the python code needed, the most important being `cewe2pdf.py`.
* one or more album directories each containing
  - one or more `*.mcf` or `.mcfx` album files
    * a directory named `<album>_mcf-Datein` for each album, if you are using `*.mcf`
  - a `cewe2pdf.ini` configuration file (or maybe the now deprecated `cewe_folder.txt`)
  - an `additional_fonts.txt` configuration file

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
usage: cewe2pdf.py [-h] [--keepDoublePages] [--pages PAGES] [--tmp-dir MCFXTMPDIR] [--appdata-dir APPDATADIR]
                   [inputFile]

Convert a photo-book from .mcf/.mcfx file format to .pdf

positional arguments:
  inputFile             Just one mcf(x) input file must be specified (default: None)

options:
  -h, --help            show this help message and exit
  --keepDoublePages     Each page in the .pdf will be a double-sided page, instead of a normal single page. (default:
                        False)
  --pages PAGES         Page numbers to render, e.g. 1,2,4-9 (default: None)
  --tmp-dir MCFXTMPDIR  Directory for .mcfx file extraction (default: None)
  --appdata-dir APPDATADIR
                        Directory for persistent app data, eg ttf fonts converted from otf fonts (default: None)

Example:
   python cewe2pdf.py c:\path\to\my\files\my_nice_fotobook.mcf
```

## Development

To create a stand-alone compiled package, you can use
```
pip install pyinstaller
pyinstaller cewe2pdf.py --onefile
```

To run the unit-test you also need to install

```
pip install pytest pikepdf
```

You can then call pytest from the working directory or use the runAllTests.py file.
