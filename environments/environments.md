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
