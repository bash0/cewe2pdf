# The beginning of a collection of file system related utilities which do not really
# belong in the main code file

import fnmatch
import logging
import os
import re
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


def localfont_dir():
    # Get OS specific directory for locally installed fonts.
    if sys.platform.startswith("win"):
        # Microsoft Windows
        os_path = getenv("LOCALAPPDATA") + "/Microsoft/Windows/Fonts/"
    elif sys.platform.startswith("darwin"):
        # Mac and several others
        os_path = "~/Library/Fonts"
    else:
        # Assume Linux
        os_path = getenv("XDG_DATA_HOME", "~/.local/share") + "/fonts"

    # join with cewe2pdf dir
    return Path(os_path).expanduser()


def systemfont_dirs():
    """Return the standard shared font directories for this platform.

    These directories are intentionally not searched unless the caller has an
    explicit configuration option for that purpose: system fonts vary between
    computers and can change PDF output.
    """
    if sys.platform.startswith("win"):
        windowsDirectory = getenv("WINDIR", r"C:\\Windows")
        return (Path(windowsDirectory) / "Fonts",)
    if sys.platform.startswith("darwin"):
        return (Path("/Library/Fonts"), Path("/System/Library/Fonts"))
    return (Path("/usr/local/share/fonts"), Path("/usr/share/fonts"))


# locate files in a directory with a pattern, with optional case sensitivity
# and the optional ability to walk the structure below the provided directory
# eg: findFilesInDir(fontdir, '*.ttf')
def findFilesInDir(dirpath: str, glob_pat: str, ignore_case: bool = True, walk_structure: bool = False):
    """Return matching files from readable directories below *dirpath*.

    This is a best-effort discovery helper: inaccessible directories are
    logged and skipped.  A caller which requires a particular directory must
    validate that requirement separately.
    """
    if not os.path.exists(dirpath):
        return []

    rule = re.compile(fnmatch.translate(glob_pat), re.IGNORECASE) if ignore_case \
        else re.compile(fnmatch.translate(glob_pat))

    dirnames = [dirpath]
    if walk_structure:
        for p, ds, fs in os.walk(dirpath): # pylint: disable=unused-variable
            for d in ds:
                dirnames.append(os.path.join(p,d))

    filelist = []
    for directory in dirnames:
        try:
            filenames = os.listdir(directory)
        except OSError as error:
            logging.warning(f"Could not scan directory '{directory}'; skipping it: {error}")
            continue
        filelist.extend(os.path.join(directory, n) for n in filenames if rule.match(n))

    return filelist

def findFileInDirs(filenames, paths):
    if not isinstance(filenames, list):
        filenames = [filenames]
    for filename in filenames:
        for p in paths:
            testPath = os.path.join(p, filename)
            if os.path.exists(testPath):
                return testPath

    complaint = f"Could not find {filenames} in {', '.join(paths)} paths"
    logging.debug(complaint)
    raise ValueError(complaint)


def findFileByExtInDirs(filebase, extList, paths):
    for p in paths:
        for ext in extList:
            testPath = os.path.join(p, filebase + ext)
            if os.path.exists(testPath):
                return testPath
    prtStr = f"Could not find {filebase} [{' '.join(extList)}] in paths {', '.join(paths)}"
    logging.info(prtStr)
    raise ValueError(prtStr)
