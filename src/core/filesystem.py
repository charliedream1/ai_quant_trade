"""Portable filesystem helpers shared by legacy examples and production adapters."""

import os
import shutil
from pathlib import Path


def make_dirs(*directories):
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def clean_dirs(path):
    target = Path(path)
    if target.is_symlink():
        raise ValueError("Refusing to recursively remove a symbolic link")
    if target.resolve() == Path(target.anchor).resolve():
        raise ValueError("Refusing to recursively remove a filesystem root")
    if target.exists():
        shutil.rmtree(target)


def find_file(path, name):
    for directory, _, files in os.walk(path):
        for filename in files:
            if name in filename:
                return str(Path(directory) / filename)
    return None
