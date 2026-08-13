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

class ConversionMessageCounters:
    """Count log records for one conversion and detach cleanly afterwards.

    The handlers deliberately count records before logger-level filtering, as
    did the original global handlers.  Their lifetime is now one conversion,
    rather than the whole Python process, so consecutive conversions no longer
    inherit one another's expected-message totals.
    """

    def __init__(self):
        self.root_handler = MsgCounterHandler()
        self.root_handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(self.root_handler)

        self.config_handler = MsgCounterHandler()
        self.config_handler.setLevel(logging.DEBUG)
        configlogger.addHandler(self.config_handler)

    def close(self):
        """Detach the handlers once the conversion has reported its totals."""
        logging.getLogger().removeHandler(self.root_handler)
        configlogger.removeHandler(self.config_handler)

    def verify(self, configSection):
        # if he has specified "normal" values for the number of messages of each kind, then warn if we do not see that number
        if configSection is None:
            return
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
                    self.config_handler.checkCounts(loggerName,leveldefs)
                elif loggerName == logging.getLogger().name:
                    self.root_handler.checkCounts(loggerName,leveldefs)
                else:
                    print(f"Invalid expectedLoggingMessageCounts logger name, entry ignored: {loggerdef}")
            else:
                print(f"Invalid expectedLoggingMessageCounts entry ignored: {loggerdef}")

    def print_summary(self):
        print("Total message counts, including messages suppressed by logger configuration")
        print(f" cewe2pdf.config: {self.config_handler.messageCountText()}")
        print(f" root:            {self.root_handler.messageCountText()}")
