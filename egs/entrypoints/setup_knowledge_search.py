"""Install the locked lexical search package entirely inside this project."""

import os
import shutil
import subprocess

from loguru import logger

from src.core.config import PROJECT_ROOT


def main() -> None:
    source = PROJECT_ROOT / "egs/requirements/zvec-grep"
    destination = PROJECT_ROOT / ".tools/zvec-grep"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("package.json", "package-lock.json"):
        shutil.copyfile(source / name, destination / name)
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm or not shutil.which("node") or not shutil.which("rg"):
        raise RuntimeError("请先安装Node.js 22+、npm及ripgrep，并加入PATH")
    subprocess.run(
        [
            npm,
            "ci",
            "--prefix",
            str(destination),
            "--ignore-scripts",
            "--omit=optional",
            "--cache",
            str(PROJECT_ROOT / ".tools/npm-cache"),
            "--no-fund",
            "--no-audit",
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )
    logger.info("zvec-grep关键词检索依赖已安装：{}", destination)


if __name__ == "__main__":
    main()
