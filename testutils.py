import glob
import os
import os.path

from pathlib import Path
from extraLoggers import mustsee

# Parse the mcf file to create variations using xml.dom.minidom rather than xml.etree.ElementTree
# Copilot suggested this choice because etree is bad at parsing CDATA
from xml.dom.minidom import Document


def getLatestResultFile(albumFolderBasename, pattern: str) -> str:
    resultpdfpattern = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", 'previous_result_pdfs', pattern))
    resultpdffiles = glob.glob(resultpdfpattern)
    # I used to sort on the modification date in order to find the latest file:
    #   resultpdffiles.sort(key=os.path.getmtime, reverse=True)
    # but that doesn't work when we run automated tests on github machines. So
    # I guess we'll just have to rely on the naming convention:
    resultpdffiles.sort(key=os.path.basename, reverse=True)
    return resultpdffiles[0] if len(resultpdffiles) > 0 else None


def createVariationMcf(dom, outFile):
    # Write the variation mcf and build a book from it. The effort in getting the edited
    # mcf file in a particular form is done that we can potentially manually compare it
    # with the original mcf file and be sure that it is not changed in unexpected ways
    with open(outFile, "w", encoding="utf-8") as file:
        # Write a custom xml declaration including the encoding which is
        # not emitted by the simplest one-line solution here:
        #   file.write(dom.toxml())
        file.write('<?xml version="1.0" encoding="UTF-8"?>\n')

        # Write the xml content, skipping the declaration we have just done
        pretty_xml = dom.documentElement.toprettyxml(indent="  ")
        # Remove excess blank lines introduced by `toprettyxml`
        clean_xml = "\n".join([line for line in pretty_xml.splitlines() if line.strip()])
        file.write(clean_xml)


def runModifications(tryToBuildBook, albumFolderBasename, albumBasename, dom, attribute_modifications, elementToModify):
    # build a pdf with the supplied tryToBuildBook method with the sets of attribute modifications
    # on the supplied element to modify in the document dom
    filesToDelete = []
    for variationName, modifications in attribute_modifications.items():
        for attr, value in modifications.items():
            elementToModify.setAttribute(attr, value)  # Modify attributes

        # Save the modified xml to a new file
        outFileBasename = f'{albumBasename}_{variationName}.mcf'
        outFile = str(Path(Path.cwd(), 'tests', f"{albumFolderBasename}", outFileBasename))
        pdfFile = f'{outFile}.pdf'
        latestResultFile = getLatestResultFile(albumFolderBasename, f"*{variationName}.mcf.pdf")

        createVariationMcf(dom, outFile)
        result = tryToBuildBook(outFile, pdfFile, latestResultFile, False, 28)
        if result:
            mustsee.info(f"Test variation {variationName} ok, variation files will be deleted")
            filesToDelete.append(outFile)
            filesToDelete.append(pdfFile)

    # do not delete the variation files until all test are run, so they
    # are present while we are debugging
    for f in filesToDelete:
        os.remove(f)


def getOutFileBasename(main, albumBasename, yyyymmdd, styleid):
    if (main):
        # use an undated output file name when running as main rather than via pytest
        outFileBasename = f'{albumBasename}.mcf.{styleid}.pdf'
    else:
        outFileBasename = f'{albumBasename}.mcf.{yyyymmdd}{styleid}.pdf'
    return outFileBasename
