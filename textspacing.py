"""CEWE letter-spacing parsing."""

import logging


def getLetterSpacing(text_format, mcf_to_reportlab):
    """
    Return CEWE's area-wide letter spacing in ReportLab points.

    ``letterSpacing`` is stored in MCF units (0.1 mm), unlike the equivalent
    HTML CSS declaration which is expressed in Qt pixels.  Using the MCF value
    avoids an otherwise undocumented pixel-to-point conversion.

    This initial implementation deliberately applies one value to the whole
    text area.  Per-span character spacing and wrapping-aware measurement are
    separate enhancements.
    """
    if text_format is None:
        return 0.0

    spacing_text = text_format.get('letterSpacing')
    if spacing_text is None:
        return 0.0

    try:
        return float(spacing_text) * mcf_to_reportlab
    except ValueError:
        logging.warning(f"Ignoring invalid text letterSpacing setting {spacing_text!r}")
        return 0.0
