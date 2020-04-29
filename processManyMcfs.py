# eg python processManyMcfs.py
# D:\Users\pete\Documents\Fotobooks\PhotoAlbum201?.mcf
# D:\Users\pete\Documents\Fotobooks\PhotoAlbum2014?.mcf
import sys
from glob import glob
from cewe2pdf import convertMcf

def printFileName(filename):
    print
    print("--------------------------->" + filename)
    resultFlag = convertMcf(filename, False)

def main():
    args = sys.argv[1:]
    for arg in args:
          for filename in glob(arg):
            printFileName(filename)

if __name__ == '__main__':
    main()