"""Stop only a child process tree started by this application."""

import os
import shutil
import signal
import subprocess
import sys


def stop_process_tree(process: subprocess.Popen[bytes]) -> None:
    if sys.platform == "win32":
        taskkill = shutil.which("taskkill")
        if taskkill:
            subprocess.run([taskkill, "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
        else:
            process.kill()
    else:
        os.killpg(process.pid, signal.SIGKILL)
