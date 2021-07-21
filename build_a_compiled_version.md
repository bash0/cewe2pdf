# Building a "compiled" cewe2pdf.exe
Pyhton calls this freezing instead of compiling. So the cewe2pdf is freezed.

## Method 1: using pyinstaller

    conda install pyinstaller
    pyinstaller cewe2pdf.py

This will generate two directories (build and dist). The final .exe is located in dist/cewe2pdf. But it does not work yet.

1. Create the folowing directories:
    - dist/cewe2pdf/cssselect2
    - dist/cewe2pdf/cairocffi
    - dist/cewe2pdf/tinycss2

2. Go to your anaconda3\Lib\site-packages\ folder and copy the VERSION files into the respective folder you created in the last step.

3. Copy the VERSION file from anaconda3\Lib\site-packages\cairosvg to dist\cewe2pdf

4. Copy the following files from C:\\...\anaconda3\Library\bin to dist\cewe2pdf:
    - cairo.dll
    - libpng16.dll
    - zlib.dll
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
    
    These is cairo.dll and its dependencies. You can look them up yourself using the dumpbin command from Visual Studio Compiler Tools: 
    
        dumpbin /dependents C:\anaconda3\Library\bin\cairo.dll

5. The program should work now, if not copy all the other files as well from C:\\...\anaconda3\Library\bin to dist\cewe2pdf

6. Make sure that near the top of cewe2pdf.py the current directory is added to the os.environ["PATH"]. This must happen before cairosvg is first imported from clpFile.py

7. start dist\cewe2pdf\cewe2pdf.exe to see if it starts without error

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