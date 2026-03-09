import logging

def getUncommentedConfigItem(configSection, itemName, defaultValue):
    return str(configSection.get(itemName, defaultValue)).split('#', 1)[0].rstrip()

def getConfigurationInt(configSection, itemName, defaultValue, minimumValue):
    returnValue = minimumValue
    if configSection is not None:
        try:
            # eg getConfigurationInt(defaultConfigSection, 'pdfImageResolution', '150', 100)
            returnValue = int(getUncommentedConfigItem(configSection, itemName, defaultValue))
        except ValueError:
            logging.error(f'Invalid int configuration value supplied for {itemName}')
            returnValue = int(defaultValue)
        if returnValue < minimumValue:
            logging.error(f'Configuration value supplied for {itemName} is less than {minimumValue}, using {minimumValue}')
            returnValue = minimumValue
    return returnValue


def getConfigurationFloat(configSection, itemName, defaultValue, minimumValue):
    returnValue = minimumValue
    if configSection is not None:
        try:
            # eg getConfigurationFloat(defaultConfigSection, 'pdfImageResolution', '1.15', 1.0)
            returnValue = float(getUncommentedConfigItem(configSection, itemName, defaultValue))
        except ValueError:
            logging.error(f'Invalid float configuration value supplied for {itemName}')
            returnValue = float(defaultValue)
        if returnValue < minimumValue:
            logging.error(f'Configuration value supplied for {itemName} is less than {minimumValue}, using {minimumValue}')
            returnValue = minimumValue
    return returnValue

def getConfigurationBool(configSection, itemName, defaultValue):
    returnValue = defaultValue
    if configSection is not None:
        try:
            # eg getConfigurationBool(defaultConfigSection, 'insideCoverWhite', 'False')
            bv = getUncommentedConfigItem(configSection, itemName, defaultValue)
            returnValue = bv.lower() == "true"
        except ValueError:
            logging.error(f'Invalid bool configuration value supplied for {itemName}')
            returnValue = bool(defaultValue)
    return returnValue
