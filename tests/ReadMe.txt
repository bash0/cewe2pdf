The main Visual Studio project is normally set up to use runAllTests.py
To debug running test_simpleBook.py you need to make two changes:
1. Set the startup file for the project to tests\test_simpleBook.py
2. Change tests\cewe2pdf.ini:
     cewe_folder becomes C:\Program Files\Elkjop fotoservice_6.3\elkjop fotoservice
     hps_folder is commented out