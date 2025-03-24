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
