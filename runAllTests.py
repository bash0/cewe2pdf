import os

import pytest
os.environ['IGNORELOCALFONTS'] = "1"


def runall():
    """Run the test suite and return pytest's operating-system exit status."""
    pytestArguments = ['-x', '--capture=tee-sys', '.', ''] # to stop after the first assertion
    # pytestArguments = ['--capture=tee-sys', '--maxfail=0', '.'] # to continue after an assertion
    return pytest.main(pytestArguments)


if __name__ == '__main__':
    raise SystemExit(runall())
