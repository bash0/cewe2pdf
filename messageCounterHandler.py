# based on Rolf's answer in https://stackoverflow.com/questions/812477/how-many-times-was-logging-error-called

import logging

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
        for l in ("ERROR", "WARNING", "INFO", "DEBUG"):
            if (l in self.levelToCountDict):
                if text: text += ", "
                text += f"{l}[{self.levelToCountDict[l]}]"
        return text

