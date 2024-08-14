Testing the program for use on Linux using Windows
==================================================

Getting the program to work on Windows is one thing - but it would be nice to be able to ensure that it still works ok on Linux.
Happily Microsoft provides a way to execute Linux on a Windows machine, see https://learn.microsoft.com/en-us/windows/wsl/install.
Once you have that installed, you can open a shell window and install python (TBD, I forgot to make notes while I did this)

Once Python is available then we must change our cewe2pdf configuration to know where the (Windows) Cewe stuff is (I have not yet tried to install Cewe on my Ubuntu subsystem)

The _cewe2pdf.ini__ file needs updates, for example:
- cewe_folder = /mnt/c/Program Files/Elkjop fotoservice_6.3/elkjop fotoservice (from C:\Program Files\Elkjop fotoservice_6.3\elkjop fotoservice)
- hps_folder = /mnt/c/Users/pete/AppData/Local/CEWE/hps (previously found via the global environment variable LOCALAPPDATA)

The _additionalfonts.txt__ file needs updates, for example:
- /mnt/c/windows/fonts/ (previously c:\windows\fonts\)