# Standalone executables

This guide owns executable build instructions and Windows installation behaviour.
For source installation and Cairo setup, use the [README](../README.md#install).
For source provenance, see [version numbering](DEVELOPER_GUIDE.md#version-numbering).

Run commands from the repository root in an activated Python environment.
Build on the target operating system; these instructions are not a cross-compilation
recipe. The project does not publish executable releases; a developer can build one
for private distribution.

## Windows build

Prepare the [normal source environment](../README.md#install), then install the
Windows-only build overlay:

```powershell
python -m pip install -r requirements-winexe.txt
python -m PyInstaller cewe2pdf.spec --noconfirm --clean
.\dist\cewe2pdf.exe --version
```

The output is `dist/cewe2pdf.exe`. The checked-in specification includes dynamic imports
needed by indexing, captures build identification, and bundles Cairo with its required
non-system DLLs. Do not replace it with a bare `--onefile cewe2pdf.py` invocation.

Cairo must be available on the build machine. The specification can locate it through
`CEWE2PDF_CAIRO_DLL`, `PATH`, or the standard GTK3 Runtime Win64 installation.
The finished Windows executable does not require its recipient to install Python,
Cairo, GTK, or MSYS2.

Smoke-test the executable itself, not only the Python source:

```powershell
.\dist\cewe2pdf.exe --outFile tests/testEmptyPageOne/executable-smoke.pdf tests\testEmptyPageOne\test_emptyPageOne.mcf
```

Check the process result, confirm the output PDF exists, and inspect it.
The undated smoke PDF is outside the dated regression cleanup pattern; remove it
separately when finished.

## Linux build

Prepare the [Linux source environment](../README.md#install), or follow the
[WSL setup](TestingOnWSL.md) when developing from Windows.
The Linux build workflow currently uses this PyInstaller version:

```bash
python -m pip install pyinstaller==6.22.0
python -m PyInstaller cewe2pdf.spec --noconfirm --clean
./dist/cewe2pdf --version
./dist/cewe2pdf --outFile tests/testEmptyPageOne/executable-smoke-linux.pdf \
  tests/testEmptyPageOne/test_emptyPageOne.mcf
```

Check the output and process result. Review library availability on the intended target
system; the Windows DLL-bundling rule is not a claim that Linux output runs on every
distribution. Remove the undated smoke PDF separately when finished.
The [Linux executable workflow](../.github/workflows/build_pyinstaller_release.yml)
is manually triggered. This guide does not define a macOS frozen-build procedure.

## Windows Explorer installation and use

A recipient can double-click the Windows executable in Explorer to be offered a
per-user installation. It copies the EXE to `%LOCALAPPDATA%/cewe2pdf` and adds
**Create PDF with cewe2pdf** to the Explorer context menu for `.mcf` and `.mcfx`.
Administrator rights are not required. The editor remains the normal double-click
application for album files.

Right-click an album and select the command. Automatic mode discovers the CEWE
installation from Windows file associations where possible and enables shared
Windows system-font discovery. This deliberately overrides
`loadSystemFonts = False` in either INI file. An explicit, valid `cewe_folder`
still takes precedence over automatic CEWE-folder discovery. Per-user fonts are
also searched unless `IGNORELOCALFONTS` is set. The resulting PDF and a diagnostic
`<album>.mcf.log` or `<album>.mcfx.log` are written beside the input.
The log is overwritten each run.

An argumentless terminal invocation shows help rather than offering installation.
Use explicit commands when installing or removing the menu:

```powershell
.\dist\cewe2pdf.exe --install
.\dist\cewe2pdf.exe --uninstall
```

Uninstalling removes the menu entries and leaves the copied executable in place.
The console may appear briefly during an Explorer launch.
Locked output files must be closed before conversion can replace them.

## Build validation in CI

The [main workflow](../.github/workflows/pythonapp.yml) runs Linux source tests and
builds/smoke-tests the Windows executable. Canonical build tags are created only after
both jobs succeed. Changes to the dependency files or packaging must continue to pass
both paths.
