Reference URL:
https://docs.anaconda.com/miniconda/install/#quick-command-line-install

Install Miniconda from the command line on Linux:

```bash
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm ~/miniconda3/miniconda.sh
```

Install Miniconda from the command line on Windows:

```bash
curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe -o .\miniconda.exe
start /wait "" .\miniconda.exe /S
del .\miniconda.exe
```

Install Miniconda with PowerShell on Windows:

```bash
wget "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe" -outfile ".\miniconda.exe"
Start-Process -FilePath ".\miniconda.exe" -ArgumentList "/S" -Wait
del .\miniconda.exe
```

After installation, restart the terminal. The `conda` command should then be
available.

```bash
source ~/miniconda3/bin/activate
```

Initialize Conda for all terminals:

```bash
conda init --all
```
