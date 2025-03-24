import logging
import logging.config
import os
import sys
import yaml

from messageCounterHandler import MsgCounterHandler

if os.path.exists('loggerconfig.yaml'):
    with open('loggerconfig.yaml', 'r') as loggeryaml: # this works on all relevant platforms so pylint: disable=unspecified-encoding
        config = yaml.safe_load(loggeryaml.read())
        logging.config.dictConfig(config)
else:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

# a logger for information we try to "insist" that the user sees
mustsee = logging.getLogger("cewe2pdf.mustsee")

# a logger for configuration, to distinguish that from logging in the album processing
configlogger = logging.getLogger("cewe2pdf.config")

# create log output handlers which count messages at each level
rootMessageCountHandler = MsgCounterHandler()
rootMessageCountHandler.setLevel(logging.DEBUG) # ensuring that it counts everything
logging.getLogger().addHandler(rootMessageCountHandler)

configMessageCountHandler = MsgCounterHandler()
configMessageCountHandler.setLevel(logging.DEBUG) # ensuring that it counts everything
configlogger.addHandler(configMessageCountHandler)


def VerifyMessageCounts(configSection):
    # if he has specified "normal" values for the number of messages of each kind, then warn if we do not see that number
    if configSection is not None:
        # the expectedLoggingMessageCounts section is one or more newline separated list of
        #   loggername: levelname[count], ...
        # e.g.
        #   root: WARNING[4], INFO[38]
        # Any loggername that is missing is not checked, any logging level that is missing is expected to have 0 messages
        ff = configSection.get('expectedLoggingMessageCounts', '').splitlines()
        loggerdefs = filter(lambda bg: (len(bg) != 0), ff)
        for loggerdef in loggerdefs:
            items = loggerdef.split(":")
            if len(items) == 2:
                loggerName = items[0].strip()
                leveldefs = items[1].strip() # a comma separated list of levelname[count]
                if loggerName == configlogger.name:
                    configMessageCountHandler.checkCounts(loggerName,leveldefs)
                elif loggerName == logging.getLogger().name:
                    rootMessageCountHandler.checkCounts(loggerName,leveldefs)
                else:
                    print(f"Invalid expectedLoggingMessageCounts logger name, entry ignored: {loggerdef}")
            else:
                print(f"Invalid expectedLoggingMessageCounts entry ignored: {loggerdef}")


def printMessageCountSummaries():
    print("Total message counts, including messages suppressed by logger configuration")
    print(f" cewe2pdf.config: {configMessageCountHandler.messageCountText()}")
    print(f" root:            {rootMessageCountHandler.messageCountText()}")
