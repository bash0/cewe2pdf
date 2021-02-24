# eg python processManyMcfs.py D:\Users\fred\albums\PhotoAlbum*.mcf

# We're not quite at the level of documenting all the classes and functions yet :-)
#    pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import sys
from glob import glob
from cewe2pdf import convertMcf


def printFileName(filename):
    print()
    print("--------------------------->" + filename)
    convertMcf(filename, False) # throwing away the result


def main():
    args = sys.argv[1:]
    for arg in args:
        for filename in glob(arg):
            printFileName(filename)


if __name__ == '__main__':
    main()
