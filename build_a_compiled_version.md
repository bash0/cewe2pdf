# Building a "compiled" cewe2pdf.exe
Python calls this freezing instead of compiling. So the cewe2pdf is freezed.

## Method 1: using pyinstaller

Reference: https://pyinstaller.org/en/stable/

    conda install pyinstaller
    pyinstaller cewe2pdf.py

This creates quite a lot of output, including warnings and even tracebacks from exceptions, but don't worry - it will generate two directories (build and dist). The final .exe is located in dist/cewe2pdf. But it does not work yet.

1. Create the folowing directories:
    - dist/cewe2pdf/cssselect2
    - dist/cewe2pdf/cairocffi
    - dist/cewe2pdf/cairosvg
    - dist/cewe2pdf/tinycss2

2. Go to your anaconda3\Lib\site-packages\ folder and copy the VERSION files into the respective folder you created in the last step.

3. Copy the following files from C:\\...\anaconda3\Library\bin to dist\cewe2pdf:
    - cairo.dll
    - zlib1.dll
    - libpng16.dll
    - freetype.dll
    - fontconfig.dll
    - bz2.dll
    - expat.dll
    - libcharset.dll
    - libiconv.dll
    - api-ms-win-crt-runtime-l1-1-0.dll 
    - api-ms-win-crt-heap-l1-1-0.dll
    - api-ms-win-crt-stdio-l1-1-0.dll
    - api-ms-win-crt-string-l1-1-0.dll
    - api-ms-win-crt-convert-l1-1-0.dll
    - api-ms-win-crt-utility-l1-1-0.dll
    - api-ms-win-crt-math-l1-1-0.dll
    - api-ms-win-crt-locale-l1-1-0.dll
    - api-ms-win-crt-time-l1-1-0.dll
    - api-ms-win-crt-environment-l1-1-0.dll
    
    Actually this description may well be a bit simplified. What you're looking for is cairo.dll and all its dependencies, and those might not be in the anaconda bin directory. You might, for example, have used the github vcpkg (https://github.com/microsoft/vcpkg?tab=readme-ov-file#quick-start-windows) to install cairo, thereby adding e.g. D:\Users\xxxx\Source\GitHub\vcpkg\installed\x64-windows\bin to the path. To find the cairo dependencies you can then run:
        
    "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin\dumpbin.exe" /dependents D:\Users\xxxx\Source\GitHub\vcpkg\installed\x64-windows\bin\cairo.dll
    
    An alternative dependencies tool is the modern Dependencies program, see https://github.com/lucasg/Dependencies?tab=readme-ov-file

    Unfortunately these static dependency analysis programs will still not find all the dependencies, because some are dynamically loaded. One way to discover the full list is to load the constructed cewe2pdf.exe into Visual Studio and run it (which should work ok because the cairo stuff will be in the path on your development machine!) Then you can examine the Output window to discover which dlls were loaded.

4. Make sure (done near the top of cewe2pdf.py) the current directory is added to the os.environ["PATH"]. This must happen before cairosvg is first imported from clpFile.py

5. Start dist\cewe2pdf\cewe2pdf.exe to see if it starts without error.
   
6. Remember that you will need a **cewe2pdf.ini** file next to your .mcf file. And maybe an **additional_fonts.txt** and a **loggerconfig.yaml** file.

## Method 2: py2exe
    pip install py2exe

then run the installer script

    python setup.py install

The result .exe will have a problem: it can't load the cairocffi._generated folder.
To fix this, you need to go to your Anaconda install path, under: `anaconda3\Lib\site-packages\cairocffi\_generated`

and create an empty file called: `__init__.py`
This file will help py2exe to recognize this package and include it.

Then there will be problems finding VERSION from cairosvg, cairoffi, cssselect2, tinycss2.
The error from cairosvg can be solved by copying the VERSION file to to the dist folder, but the error fro cairocffi indicates, that it searches for the file inside the .zip file. But you can't modify the zip file, otherwise the .exe won't start.
So needs to be patched in the libraries.
