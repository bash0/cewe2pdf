cewe2pdf
========

A python script to turn cewe photobooks into pdf documents. The CEWE pdf export is achieved by interpreting the mcf xml-files and compiling a pdf document which looks exactly like the cewe photo book.

tags: mcf2pdf, mcf_to_pdf, CEWE Fotobuch als pdf speichern, Fotobuch nach pdf exportieren, cewe Fotobuch pdf, mcf in pdf umwandeln, aus CEW-Fotobuch ein pdf machen, cewe Fotobuch pdf

Install
-------

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

At this point, you should have those files in your current directory :
* `cewe2pdf.py`
* `cewe_folder.txt`
* `additionnal_fonts.txt`
* your `*.mcf` file
* a directory named `<album>_mcf-Datein`

How to use
----------

Just run `cewe2pdf.py` and you will find a new pdf file to appear in your current directory.

