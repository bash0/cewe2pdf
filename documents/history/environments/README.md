# Legacy Conda environment exports

These [Linux](cewe2pdfenvlinux.yml) and [Windows](cewe2pdfenvwindows.yml) YAML files
record an older Python 3.13 environment with earlier package versions and executable
build tools mixed into the environment. They do not reproduce the project's supported
Python 3.12 CI environment.

For current setup, follow [installation](../../../README.md#install), or the
[Linux/WSL guide](../../TestingOnWSL.md). For dependency maintenance, use the
[developer guide](../../DEVELOPER_GUIDE.md#python-dependencies).

The original environment names and version/build pins are preserved for historical
reference. These exports are not inputs to the current CI workflows.

## Earlier setup notes

> The following instructions belong to these legacy exports; use the current
> setup linked above for development.

The yml files here are used to create the environments for the different platforms. The windows one is the original, the linux version is tidied by copilot.

Installing on Ubuntu (under WSL, though I think it should work on a native install too):

- Install Miniconda in your WSL Ubuntu instance (if you haven’t already):
```
	wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
	bash Miniconda3-latest-Linux-x86_64.sh
``` 
- If you answered no to setting up the environment you can do it later:
```
	~/miniconda3/bin/conda init
```
- Then
```
	conda env create -f cewe2pdfxxx.yml
	conda activate cewe2pdfenv 
```
