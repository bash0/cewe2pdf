# This test needs to be in its own directory, so it can have it's own cwew2pdf.ini.
# Also we can store the asset files here.

# Test the default substitution for missing fonts

# Bootstrap the project root so this test can also run directly.
import logging
import os, os.path
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from testutils import configureTestImportPaths
configureTestImportPaths(__file__)
from datetime import datetime
from pikepdf import Pdf

from compare_pdf import ComparePDF, ShowDiffsStyle # type: ignore
from cewe2pdf import convertMcf # type: ignore

from testutils import getLatestResultFile


def tryToBuildBook(inFile, outFile, latestResultFile, keepDoublePages, expectedPages):
    if os.path.exists(outFile) == True:
        os.remove(outFile)
    assert os.path.exists(outFile) == False
    convertMcf(inFile, keepDoublePages, outputFileName=outFile)
    assert Path(outFile).exists() == True

    #check the pdf contents
    # we could also test more sophisticated things, like colors or compare images.
    readPdf = Pdf.open(outFile)
    numPages =  len(readPdf.pages)
    assert numPages == expectedPages, f"Expected {expectedPages} pages, found {numPages}"

    if latestResultFile is not None:
        # compare our result with the latest one
        print(f"Compare {outFile} with {latestResultFile}")
        files = [outFile, latestResultFile]
        compare = ComparePDF(files, ShowDiffsStyle.Nothing)
        result = compare.compare()
        assert result, "Pixel comparison failed"
    else:
        print(f"No result file to compare with")

    #os.remove(outFile)
    return numPages


def defineCommonVariables():
    albumFolderBasename = 'testTextBox'
    albumBasename = "testTextBox"
    inFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", f'{albumBasename}.mcf'))
    yyyymmdd = datetime.today().strftime("%Y%m%d")
    return albumFolderBasename,albumBasename,inFile,yyyymmdd

def test_testfontsubstitution(main=False):
    albumFolderBasename, albumBasename, inFile, yyyymmdd = defineCommonVariables()
    styleid = "S"
    if (main):
        # use an undated output file name when running as main rather than via pytest
        outFileBasename = f'{albumBasename}.mcf.pdf'
    else:
        outFileBasename = f'{albumBasename}.mcf.{yyyymmdd}{styleid}.pdf'
    outFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", outFileBasename))
    latestResultFile = getLatestResultFile(albumFolderBasename, f"*{styleid}.pdf")
    tryToBuildBook(inFile, outFile, latestResultFile, False, 28)


def test_textBoxWithoutCeweWithLocalFonts(caplog):
    """A standalone album renders with a deliberately empty cewe_folder in the ini file.

    This is intentionally a smoke test rather than a pixel comparison: the
    local-font folder is allowed to vary between users.  An empty local
    additional_fonts.txt prevents the repository's sample definitions from
    contributing any fonts, leaving only normal local-font discovery.
    """
    sourceFolder = PROJECT_ROOT / 'tests' / 'testTextBox'
    caplog.set_level(logging.INFO)

    with TemporaryDirectory() as temporaryDirectory:
        temporaryAlbumFolder = Path(temporaryDirectory) / 'testTextBox'
        temporaryAlbumFolder.mkdir()
        shutil.copy2(sourceFolder / 'testTextBox.mcf', temporaryAlbumFolder)
        shutil.copytree(sourceFolder / 'testTextBox_mcf-Dateien',
                        temporaryAlbumFolder / 'testTextBox_mcf-Dateien')
        (temporaryAlbumFolder / 'cewe2pdf.ini').write_text(
            '[DEFAULT]\ncewe_folder = \n', encoding='utf-8')
        (temporaryAlbumFolder / 'additional_fonts.txt').touch()

        outputFile = temporaryAlbumFolder / 'standalone-textbox.pdf'
        originalWorkingDirectory = Path.cwd()
        originalIgnoreLocalFonts = os.environ.pop('IGNORELOCALFONTS', None)
        try:
            os.chdir(temporaryAlbumFolder)
            assert convertMcf(str(temporaryAlbumFolder / 'testTextBox.mcf'), False,
                              outputFileName=str(outputFile))
        finally:
            os.chdir(originalWorkingDirectory)
            if originalIgnoreLocalFonts is not None:
                os.environ['IGNORELOCALFONTS'] = originalIgnoreLocalFonts

        assert outputFile.exists()
        with Pdf.open(outputFile) as readPdf:
            assert len(readPdf.pages) == 28

    conversionLog = '\n'.join(
        f'{record.levelname} - {record.name} - {record.getMessage()}'
        for record in caplog.records)
    print(f'Standalone textbox conversion log:\n{conversionLog}')

    assert 'CEWE folder deliberately left unspecified' in conversionLog
    assert 'Registering ' in conversionLog


if __name__ == '__main__':
    # When running this test directly we will normally not have IGNORELOCALFONTS set, so the system
    # fonts will be registered and could be accessed (though the mcf file for this test is not supposed
    # to do so). When the tests are run by a full pytest discovery, IGNORELOCALFONTS is set to 1
    # so that the system fonts are not registered (not on the developer machine nor on the github servers)

    # First the normal direct pixel-comparison run.
    test_testfontsubstitution(main=True)

    # Then run the cewe missing smoke test through pytest so its caplog fixture can display the log.
    # This produces a confusing message about skipping the other test, but it is harmless.
    pytest.main([__file__, '-k', 'test_textBoxWithoutCeweWithLocalFonts', '-s'])
