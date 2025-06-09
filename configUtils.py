import logging

def getConfigurationInt(configSection, itemName, defaultValue, minimumValue):
    returnValue = minimumValue
    if configSection is not None:
        try:
            # eg getConfigurationInt(defaultConfigSection, 'pdfImageResolution', '150', 100)
            returnValue = int(configSection.get(itemName, defaultValue))
        except ValueError:
            logging.error(f'Invalid configuration value supplied for {itemName}')
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
            returnValue = float(configSection.get(itemName, defaultValue))
        except ValueError:
            logging.error(f'Invalid configuration value supplied for {itemName}')
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
            bv = configSection.get(itemName, defaultValue)
            returnValue = bv.lower() == "true"
        except ValueError:
            logging.error(f'Invalid configuration value supplied for {itemName}')
            returnValue = bool(defaultValue)
    return returnValue
