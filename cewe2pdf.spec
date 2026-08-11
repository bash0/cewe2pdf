# -*- mode: python ; coding: utf-8 -*-

import subprocess
from pathlib import Path

# A frozen executable has no .git directory to inspect at run time.  Capture
# the Git description now and bundle it as a small Python module instead.
generatedBuildInfoDirectory = Path(SPECPATH) / 'build' / 'generatedBuildInfo'
generatedBuildInfoDirectory.mkdir(parents=True, exist_ok=True)
try:
    gitDescription = subprocess.run(
        ['git', 'describe', '--tags', '--long', '--always', '--dirty',
         '--match', 'cewe2pdf-v*'],
        cwd=SPECPATH,
        check=True,
        capture_output=True,
        text=True).stdout.strip()
except (FileNotFoundError, OSError, subprocess.CalledProcessError):
    gitDescription = None
(generatedBuildInfoDirectory / 'frozenBuildInfo.py').write_text(
    f'FROZEN_GIT_BUILD_IDENTIFICATION = {gitDescription!r}\n', encoding='utf-8')

# NumPy 2 imports this module dynamically during initialisation through OpenCV.
# PyInstaller's normal analysis does not see that import.
hiddenimports = ['numpy._core._exceptions']


a = Analysis(
    ['cewe2pdf.py'],
    pathex=[str(generatedBuildInfoDirectory)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # cffi imports setuptools only to support legacy build-time machinery.
    # The converter does not need it at run time, and excluding it avoids
    # bundling setuptools' deprecated pkg_resources API.
    excludes=['setuptools', 'pkg_resources'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='cewe2pdf',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
