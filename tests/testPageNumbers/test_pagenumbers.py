# This test needs to be in its own directory, so it can have it's own cwew2pdf.ini.
# Also we can store the asset files here.

# Test rendering when page one is empty

#if you run this file directly, it won't have access to parent folder, so add it to python path
import os, os.path
import sys
sys.path.append('..')
sys.path.append('.')
sys.path.append('tests/compare-pdf/compare_pdf') # used if compare_pdf has not been pip installed

# Parse the mcf file to create variations using xml.dom.minidom rather than xml.etree.ElementTree
# Copilot suggested this choice because etree is bad at parsing CDATA
from xml.dom.minidom import parse, Document

from datetime import datetime
from pathlib import Path
from pikepdf import Pdf

from compare_pdf import ComparePDF, ShowDiffsStyle # type: ignore
from cewe2pdf import convertMcf # type: ignore
from extraLoggers import mustsee # type: ignore

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
    readPdf.close()

    if latestResultFile is not None:
        # compare our result with the latest one
        print(f"Compare {outFile} with {latestResultFile}")
        files = [outFile, latestResultFile]
        compare = ComparePDF(files, ShowDiffsStyle.Nothing)
        result = compare.compare()
        compare.cleanup() # to force closure of the files and allow us to delete them
        assert result, "Pixel comparison failed"
    else:
        print(f"No result file to compare with {os.path.basename(outFile)}")
        result = False # we keep the result file so it can become an approved version

    return result


def checkModifiedMcfVersions(infile, attribute_modifications, albumFolderBasename, albumBasename):
    # Parse the mcf file and find the <pagenumbering> element
    dom = parse(infile)
    pagenumbering_element = dom.getElementsByTagName("pagenumbering")[0]
    if pagenumbering_element is None:
        raise ValueError("No <pagenumbering> element found in {infile}")

    # Iterate through modifications and create new versions
    filesToDelete = []
    for variationName, modifications in attribute_modifications.items():
        for attr, value in modifications.items():
            pagenumbering_element.setAttribute(attr, value)  # Modify attributes

        # Save the modified xml to a new file
        outFileBasename = f'{albumBasename}_{variationName}.mcf'
        outFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", outFileBasename))
        pdfFile = f'{outFile}.pdf'
        latestResultFile = getLatestResultFile(albumFolderBasename, f"*{variationName}.mcf.pdf")


        # Write the variation mcf and build a book from it. The effort in getting the file
        # result in a particular form is done that we can potentiallt manually compare it with
        # the original mcf and be sure that it is not changed in unexpected ways
        with open(outFile, "w", encoding="utf-8") as file:
            # Write a custom xml declaration including the encoding which is not emitted
            # by the simplest one-line solution, file.write(dom.toxml())
            file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            # Write the xml content, skipping the declaration we have just done
            pretty_xml = dom.documentElement.toprettyxml(indent="  ")
            # Remove blank lines introduced by `toprettyxml`
            clean_xml = "\n".join([line for line in pretty_xml.splitlines() if line.strip()])
            file.write(clean_xml)
            result = tryToBuildBook(outFile, pdfFile, latestResultFile, False, 28)
            if result:
                mustsee.info(f"Test variation {variationName} ok, variation files will be deleted")
                filesToDelete.append(outFile)
                filesToDelete.append(pdfFile)
    for f in filesToDelete:
        os.remove(f)

def test_testEmptyPageOne():
    albumFolderBasename = 'testPageNumbers'
    albumBasename = "test_pagenumbers"
    inFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", f'{albumBasename}.mcf'))
    yyyymmdd = datetime.today().strftime("%Y%m%d")

    styleid = "S"
    outFileBasename = f'{albumBasename}.mcf.{yyyymmdd}{styleid}.pdf'
    outFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", outFileBasename))
    latestResultFile = getLatestResultFile(albumFolderBasename, f"*{styleid}.pdf")
    tryToBuildBook(inFile, outFile, latestResultFile, False, 28)

    styleid = "D"
    outFileBasename = f'{albumBasename}.mcf.{yyyymmdd}{styleid}.pdf'
    outFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", outFileBasename))
    latestResultFile = getLatestResultFile(albumFolderBasename, f"*{styleid}.pdf")
    tryToBuildBook(inFile, outFile, latestResultFile, True, 15)

    # now use the same input mcf file to create and test variations in page numbering
    attribute_modifications = {
        # test all formats in position 4
        "f1p4": {"format": "1", "position": "4"},
        "f2p4": {"format": "2", "position": "4"},
        "f3p4": {"format": "3", "position": "4"},
        "f4p4": {"format": "4", "position": "4"},
        "f5p4": {"format": "5", "position": "4"},
        "f6p4": {"format": "6", "position": "4"},
        # test all positions in format 0
        "f0p1": {"format": "0", "position": "1"},
        "f0p2": {"format": "0", "position": "2"},
        "f0p4": {"format": "0", "position": "4"},
        "f0p5": {"format": "0", "position": "5"},
    }

    checkModifiedMcfVersions(inFile, attribute_modifications, albumFolderBasename, albumBasename)


if __name__ == '__main__':
    #only executed when this file is run directly.
    test_testEmptyPageOne()
