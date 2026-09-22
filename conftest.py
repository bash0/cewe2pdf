"""Pytest-wide settings for reproducible cewe2pdf regression tests."""

import os


# Golden PDFs are made from the fonts explicitly supplied by each test, not
# from whichever per-user fonts happen to be installed on the test machine.
# Keep direct ``python -m pytest`` runs equivalent to ``runAllTests.py`` and
# the CI test environment.
os.environ['IGNORELOCALFONTS'] = '1'
