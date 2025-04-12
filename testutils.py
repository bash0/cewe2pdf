import glob
import os
import os.path

from pathlib import Path

def getLatestResultFile(albumFolderBasename, pattern: str) -> str:
    resultpdfpattern = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", 'previous_result_pdfs', pattern))
    resultpdffiles = glob.glob(resultpdfpattern)
    # I used to sort on the modification date in order to find the latest file:
    #   resultpdffiles.sort(key=os.path.getmtime, reverse=True)
    # but that doesn't work when we run automated tests on github machines. So
    # I guess we'll just have to rely on the naming convention:
    resultpdffiles.sort(key=os.path.basename, reverse=True)
    return resultpdffiles[0] if len(resultpdffiles) > 0 else None
