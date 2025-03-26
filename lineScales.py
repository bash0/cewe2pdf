from extraLoggers import mustsee, configlogger

class LineScales():

    defaultLineScale = 1.1 # line scale if not overridden. Best to configure to 1.15 - don't break old albums by changing here
    fontLineScales = {} # mapping fontnames to linescale where the standard defaultLineScale is not ok

    def __init__(self):
        return

    @staticmethod
    def setupDefaultLineScale(configSection):
        if configSection is not None:
            try:
                dls = configSection.getfloat('defaultLineScale', 1.15)
                LineScales.defaultLineScale = dls
            except:# noqa: E722  # pylint: disable=bare-except
                configlogger.error("Invalid defaultLineScale in .ini file")
        mustsee.info(f"Default line scale = {LineScales.defaultLineScale}")

    @staticmethod
    def setupFontLineScales(configSection):
        if configSection is not None:
            ff = configSection.get('fontLineScales', '').splitlines()  # newline separated list of fontname : line_scale
            specifiedLineScales = filter(lambda bg: (len(bg) != 0), ff)
            for specifiedLineScale in specifiedLineScales:
                scaleItems = specifiedLineScale.split(":")
                if len(scaleItems) == 2:
                    fontName = scaleItems[0].strip()
                    try:
                        scale = float(scaleItems[1].strip())
                        LineScales.fontLineScales[fontName] = scale
                        configlogger.info(f"Font {fontName} uses non-standard line scale {LineScales.fontLineScales[fontName]}")
                    except ValueError:
                        configlogger.error(f"Invalid line scale value {scaleItems[1]} ignored for {fontName}")
                else:
                    configlogger.error(f"Invalid lineScales entry ignored (should be 'FontName: Scale'): {specifiedLineScale}")

    @staticmethod
    def lineScaleForFont(font):
        if font in LineScales.fontLineScales:
            return LineScales.fontLineScales[font]
        return LineScales.defaultLineScale
