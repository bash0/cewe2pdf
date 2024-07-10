# use py2exe to generate a .exe
# Important: currently, the generated .exe will not run.
#   There is a problem with the cairocffi package
#   cairocffi._generated is not found.)
# For now, use the pyinstaller method described in:
#   build_a_compiled_version.md
#
# usage:
# > python setup.py py2exe

from distutils.core import setup
# import py2exe

setup(console=['cewe2pdf.py'],
      options={"py2exe": {
          "packages": ['PIL', 'reportlab', 'lxml', 'cairosvg', 'cairocffi', 'urllib'],
          # 'includes': ['cairocffi._generated'],
          "bundle_files": 3,
          "compressed": False, }})
