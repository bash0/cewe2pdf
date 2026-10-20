# Testing cewe2pdf on Linux using a Windows PC

See the [README documentation map](../README.md#documentation) for the other guides
and the [developer guide](DEVELOPER_GUIDE.md) for the general test workflow.

Testing on Linux is useful both as an additional supported platform and as a
reasonably close reproduction of the Ubuntu environment used by GitHub
Actions. Microsoft provides Linux on a Windows machine through the
[Windows Subsystem for Linux (WSL)](https://learn.microsoft.com/en-us/windows/wsl/install).

These instructions assume an Ubuntu WSL distribution and a Windows checkout
of this repository. The source checkout may remain on the Windows file
system; for example, it is visible to WSL as:

```
/mnt/c/Users/<your-Windows-user-name>/source/repos/cewe2pdf
```

## One-time WSL environment setup

Use a Linux Python 3.12 environment. It is separate from Python and Conda on
Windows, even if it has the same environment name. Do not create a `.venv`
inside the shared Windows checkout: a Linux virtual environment contains
Linux-specific links and executables. A Conda environment in the Linux home
directory avoids that problem.

The following is the recommended setup for a WSL installation which already
has Miniconda or Anaconda. The `(base)` prompt indicates that Conda is
available.

```bash
# Create this once. It is stored below /home/<your-Linux-user>/miniconda3,
# not in the Windows Conda installation.
conda create --name cewe2pdf312 python=3.12

conda activate cewe2pdf312

# Cairo is a Linux system library used by CairoSVG for clip art and masks.
sudo apt update
sudo apt install libcairo2

cd /mnt/c/Users/<your-Windows-user-name>/source/repos/cewe2pdf
python -m pip install --upgrade pip
python -m pip install -r requirements-pinned.txt
python -m pip check
```

`requirements-pinned.txt` is deliberate: it is the locked Python package set
used by the GitHub test job. In particular, it installs `pillow-heif`, which
is needed by `testImageFormats` to read the HEIC test image.

If Conda is not installed in WSL, create a Python 3.12 virtual environment in
the Linux home directory instead (the exact package used to obtain Python 3.12
depends on the Ubuntu version):

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv libcairo2
python3.12 -m venv ~/venvs/cewe2pdf312
source ~/venvs/cewe2pdf312/bin/activate

cd /mnt/c/Users/<your-Windows-user-name>/source/repos/cewe2pdf
python -m pip install --upgrade pip
python -m pip install -r requirements-pinned.txt
python -m pip check
```

## Everyday use

For each new WSL shell, activate the environment and change to the checkout:

```bash
conda activate cewe2pdf312
cd /mnt/c/Users/<your-Windows-user-name>/source/repos/cewe2pdf
```

If using the virtual-environment alternative, use this activation command
instead:

```bash
source ~/venvs/cewe2pdf312/bin/activate
```

Check `python --version` after activation, then use the [test workflow](../tests/README.md#running-tests).
For a quick platform-sensitive check:

```bash
python -m pytest -q tests/testImageExtractor/test_imageFormats.py tests/testShadows/test_shadows.py
```

The [comparison policy](../tests/README.md#comparison-tolerances) explains the native
Cairo variation on Linux. `conda deactivate` leaves the Conda environment without
changing the Windows environment.

## Using the Windows CEWE resources and fonts

The self-contained tests use resources supplied in `tests/`, so no CEWE
installation is needed for the test suite. To make a PDF from a real album
using the locally installed Windows CEWE resources and fonts, configure their
WSL paths in an album-local `cewe2pdf.ini` file. For example:

- `cewe_folder = /mnt/c/Program Files/Elkjop fotoservice_6.3/elkjop fotoservice`
  (from `C:\Program Files\Elkjop fotoservice_6.3\elkjop fotoservice`)
- `hpsFolder = /mnt/c/Users/<your-Windows-user-name>/AppData/Local/CEWE/hps`
  (previously found through the Windows `LOCALAPPDATA` variable)

For extra fonts, use WSL paths in `additional_fonts.txt`, for example:

- `/mnt/c/Windows/Fonts/`
- `/mnt/c/Users/<your-Windows-user-name>/AppData/Local/Microsoft/Windows/Fonts/`

Then, from the repository directory, run for example:

```bash
python cewe2pdf.py /path/to/album.mcf
```

## Building a Linux executable version of cewe2pdf

Follow the [Linux build instructions](build_a_compiled_version.md#linux-build) after setting up this environment.
