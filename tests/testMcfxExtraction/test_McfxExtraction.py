# following the pattern established by BarchSteel ...

# This test is in its own directory, so it can have it's own configuration files if it needs them
# Also we can store the asset files here.

# Test the unpacking of a .mcfx file to a .mcf file and the associated image files

#if you run this file directly, it won't have access to parent folder, so add it to python path
import sys
sys.path.append('..')
sys.path.append('.')
from pathlib import Path
import os, os.path
import filecmp
import logging

from mcfx import unpackMcfx

def delete_outdir(fulldirpath):
    if not os.path.exists(fulldirpath):
        return
    if not os.path.isdir(fulldirpath):
        # weird, but assume it was a mistakenly created file of this name
        os.remove(fulldirpath)
        return
    files = os.listdir(fulldirpath)
    for file in files:
        # then we have to delete the files first
        os.remove(os.path.join(fulldirpath, file))
    os.rmdir(fulldirpath)

def test_mcfxExtraction():
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    inPath = Path(Path.cwd(), 'tests', 'testMcfxExtraction', 'testMcfxExtraction.mcfx')
    outdirPath = Path(Path.cwd(), 'tests', 'testMcfxExtraction', 'tmp-dir')
    delete_outdir(outdirPath)

    unpackedFolder, mcfxmlname = unpackMcfx(inPath, outdirPath)

    assert unpackedFolder is None # since we are providing an outdir
    assert str(mcfxmlname) == os.path.join(str(outdirPath), "data.mcf") # the mcf is always called data.mcf!

    # At this point we could usefully compare data.mcf with McfOriginals/testMcfxExtraction.mcf but it's not
    # easy because the XML contains some "session" data, like the lastTextFormat used tag, the folder id, some
    # statistical stuff, and so on. And sometimes the Cewe editor just seems to be a bit random about the order
    # in which it stores, e.g., alignment attributes. Something to add in the next round ...

    # check that all the (image) files from the checked-in mcf version are present in the newly unpacked mcfx folder
    mcfdateienPath = Path(Path.cwd(), 'tests', 'testMcfxExtraction', 'McfOriginals', 'testMcfxExtraction_mcf-Dateien')

    # I'd like to use this:
    #   dcmp = filecmp.dircmp(mcfdateienPath, outdirPath, ignore=('folderid.xml'))
    # but can't make it work
    errorCount = 0
    for originalFileBaseName in os.listdir(mcfdateienPath):
        if originalFileBaseName == 'folderid.xml':
            continue # this is always different
        originalFile = os.path.join(mcfdateienPath, originalFileBaseName)
        mcfxFile = os.path.join(outdirPath, originalFileBaseName)
        if os.path.exists(mcfxFile):
            if not filecmp.cmp(originalFile, mcfxFile):
                print(f"{originalFileBaseName} found but not equal")
                errorCount += 1
        else:
            print(f"{originalFileBaseName} not found")
            errorCount += 1

    assert errorCount == 0


if __name__ == '__main__':
    #only executed when this file is run directly.
    test_mcfxExtraction()