# based on Rolf's answer in https://stackoverflow.com/questions/812477/how-many-times-was-logging-error-called

import logging
import re

class MsgCounterHandler(logging.Handler):
    levelToCountDict = None

    def __init__(self, *args, **kwargs):
        super(MsgCounterHandler, self).__init__(*args, **kwargs)
        self.levelToCountDict = {}

    def emit(self, record):
        l = record.levelname
        if (l not in self.levelToCountDict):
            self.levelToCountDict[l] = 0
        self.levelToCountDict[l] += 1

    def messageCountText(self):
        # create a text with the counts shown in order from worst to best
        text = ""
        for l in (
            logging.getLevelName(logging.CRITICAL),
            logging.getLevelName(logging.ERROR),
            logging.getLevelName(logging.WARNING),
            logging.getLevelName(logging.INFO),
            logging.getLevelName(logging.DEBUG)
            ):
            if (l in self.levelToCountDict):
                if text: text += ", "
                text += f"{l}[{self.levelToCountDict[l]}]"
        return text

    def checkCounts(self, loggerName, leveldefs):
        # leveldefs is a comma separated list of LEVELNAME[count] entries. Use that to create a
        # dictionary of the expected number of messages at each level. We start with expected 0
        # for all levels, and then override with the entries from the leveldefs string
        expected = {logging.CRITICAL: 0, logging.ERROR: 0, logging.WARNING: 0, logging.INFO: 0, logging.DEBUG: 0}
        levelNamesMapping = logging.getLevelNamesMapping()
        levelspecs = leveldefs.split(",")
        for levelspec in levelspecs:
            # parse out the level name and count
            matches = re.findall("(\w+)\[(\d+)\]",levelspec.strip())
            if len(matches) == 1:
                levelname = matches[0][0].upper()
                if levelname in levelNamesMapping.keys():
                    level = levelNamesMapping[levelname]
                    levelcount = int(matches[0][1])
                    expected[level] = levelcount
                else:
                    print(f"Unknown message level {levelname} in expected message specification for {loggerName}")

        # now run through all the expected counts, including the initial entries with 0 expected which have not
        # been overridden by the configuration entries and check that the actuals are the same as the expected
        for level in expected.keys():
            levelname = logging._levelToName[level]
            if levelname in self.levelToCountDict.keys():
                actualcount = self.levelToCountDict[levelname]
            else:
                actualcount = 0
            if actualcount != expected[level]:
                print(f"NB >>>>> {loggerName} has {actualcount} {levelname} messages, versus expected {expected[level]}")
