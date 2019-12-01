# test to convert a simple mcf to pdf
#if you run this file directly, it won't have access to parent folder, so add it to python path
import sys
sys.path.append('..')
sys.path.append('.')
from pathlib import Path
import os, os.path

from cewe2pdf import convertMcf

def test_simpleBook():
    inFile = str(Path(Path.cwd(), 'tests', 'unittest_fotobook.mcf'))
    outFile = str(Path(Path.cwd(), 'tests', 'unittest_fotobook.mcf.pdf'))
    os.remove(outFile)
    assert os.path.exists(outFile) == False
    convertMcf(inFile)
    assert Path(outFile).exists() == True
    os.remove(outFile)

if __name__ == '__main__':
    #only executed when this file is run directly.
    test_simpleBook()