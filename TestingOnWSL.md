Testing the program on Linux using a Windows PC
===============================================

Getting the program to work on Windows is one thing - but it would be nice to be able to ensure that it still works ok on Linux.

Microsoft provides a way to execute Linux on a Windows machine, the [Windows Subsystem for Linux](https://learn.microsoft.com/en-us/windows/wsl/install).
Once WSL is installed we must create the Python environment (TBD, I forgot to make notes while I did this)
- open a shell window
- install Python
- run pip install -r  requirements.txt

When Python and our requirements are in place then we must change the cewe2pdf configuration to know where the (Windows) Cewe stuff is when it is accessed using the Linux file system. (I have not tried to install Cewe on the WSL Ubuntu subsystem. Since we don't need the executables, just the data for backgrounds, cliparts etc., it seems better to use exactly the same files as have been used in the Windows testing on the same machine)

The _cewe2pdf.ini_ file needs updates, for example:
- `cewe_folder = /mnt/c/Program Files/Elkjop fotoservice_6.3/elkjop fotoservice`<br/>&nbsp;&nbsp;&nbsp;(from C:\Program Files\Elkjop fotoservice_6.3\elkjop fotoservice)
- `hps_folder = /mnt/c/Users/pete/AppData/Local/CEWE/hps`<br/>&nbsp;&nbsp;&nbsp;(previously found via the global environment variable LOCALAPPDATA)

The _additional_fonts.txt_ file needs updates, for example:
- `/mnt/c/windows/fonts/`<br/>&nbsp;&nbsp;&nbsp;(previously C:\Windows\Fonts\)
- `/mnt/c/Users/pete/AppData/Local/Microsoft/Windows/Fonts/`<br/>&nbsp;&nbsp;&nbsp;(downloaded and installed fonts)

And that should do it. In the Linux shell go to the cewe2pdf directory and run it, for example
```
	python3 cewe2pdf.py tests/unittest_fotobook.mcfx
```
