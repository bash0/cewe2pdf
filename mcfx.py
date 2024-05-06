# This file contains code to unpack an .mfcx album to the older format
# of an mcf file and a folder of images. An mfcx file is just a database
# with a single table, Files, where each row is a filename and a blob
# content for the file. We create a temporary directory and unpack all
# the files to there. One of these files is the .mcf file in exactly the
# format which we have used for previous versions.

# This code is basically taken from
# https://pynative.com/python-sqlite-blob-insert-and-retrieve-digital-data/#h-retrieve-image-and-file-stored-as-a-blob-from-sqlite-table

import logging
import os
import tempfile
import sqlite3
import sys

from pathlib import Path

def writeTofile(data, filename):
    # logging.info("Writing {}".format(filename))
    with open(filename, 'wb') as file:
        file.write(data)

def unpackMcfx(mcfxPath: Path, tempdirPath):
    mcfname = ""
    curdir = os.getcwd();

    tempdir = None
    if tempdirPath is not None:
        if not os.path.exists(tempdirPath):
            os.mkdir(tempdirPath)
    else:
        tempdir = tempfile.TemporaryDirectory()
        tempdirPath = tempdir.name

    try:
        os.chdir(tempdirPath) # somewhere like C:\Users\pete\AppData\Local\Temp\tmpshi3s9di
        logging.info("Unpacking mcfx to {}".format(os.getcwd()))

        fullname = mcfxPath.resolve()
        mcfxMtime = os.path.getmtime(fullname)
        connection = sqlite3.connect(fullname)
        cursor = connection.cursor()
        logging.info("Connected to mcfx database")

        sql_fetch_blob_query = """SELECT * from Files"""
        cursor.execute(sql_fetch_blob_query)
        record = cursor.fetchall()
        for row in record:
            filename = row[0]
            filecontent = row[1]
            lastchange = row[2] / 1000
            if lastchange == 0:
                lastchange = mcfxMtime
            if filename.endswith(".mcf"):
                if mcfname:
                    logging.error("Exiting: found more than one mcf file in the mcfx database!")
                    sys.exit(1)
                mcfname = Path(tempdirPath) / filename

            if os.path.exists(filename) and lastchange < os.path.getmtime(filename):
                #not changed since last extraction
                continue

            writeTofile(filecontent, filename)

        cursor.close()

    except sqlite3.Error as error:
        logging.error("Exiting: failure to read image data: {}".format(error))
        sys.exit(1)

    finally:
        if connection:
            connection.close()
            logging.info("Disconnected from mcfx database")
        os.chdir(curdir)

        if not mcfname:
            logging.error("Exiting: no mcf file found in mcfx")

        logging.info("returned to cwd {}, mcfname {}".format(os.getcwd(), mcfname))

    # return tempdir so that we can use cleanup() when we're done with it
    return (tempdir, mcfname)
