import os
import pytest
os.environ['IGNORELOCALFONTS'] = "1"
pytest.main(['-x', '--capture=tee-sys', '.', '']) # to stop after the first assertion
# pytest.main(['--capture=tee-sys', '--maxfail=0', '.']) # to continue after an assertion