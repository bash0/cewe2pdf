cewe2pdf
========

A python script to turn cewe photobooks into pdf documents.
The CEWE pdf export is achieved by interpreting the mcf xml-files 
and compiling a pdf document which looks like the cewe photo book.

There are many unsupported options, so an exact conversion cannot be guaranteed.

tags: mcf2pdf, mcf_to_pdf, CEWE Fotobuch als pdf speichern, Fotobuch nach pdf exportieren, cewe Fotobuch pdf, mcf in pdf umwandeln, aus CEW-Fotobuch ein pdf machen, cewe Fotobuch pdf


Install - Windows
-----------------
Install a Anaconda Python with the newest Python 3 version.

Press Windows Start button and start the "Anaconda prompt"

Make sure you have all the dependencies installed by executing:
```
conda install lxml reportlab pillow
```

Go to the directory where cewe2pdf is installed and create a text file there with filname ``cewe_folder.txt``
and use a text editor to write the installation directory of the CEWE software into the text file.
Example
if you have the software branded for the company DM, called "dm-Fotowelt", then this path will be:
```
C:\Program Files\dm\dm-Fotowelt\dm-Fotowelt.exe
```
Save the file and close it.

Create a nother text file called ``additional_fonts.txt``, but leave it empty.

Install - Linux
---------------

Copy the script where your album is (`*.mcf` file)

Ensure the python dependancies are installed.

On Fedora :
```
sudo dnf install python2-lxml python2-reportlab
```

Define the CEWE path (the directory where your CEWE album software is - you can recognize it with the many `.so` files and some subdirs like `Resources`). Put it into a file named `cewe_folder.txt`.

Example with my CEWE software in /opt/CEWE :
```
echo "/opt/CEWE" > cewe_folder.txt
```

Define some additionnal fonts (`name = /path/to/file.ttf`) into a file named `additionnal_fonts.txt`

This will create an empty file :
```
touch additionnal_fonts.txt
```

You can edit additionnal_fonts.txt and add the fonts you want.

Install - continued
-------------------

At this point, you should have these files in your current directory :
* `cewe2pdf.py`
* `cewe_folder.txt`
* `additionnal_fonts.txt`
* your `*.mcf` file
* a directory named `<album>_mcf-Datein`

How to use
----------

Just run `cewe2pdf.py` and you will find a new pdf file to appear in your current directory.
Example:
```
   python cewe2pdf.py c:\path\to\my\files\my_nice_fotobook.mcf
```
Development
-----------
To create a stand-alone compiled package, you can use
```
pip install pyinstaller
pyinstaller cewe2pdf.py --onefile
```