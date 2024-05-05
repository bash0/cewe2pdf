cewe2pdf
========

A python script to turn cewe photobooks into pdf documents.
The CEWE pdf export is achieved by interpreting the mcf xml-files
and compiling a pdf document which looks like the cewe photo book.

There are many unsupported options, so an exact conversion cannot be guaranteed. The script is mostly based on reverse-engineering and guessing. It is not meeting any official specifications. So don't be surprised if one or another feature doesn't work. However, improvements are always appreciated.

You will need underlying Cairographics (<https://www.cairographics.org/>) support installed on your machine for the handling of clip art. How you get this will depend on your platform, but if you have the GTK+ toolkit installed (<https://www.gtk.org/docs/installations/>) that should do it. An alternative way to get Cairo installed is to use vcpkg (https://learn.microsoft.com/en-gb/vcpkg/get_started/overview and https://vcpkg.io/en/)

tags: mcf2pdf, mcf_to_pdf, CEWE Fotobuch als pdf speichern, Fotobuch nach pdf exportieren, cewe Fotobuch pdf, mcf in pdf umwandeln, aus CEW-Fotobuch ein pdf machen, cewe Fotobuch pdf

Install - Windows
-----------------

Download or clone this cewe2pdf repository into a folder of your choice.

The easiest way to start this Python script, is to install the latest python version.
Then from the start-menu open your python promt and install the dependencies

```
pip install lxml reportlab pillow cairosvg fonttools pyyaml
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

There does not appear to be a "binaries only" installation for GTK+ or Cairographics, which means you'll have to build it yourself.

Install - Windows (continued)
-----------------------------

Go to the directory where cewe2pdf is installed and create a text file there with filename ``cewe_folder.txt``
and use a text editor to write the installation directory of the CEWE software into the text file.
Example
if you have the software branded for the company DM, called "dm-Fotowelt", then the file ``cewe_folder.txt`` should contain:

```
C:\Program Files\dm\dm-Fotowelt\dm-Fotowelt.exe
```

Save the file and close it.

Alternatively - indeed, preferably, if you want full functionality - you can move on to more extensive configuration by using ``cewe2pdf.ini`` instead of ``cewe_folder.txt``. Here you can specify the location of the cewe folder, provide a comma separated list of locations for additional background images and define how the additional fonts you have specified (see below) are organised into families so that bold and italic texts are shown correctly.
The contents can, for example, be of the form:

```
[DEFAULT]
cewe_folder = C:\Program Files\Elkjop fotoservice_6.3\elkjop fotoservice
extraBackgroundFolders =
 C:/ProgramData/hps/5026/addons/447/backgrounds/v1/backgrounds
 C:/ProgramData/hps/5026/addons/448/backgrounds/v1/backgrounds
fontFamilies =
 Bodoni,Bodoni,BodoniB,BodoniI,BodoniBI
```

Install - MacOS
---------------

Download the repository into a folder of your choice.

Install the packages listed in `requirements.txt` into a Python environment.

Install `cairo`, for example using the `brew` package manager. If you dont have `brew`installed, please do so [https://brew.sh/](https://brew.sh/). Then run

```
brew install cairo
```

as shown here [https://formulae.brew.sh/formula/cairo](https://formulae.brew.sh/formula/cairo).

Follow the steps outlined for Linux on linking to the software (most likely it will be installed in `/Applications`) and creating the font file. The standard directory for fonts on MacOS is `~/Library/Fonts/`.

Install - Linux
---------------

Download the repository into a folder of your choice.

Ensure the python dependencies are installed.

On Fedora :

```
sudo dnf install python3-lxml python3-reportlab python-cairosvg fonttools python3-pyyaml
```

On Debian:
```
sudo apt install python3-cairosvg python3-fonttools python3-lxml python3-packaging python3-pillow python3-reportlab python3-yaml
```

Define the CEWE path (the directory where your CEWE album software is installed. You can recognize it by the many `.so` files and some subdirs like `Resources`). Put this directory name into a file named `cewe_folder.txt`.

Example with my CEWE FOTOWELT is installed in /home/username/CEWE/CEWE FOTOWELT/ :

```
echo "/home/username/CEWE/CEWE FOTOWELT/" > cewe_folder.txt
```

Example with my CEWE software in /opt/CEWE :

```
echo "/opt/CEWE" > cewe_folder.txt
```

Install - additional_fonts.txt
------------------------------

Create another text file called ``additional_fonts.txt``.
This can be left empty, but to get the correct fonts in the pdf you should specify them here.

Add single font files or whole directories with `.ttf` files in it:

Windows font file and directory paths:

```
C:\Windows\Fonts\BOD_R.TTF
C:\Windows\Fonts\
```

Example for linux font file and directory paths:

```
/usr/share/fonts/truetype/lato/Lato-Heavy.ttf
/home/myusername/.local/share/fonts/
```

This will create an empty file :

```
touch additional_fonts.txt
```

.xmcf Files
-----------

If your CEWE software uses `.xmcf` files for your projects, you can simply still use this. The `.xmcf` file format is just an archive of the `*.mcf` file, the `<album>_mcf-Dateien` folder and a few other files. Right click the `.xmcf` file and your os should give you an open to open the archive. Copy the relevant files out of it, and you should be all set for the next steps.

.mcfx Files
-----------

If your CEWE software (probably from about 7.3.x onwards) uses `.mcfx` files to store the album, you can still use this. The `.mcfx` file format packs the `*.mcf` file, the content of the `<album>_mcf-Dateien` folder and a few other files into a single database file. You can unpack those for yourself (see the notes in issue https://github.com/bash0/cewe2pdf/issues/119) or you can instead simply use "Save as" in the album editor to save to the .mcf format which cewe2pdf can use.

Install - continued
-------------------

At this point, you should have these files in your current directory :

* `cewe2pdf.py`
* `cewe_folder.txt`
* `additional_fonts.txt`
* your `*.mcf` file
* a directory named `<album>_mcf-Datein`

How to use
----------

Just run `cewe2pdf.py` and you will find a new pdf file to appear in your current directory.
Example:

```
   python cewe2pdf.py c:\path\to\my\files\my_nice_fotobook.mcf
```

Options
-------

currently cewe2pdf supports the following options. They are shown if you run

```python cewe2pdf.py --help```

```
usage: cewe2pdf [-h] [--keepDoublePages] [inputFile]

Convert a foto-book from .mcf file format to .pdf

positional arguments:
  inputFile          the mcf input file. If not given, the first .mcf in the
                     current directory is used. (default: None)

optional arguments:
  -h, --help         show this help message and exit
  --keepDoublePages  Each page in the .pdf will be a double-sided page,
                     instead of a normal single page. (default: False)

Example:
   python cewe2pdf.py c:\path\to\my\files\my_nice_fotobook.mcf

```

Development
-----------

To create a stand-alone compiled package, you can use

```
pip install pyinstaller
pyinstaller cewe2pdf.py --onefile
```

To run the unit-test you also need to install

```
pip install pytest pdfrw
```

You can then call pytest from the working directory or use the runAllTests.py file.
