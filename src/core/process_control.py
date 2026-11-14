"""Stop only a child process tree started by this application."""

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path


def _linux_descendants(root: int) -> list[int]:
    """Include children that created their own process session, such as retrieval CLIs."""
    parents: dict[int, list[int]] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            fields = (entry / "stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()
            parents.setdefault(int(fields[1]), []).append(int(entry.name))
        except (OSError, ValueError, IndexError):
            continue
    result = []
    waiting = [root]
    while waiting:
        children = parents.get(waiting.pop(), [])
        result.extend(children)
        waiting.extend(children)
    return result


def stop_process_tree(process: subprocess.Popen[bytes]) -> None:
    if sys.platform == "win32":
        taskkill = shutil.which("taskkill")
        if taskkill:
            subprocess.run([taskkill, "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
        else:
            process.kill()
    else:
        try:
            # Freeze the owner before discovering descendants so it cannot create new work.
            os.kill(process.pid, signal.SIGSTOP)
            if sys.platform.startswith("linux"):
                for pid in reversed(_linux_descendants(process.pid)):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            # A spawn worker may not have created its session yet. Kill only the owned handle.
            try:
                process.kill()
            except ProcessLookupError:
                pass
