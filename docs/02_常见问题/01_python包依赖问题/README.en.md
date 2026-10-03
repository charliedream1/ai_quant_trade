# 1. Notes

Last updated: 2025-02-15. Added on 2026-10-01: the root-level
`requirements.txt` file has been removed. Dependencies are now maintained by
each runnable example or topic directory. Enter the target directory before
installing dependencies.

Notes:

- Environment files may lag behind the latest code.

The exported full Python dependency environments are provided for reference:

- Files starting with `pip` were exported with pip.
- Files starting with `conda` were exported with Conda.

Versions:

- Files containing `finrl` correspond to the reinforcement-learning strategy
  environment.
- Files without `finrl` correspond to other environment configurations.

Test environment:

- Windows 10
- Python 3.8
- GPU: GTX 1050 Ti (4096 M) + CUDA 10.2 + cuDNN 8.6
- RAM: 32 GB
- CPU: i7-8750H

# 2. Import an Environment

> Since 2026-10-01, the repository root no longer provides a unified
> `requirements.txt`. Enter the target example or topic directory and use the
> dependency file maintained there.

Using pip:

```bash
# Example: enter the runnable example or topic directory first.
cd <project-dir>
pip install -r requirements.txt

# Temporarily use a mirror.
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

Using Conda:

```bash
# Run this inside the subproject directory.
conda install --yes --file requirements.txt
```
