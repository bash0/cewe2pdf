import glob
import os, os.path

from pathlib import Path

def getLatestResultFile(albumFolderBasename, pattern : str)-> str:
    resultpdfpattern = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", 'previous_result_pdfs', pattern))
    resultpdffiles = glob.glob(resultpdfpattern)
    resultpdffiles.sort(key=os.path.getmtime, reverse=True)
    return resultpdffiles[0] if len(resultpdffiles) > 0 else None
