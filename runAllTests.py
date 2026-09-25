import pytest

# A simple "pass/fail" alternative with no diagnostic output is simply to run
#    python -m pytest -rs
# from a command prompt with the correct environment activated (eg conda activate <environment>),
# thus running all tests in the current directory and subdirectories and reporting the results
# in a compact form.
# Other possibilities are to ignore the calendar tests, for example, by running
#   python -m pytest -rs --ignore=tests/testCalendar
# or to run only the calendar tests by running
#   python -m pytest -rs tests/testCalendar

def runall():
    """Run the test suite and return pytest's operating-system exit status."""
    pytestArguments = ['-x', '--capture=tee-sys', '.', ''] # to stop after the first assertion
    # pytestArguments = ['--capture=tee-sys', '--maxfail=0', '.'] # to continue after an assertion
    return pytest.main(pytestArguments)


if __name__ == '__main__':
    raise SystemExit(runall())
