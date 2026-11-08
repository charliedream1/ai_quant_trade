"""Install the locked lexical search package in the configured tools directory."""

import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

from loguru import logger

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from src.core.config import PROJECT_ROOT  # noqa: E402
from src.core.tool_paths import tools_root  # noqa: E402


def main() -> None:
    source = PROJECT_ROOT / "egs/requirements/zvec-grep"
    destination = tools_root() / "zvec-grep"
    cache = tools_root() / "npm-cache"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("package.json", "package-lock.json"):
        shutil.copyfile(source / name, destination / name)
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm or not shutil.which("node") or not shutil.which("rg"):
        raise RuntimeError("请先安装Node.js 22+、npm及ripgrep，并加入PATH")
    subprocess.run(  # nosec B603
        [
            npm,
            "ci",
            "--prefix",
            str(destination),
            "--ignore-scripts",
            "--omit=optional",
            "--cache",
            str(cache),
            "--no-fund",
            "--no-audit",
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )
    logger.info("zvec-grep关键词检索依赖已安装：{}", destination)


if __name__ == "__main__":
    main()
