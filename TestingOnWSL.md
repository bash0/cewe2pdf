Testing the program on Linux using a Windows PC
===============================================

Getting the program to work on Windows is one thing - but it would be nice to be able to ensure that it still works ok on Linux.

Microsoft provides a way to execute Linux on a Windows machine, the [Windows Subsystem for Linux](https://learn.microsoft.com/en-us/windows/wsl/install).
Once WSL is installed we must create the Python environment (TBD, I forgot to make notes while I did this)
- open a shell window (start psh, run wsl)
- first time, install Python in some way (I used the steps from [here](https://gist.github.com/rutcreate/c0041e842f858ceb455b748809763ddb)), though when I checked the current version it was 3.10 rather than the 3.8 described in the document, so I just stopped there.
  - sudo apt update
  - sudo apt install software-properties-common -y
  - sudo add-apt-repository ppa:deadsnakes/ppa
  - sudo apt update
  - sudo apt install python3.10 python3.10-venv python3.10-dev
  - python3 --version
- install our environment
  - cd /mnt/d/whatever (wherever your cewe2pdf stuff is)
  - pip install -r requirements-pinned.txt

At this point we should be able to run the unit tests, for example
```
	python runAllTests.py
```
which should execute in the same environment as is used for running the python build tests on GitHub, with only our local test resource files being used. The tests should all pass, and the output should be similar to what is seen on Windows.

## Using the Windows Cewe resources and fonts

If you want to use the locallly installed Cewe resources and Windows fonts you must change the cewe2pdf configuration to know where the (Windows) Cewe stuff is when it is accessed using the Linux file system. (I have not tried to install Cewe on the WSL Ubuntu subsystem. Since we don't need the executables, just the data for backgrounds, cliparts etc., it seems better to use exactly the same files as have been used in the Windows testing on the same machine)

The _cewe2pdf.ini_ file needs updates, for example:
- `cewe_folder = /mnt/c/Program Files/Elkjop fotoservice_6.3/elkjop fotoservice`<br/>&nbsp;&nbsp;&nbsp;(from C:\Program Files\Elkjop fotoservice_6.3\elkjop fotoservice)
- `hps_folder = /mnt/c/Users/pete/AppData/Local/CEWE/hps`<br/>&nbsp;&nbsp;&nbsp;(previously found via the global environment variable LOCALAPPDATA)

The _additional_fonts.txt_ file needs updates, for example:
- `/mnt/c/windows/fonts/`<br/>&nbsp;&nbsp;&nbsp;(previously C:\Windows\Fonts\)
- `/mnt/c/Users/pete/AppData/Local/Microsoft/Windows/Fonts/`<br/>&nbsp;&nbsp;&nbsp;(downloaded and installed fonts)

And that should do it. In the Linux shell go to the cewe2pdf directory and run it, for example
```
	python3 cewe2pdf.py tests/unittest_fotobook.mcf
```

## Building the Linux executable version of cewe2pdf
Install the requirements, run the tests, and then build the executable version of cewe2pdf for Linux. 
The following commands should be run in the WSL shell:
```
   pip install -r requirements-pinned.txt
   python runAllTests.py
   python -m pip install pyinstaller==6.22.0
   python -m PyInstaller cewe2pdf.spec --noconfirm --clean
   ./dist/cewe2pdf --version
   ./dist/cewe2pdf --outFile tests/testEmptyPageOne/executable-smoke-linux.pdf   tests/testEmptyPageOne/test_emptyPageOne.mcf
```
