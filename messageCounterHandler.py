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
        # leveldefs is a comma separated list of LEVELNAME[count] entries
        levels = leveldefs.split(",")
        for level in levels:
            # parse out the level name and count
            matches = re.findall("(\w+)\[(\d+)\]",level.strip())
            if len(matches) == 1:
                levelname = matches[0][0]
                levelcount = int(matches[0][1])
                if levelname in self.levelToCountDict.keys():
                    actualcount = self.levelToCountDict[levelname]
                    if actualcount != levelcount:
                        print(f"NB >>>>> {loggerName} has {actualcount} {levelname} messages, versus expected {levelcount}")


