# Building a "compiled" cewe2pdf.exe
Python calls this freezing instead of compiling. So the cewe2pdf is freezed.

## Method 1: using pyinstaller

Reference: https://pyinstaller.org/en/stable/

    conda install pyinstaller

Then run
    
    pyinstaller --onefile --workpath "D:\\temp\\cewe2pdf\\build" --distpath "D:\\temp\\cewe2pdf\\dist" cewe2pdf.py

This creates quite a lot of output, but in the end it will generate the two specified directories (build and dist). The resulting single (large!) executable file, **cewe2pdf.exe**, is in the dist directory, you can use this file on other PCs.
Remember that you will need a **cewe2pdf.ini** file next to your .mcf file. And maybe an **additional_fonts.txt** and a **loggerconfig.yaml** file.

NB, previous versions of this description describe at length what *pyinstaller* did not do correctly, and how to remedy the situation.

As of Mar 2024, with the latest versions of everything installed, as shown below, then running pyinstaller as shown above collects everything it needs, all on its own 
- Anaconda 2024.02
    - conda version : 24.1.2
    - python version : 3.11.7.final.0
- all the latest versions of the packages mentioned in requirements.txt
    - fonttools  4.1.0
    - lxml 5.1.0
    - pillow 10.2.0
    - pdfrw 0.4
    - cairosvg 2.7.1
    - pyyaml 6.0.1
- the latest pyinstaller
    - pyinstaller 5.13.2
- a Cairo installation for windows from github vcpkg (in the local PATH)
    - no version, but dated 03/05/2020

