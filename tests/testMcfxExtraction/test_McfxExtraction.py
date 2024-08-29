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

import xml.etree.ElementTree as ET

from mcfx import unpackMcfx

class XmlTree():
    # Credit to https://stackoverflow.com/questions/24492895/comparing-two-xml-files-in-python, with mods

    # def __init__(self):
    # nothing here yet

    def xml_compare(self, x1, x2, tagExcludes=[], attributeExcludes=[]):
        """
        Compares two xml etrees
        :param x1: the first tree
        :param x2: the second tree
        :param tagExcludes: list of string of tags where no attributes are compared
        :param attributeExcludes: list of string of attributes to exclude from comparison
        :return:
            True if both files match
        It would really be MUCH better to have a list of attributes to exclude per listed tag, but this is round 1!
        """

        result = True

        if x1.tag != x2.tag:
            print('Tags do not match: %s and %s' % (x1.tag, x2.tag))
            result = False
        if x1.tag not in tagExcludes:
            for name, value in x1.attrib.items():
                if not name in attributeExcludes:
                    if x2.attrib.get(name) != value:
                        print('Attributes do not match: %s=%r, %s=%r' % (name, value, name, x2.attrib.get(name)))
                        result = False
            for name in x2.attrib.keys():
                if not name in attributeExcludes:
                    if name not in x1.attrib:
                        print('x2 has an attribute x1 is missing: %s' % name)
                        result = False
        if not self.text_compare(x1.text, x2.text):
            print('text: %r != %r' % (x1.text, x2.text))
            result = False
        if not self.text_compare(x1.tail, x2.tail):
            print('tail: %r != %r' % (x1.tail, x2.tail))
            result = False
        cl1 = list(x1)
        cl2 = list(x2)
        if len(cl1) != len(cl2):
            print('children length differs, %i != %i' % (len(cl1), len(cl2)))
            result = False
        i = 0
        for c1, c2 in zip(cl1, cl2):
            i += 1
            if not c1.tag in attributeExcludes:
                if not self.xml_compare(c1, c2, tagExcludes, attributeExcludes):
                    print('children %i do not match: %s' % (i, c1.tag))
                    result = False
        return result

    def text_compare(self, t1, t2):
        """
        Compare two text strings
        :param t1: text one
        :param t2: text two
        :return:
            True if a match
        """
        if not t1 and not t2:
            return True
        if t1 == '*' or t2 == '*':
            return True
        return (t1 or '').strip() == (t2 or '').strip()



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
    errorCount = 0

    inPath = Path(Path.cwd(), 'tests', 'testMcfxExtraction', 'testMcfxExtraction.mcfx')
    outdirPath = Path(Path.cwd(), 'tests', 'testMcfxExtraction', 'tmp-dir')
    delete_outdir(outdirPath)

    # here's the call which we are actually testing ...
    unpackedFolder, mcfxmlname = unpackMcfx(inPath, outdirPath)

    # now to check what we think of what it has done ...
    assert unpackedFolder is None # since we are providing an outdir
    assert str(mcfxmlname) == os.path.join(str(outdirPath), "data.mcf") # the mcf is always called data.mcf!

    # At this point we want to compare the extracted data.mcf with McfOriginals/testMcfxExtraction.mcf but it's not
    # easy because the XML contains some "session" data, like the lastTextFormat used tag, the folder id, some
    # statistical stuff, and so on. And sometimes the Cewe editor just seems to be a bit random about the order
    # in which it stores, e.g., alignment attributes.

    extractedXml = ET.parse(mcfxmlname)
    originalXml = ET.parse(Path(Path.cwd(), 'tests', 'testMcfxExtraction', 'McfOriginals', 'testMcfxExtraction.mcf'))

    comparator = XmlTree()

    if not comparator.xml_compare(extractedXml.getroot(), originalXml.getroot(),
            ["lastTextFormat", "project", "savingVersion", "statistics"], # complete tags to ignore
            ["folderID", "imagedir"]): # attributes to ignore
        print("fotobook XML extracted from .mcfx doesn't match the original mcf version closely enough")
        errorCount += 1

    # check that all the (image) files from the checked-in mcf version are present in the newly unpacked mcfx folder
    mcfdateienPath = Path(Path.cwd(), 'tests', 'testMcfxExtraction', 'McfOriginals', 'testMcfxExtraction_mcf-Dateien')

    # I'd like to use this:
    #   dcmp = filecmp.dircmp(mcfdateienPath, outdirPath, ignore=('folderid.xml'))
    # but can't make it work
    for originalFileBaseName in os.listdir(mcfdateienPath):
        if originalFileBaseName == 'folderid.xml':
            continue # this is always different
        if originalFileBaseName.endswith('~'):
            continue # backup files, who cares
        originalFile = os.path.join(mcfdateienPath, originalFileBaseName)
        mcfxFile = os.path.join(outdirPath, originalFileBaseName)
        if os.path.exists(mcfxFile):
            if not filecmp.cmp(originalFile, mcfxFile):
                print(f"{originalFileBaseName} found in .mcfx extraction, but not equal to the original")
                errorCount += 1
        else:
            print(f"{originalFileBaseName} not found in .mcfx extraction")
            errorCount += 1

    assert errorCount == 0


if __name__ == '__main__':
    #only executed when this file is run directly.
    test_mcfxExtraction()