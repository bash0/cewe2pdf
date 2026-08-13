from extraLoggers import mustsee, configlogger

class LineScales:
    """Line-spacing settings read for one conversion.

    These used to be class attributes, which meant a conversion could change
    the spacing used by a later conversion in the same Python process.
    Keeping them together in this small object makes the configuration
    lifetime explicit and leaves the renderer free of mutable module state.
    """

    def __init__(self, configSection):
        # Best to configure 1.15 in new setups; retain 1.1 as the historical
        # fallback so old albums are not silently reformatted.
        self.default_line_scale = 1.1
        self.font_line_scales = {}
        self._setupDefaultLineScale(configSection)
        self._setupFontLineScales(configSection)

    def _setupDefaultLineScale(self, configSection):
        if configSection is not None:
            try:
                dls = configSection.getfloat('defaultLineScale', 1.15)
                self.default_line_scale = dls
            except:# noqa: E722  # pylint: disable=bare-except
                configlogger.error("Invalid defaultLineScale in .ini file")
        mustsee.info(f"Default line scale = {self.default_line_scale}")

    def _setupFontLineScales(self, configSection):
        if configSection is not None:
            ff = configSection.get('fontLineScales', '').splitlines()  # newline separated list of fontname : line_scale
            specifiedLineScales = filter(lambda bg: (len(bg) != 0), ff)
            for specifiedLineScale in specifiedLineScales:
                scaleItems = specifiedLineScale.split(":")
                if len(scaleItems) == 2:
                    fontName = scaleItems[0].strip()
                    try:
                        scale = float(scaleItems[1].strip())
                        self.font_line_scales[fontName] = scale
                        configlogger.info(f"Font {fontName} uses non-standard line scale {self.font_line_scales[fontName]}")
                    except ValueError:
                        configlogger.error(f"Invalid line scale value {scaleItems[1]} ignored for {fontName}")
                else:
                    configlogger.error(f"Invalid lineScales entry ignored (should be 'FontName: Scale'): {specifiedLineScale}")

    def lineScaleForFont(self, font):
        if font in self.font_line_scales:
            return self.font_line_scales[font]
        return self.default_line_scale
