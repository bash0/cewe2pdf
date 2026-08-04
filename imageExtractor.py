import os
import sys
import argparse
from pathlib import Path
from mcfx import unpackMcfx

def collectArgsAndExtract():
    class CustomArgFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass

    epilogText = "Example:\n   python imageExtractor.py"
    exampleFile = r"c:\path\to\my\files\my_nice_fotobook.mcfx"
    parser = argparse.ArgumentParser(description='Extract all the images (and data.mcf) from an mcfx file',
                                     epilog=f"{epilogText} {exampleFile}\n \n",
                                     formatter_class=CustomArgFormatter)
    parser.add_argument('--out-dir', dest='imageDir', action='store',
                        default=None,
                        help='Directory for extracted photos')
    parser.add_argument('inputFile', type=str, nargs='?',
                        help='Just one mcf(x) input file must be specified')

    args = parser.parse_args()

    if args.inputFile is None:
        # you must specify a file name. Check if there are any obvious candidates
        # which we could use in an example text
        fnames = [i for i in os.listdir(os.curdir) if os.path.isfile(i) and i.endswith('.mcfx')]
        if len(fnames) >= 1:
            # There is one or more mcf(x) file! Show him how to specify the first such file as an example.
            exampleFile = os.path.join(os.getcwd(), fnames[0])
            if ' ' in exampleFile:
                exampleFile = f'\"{exampleFile}\"'
            parser.epilog = f"{epilogText} {exampleFile}\n \n"
        parser.parse_args(['-h'])
        sys.exit(1)

    if args.imageDir is None:
        parser.parse_args(['-h'])
        sys.exit(1)

    imageDir = os.path.abspath(args.imageDir)

    # convert the file
    inputFilePath = Path(args.inputFile)
    imageDirPath = Path(imageDir)

    unpackedFolder, mcfxmlname = unpackMcfx(inputFilePath, imageDirPath)

if __name__ == '__main__':
    # only executed when this file is run directly.
    # we need trick to have both: default and fixed formats.
    collectArgsAndExtract()

