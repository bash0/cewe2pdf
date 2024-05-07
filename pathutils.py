# The beginning of a collection of file system related utilities which do not really
# belong in the main code file

import sys
from os import getenv
from pathlib import Path

def appdata_dir():
    r"""
    Get OS specific appdata directory path for cewe2pdf.
    Typical user data directories are:
        macOS:    ~/Library/Application Support/cewe2pdf
        Unix:     ~/.local/share/cewe2pdf   # or in $XDG_DATA_HOME, if defined
        Win 10:   C:\Users\<username>\AppData\Local\cewe2pdf
    :return: full path to the user-specific data dir
    """
    # get os specific path
    if sys.platform.startswith("win"):
        os_path = getenv("LOCALAPPDATA")
    elif sys.platform.startswith("darwin"):
        os_path = "~/Library/Application Support"
    else:
        # linux
        os_path = getenv("XDG_DATA_HOME", "~/.local/share")

    # join with cewe2pdf dir
    path = Path(os_path) / "cewe2pdf"
    return path.expanduser()
