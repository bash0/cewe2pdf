import os
import pytest
os.environ['IGNORELOCALFONTS'] = "1"
pytest.main(['-x', '--capture=tee-sys', '.', ''])
