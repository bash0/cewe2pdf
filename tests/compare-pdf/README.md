------

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/Formartha/compare-pdf/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/compare-pdf)](https://pypi.org/project/compare-pdf)
![PyPI - Downloads](https://img.shields.io/pypi/dm/compare-pdf)

PDF Visual Comparison Tool
==========================
This utility compares PDF files visually by converting each page into images and then comparing them using OpenCV.
It is particularly useful for identifying differences between PDF files that may not be apparent through text comparison alone.

Features
--------
*   Compares PDF files visually, page by page.
*   Supports multi-page PDF files.
*   Reports differences between PDF files, specifying the page number and source file.

Requirements
------------
*   Python 3.x
*   PyMuPDF (`fitz`) library
*   OpenCV (`cv2`) library

For detailed requirements, see below.

Installation for local development
------------
1.  Clone the repository:
    
    `git clone https://github.com/Formartha/compare-pdf.git`
    

2.  Install the required dependencies:
    
    `pip install pymupdf opencv-python`
    

Installation for self usage
------------
`pip install compare-pdf`

Usage
-----
```
compare_pdf --pdf <path_to_pdf1> --pdf <path_to_pdf2> ... [--showdiffs={sidebyside|diffimage}]
```

* Replace `<path_to_pdf1>`, `<path_to_pdf2>`, etc. with the paths to the PDF files you want to compare. At least two PDF files are required for comparison.
* The `--showdiffs` option requests the display of differing pages in a window as they are discovered. A diff window is dismissed by typing any character and the processing continues
    * _sidebyside_ places the differing pdf pages horizontally next to each other in the diff window
    * _diffimage_ places an OpenCV absdiff result in the diff window, a white background with non-white pixels showing where the images differed.

The program returns a zero result code when there are no differences, otherwise -1

Example
-------
`compare_pdf --pdf file1.pdf --pdf file2.pdf`

This will compare `full/path/to/file1.pdf` and `full/path/to/file2.pdf` visually, reporting any differences found.

Requirements.txt
----------------
The _requirements.txt_ file specifying exactly which modules are needed in a virtual environenment was generated using the commands below
```
pip3 install pipreqs
pip3 install pip-tools
pipreqs --savepath=requirements.in && pip-compile
```
The result was not perfect, however, so that manual additions were needed:
```
PyMuPDF==1.25.5
setuptools==75.8.0
wheel==0.45.1
```

License
-------
This project is licensed under the MIT License - see the LICENSE file for details.

Useful references
-----------------
* https://stackoverflow.com/questions/31684375/automatically-create-file-requirements-txt/65728461#65728461
* https://codedeepai.com/finding-difference-between-multiple-images-using-opencv-and-python/
