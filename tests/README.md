# Test-local notes

For the standard portable regression workflow, approved results, and fixture layout,
see the [developer guide](../documents/DEVELOPER_GUIDE.md#tests-and-approved-output).
The [compare-pdf README](compare-pdf/README.md) documents the comparison helper.

## Manual Visual Studio inspection with installed resources

The older notes below describe an optional Windows inspection of unittest_fotobook
using installed resources. These are not the settings for the portable approved-result
regression run. Substitute actual installation paths and keep local experiments out
of the shared fixture configuration.

On Windows the main Visual Studio project is normally set up to use runAllTests.py, which uses
pytest to find tests, and thus runs the same tests as will be run in the github checkin action.

To debug by running simply test_simpleBook.py (or some other individual test) with Visual Studio
you need to make two changes:
1. Set the startup file for the VS project to tests\unittest_fotobook\test_simpleBook.py
2. Change tests\unittest_fotobook\cewe2pdf.ini:
     cewe_folder becomes e.g. C:\Program Files\Elkjop fotoservice_6.3\elkjop fotoservice
     hps_folder is commented out
3. Change tests\unittest_fotobook\additional_fonts.txt
     comment in system fonts line, e.g. C:\WINDOWS\FONTS\

The resulting pdf file will be "better" than the version running with only the checked in
resources, because all the text will be in the correct fonts (using CEWE or Windows fonts
rather than substitutions)  It is worth making these changes to execute in "the correct"
environment simply because you will then see the correct results for various items which
demonstrate that particular behaviours work correctly or that special issues have been
fixed - items which in the "server only" version are not as well presented.

For this reason a previous result pdf from the correctly configured Windows environment run
has been kept:
    unittest_fotobook.mcf.20250413SwithWindowsFonts.pdf
just so that there is a record of how the proper result looks.