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
    curdir = os.getcwd()

    tempdir = None
    if tempdirPath is not None:
        if not os.path.exists(tempdirPath):
            os.mkdir(tempdirPath)
    else:
        # we actually return the tempdir resource so keep pylint quiet here
        tempdir = tempfile.TemporaryDirectory() # pylint: disable=consider-using-with
        tempdirPath = tempdir.name

    try:
        os.chdir(tempdirPath) # somewhere like C:\Users\pete\AppData\Local\Temp\tmpshi3s9di
        logging.info(f"Unpacking mcfx to {os.getcwd()}")

        fullname = mcfxPath.resolve()
        mcfxMtime = os.path.getmtime(fullname)
        connection = sqlite3.connect(fullname)
        cursor = connection.cursor()
        logging.info(r"Connected to mcfx database")

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
                    logging.error(r"Exiting: found more than one mcf file in the mcfx database!")
                    sys.exit(1)
                mcfname = Path(tempdirPath) / filename

                # try turn the blob of bytes into a string, since an mcf is supposed to be xml
                try:
                    notused = str(filecontent, encoding='utf-8')
                except UnicodeDecodeError as decodeEx:
                    if decodeEx.reason == "invalid start byte" and decodeEx.object[decodeEx.start-1] == 0:
                        # Then we've (probably, based on experimentation!) reached the end of the xml string
                        # and there is junk in the buffer after that. Shorten the amount of data to be stored
                        # in the actual xml file...
                        filecontent = filecontent[:decodeEx.start-1]

            if os.path.exists(filename) and lastchange < os.path.getmtime(filename):
                # not changed since last extraction
                continue

            writeTofile(filecontent, filename)

        cursor.close()

    except sqlite3.Error as error:
        logging.error(f"Exiting: sqllite3 failed to read image or mcf data: {error}")
        sys.exit(1)
    except Exception as ex:
        logging.error(f"Exiting: failure handling image or mcf data: {ex}")
        sys.exit(1)

    finally:
        if connection:
            connection.close()
            logging.info(r"Disconnected from mcfx database")
        os.chdir(curdir)

        if not mcfname:
            logging.error(r"Exiting: no mcf file found in mcfx")

        logging.info(f"returned to cwd {os.getcwd()}, mcfname {mcfname}")

    # return tempdir so that we can use cleanup() when we're done with it
    return (tempdir, mcfname)
