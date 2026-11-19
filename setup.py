"""PEP 517 resource hooks; installation is driven by pyproject.toml."""

import sys
from pathlib import Path

from setuptools import setup

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.packaging.build_support import PublicSdist, ResourceBuild  # noqa: E402

setup(cmdclass={"build_py": ResourceBuild, "sdist": PublicSdist})
