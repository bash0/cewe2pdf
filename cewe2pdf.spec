# -*- mode: python ; coding: utf-8 -*-

import os
import shutil
import subprocess
import sys
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


def findCairoDll():
    """Return the Windows Cairo DLL supplied by a GTK runtime, if present."""
    cairoDllName = 'libcairo-2.dll'
    cairoDllPath = shutil.which(cairoDllName)
    if cairoDllPath is not None:
        return Path(cairoDllPath)

    # GTK3-Runtime Win64 uses this default location.  Checking it explicitly
    # also handles an installer which did not update the current PATH.
    programFiles = os.environ.get('ProgramFiles')
    if programFiles is not None:
        cairoDllPath = Path(programFiles) / 'GTK3-Runtime Win64' / 'bin' / cairoDllName
        if cairoDllPath.is_file():
            return cairoDllPath
    return None


def findCairoRuntimeDlls(cairoDll):
    """Return Cairo and its non-system DLL dependencies from its runtime."""
    # pefile is installed with PyInstaller on Windows.  Import it here rather
    # than at module level, because Linux builds do not need this code path.
    import pefile

    runtimeDirectory = cairoDll.parent
    cairoRuntimeDlls = {cairoDll}
    pendingDlls = [cairoDll]

    while pendingDlls:
        dll = pendingDlls.pop()
        portableExecutable = pefile.PE(str(dll), fast_load=True)
        portableExecutable.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
        for importedLibrary in getattr(portableExecutable, 'DIRECTORY_ENTRY_IMPORT', []):
            dependency = runtimeDirectory / importedLibrary.dll.decode('ascii')
            if dependency.is_file() and dependency not in cairoRuntimeDlls:
                cairoRuntimeDlls.add(dependency)
                pendingDlls.append(dependency)

    return cairoRuntimeDlls


def findPythonRuntimeDlls():
    """Return Conda native DLLs required by CPython extension modules."""
    runtimeDirectory = Path(sys.prefix) / 'Library' / 'bin'
    runtimeDllNames = [
        'ffi.dll', 'libbz2.dll', 'libcrypto-3-x64.dll', 'libexpat.dll',
        'liblzma.dll', 'libssl-3-x64.dll', 'sqlite3.dll',
    ]
    return [
        runtimeDirectory / dllName
        for dllName in runtimeDllNames
        if (runtimeDirectory / dllName).is_file()
    ]


binaries = []
if sys.platform == 'win32':
    # CPython from python.org contains these libraries itself, while Conda
    # keeps native dependencies of standard extension modules in Library\bin.
    # Bundle them when present so a Conda-built EXE is independent of the shell
    # from which it is launched.
    binaries.extend((str(dll), '.') for dll in findPythonRuntimeDlls())
    cairoDll = findCairoDll()
    if cairoDll is None:
        raise SystemExit(
            'The Windows standalone build needs GTK3 Runtime (libcairo-2.dll). '
            'Install GTK3 Runtime Win64, or place its bin directory on PATH.')
    # cairocffi loads Cairo through ctypes, so PyInstaller cannot infer this
    # native dependency from Python imports.  Bundle Cairo and the DLLs it
    # needs from the same GTK/MSYS2 runtime beside the executable.
    binaries.extend((str(dll), '.') for dll in findCairoRuntimeDlls(cairoDll))


a = Analysis(
    ['cewe2pdf.py'],
    pathex=[str(generatedBuildInfoDirectory)],
    binaries=binaries,
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
