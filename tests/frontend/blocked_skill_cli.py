"""Declared silent CLI with a child holding its inherited pipes and a file lock."""

import subprocess
import sys
from pathlib import Path
from time import sleep

from filelock import FileLock

root = Path(sys.argv[1])
if len(sys.argv) > 2:
    with FileLock(str(root / "child.lock")):
        (root / "child-ready").write_text("ready", encoding="utf-8")
        sleep(120)
else:
    sys.stdin.read()
    subprocess.Popen([sys.executable, __file__, str(root), "child"])
    sleep(120)
