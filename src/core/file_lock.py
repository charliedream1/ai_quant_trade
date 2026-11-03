"""Cross-process advisory locks for short project configuration read/modify/write."""

import importlib
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

locker: Any = importlib.import_module("msvcrt" if os.name == "nt" else "fcntl")


@contextmanager
def file_lock(target: Path, timeout: float = 15):
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.with_name(target.name + ".lock").open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        started = time.monotonic()
        while True:
            try:
                if os.name == "nt":
                    stream.seek(0)
                    locker.locking(stream.fileno(), locker.LK_NBLCK, 1)
                else:
                    locker.flock(stream.fileno(), locker.LOCK_EX | locker.LOCK_NB)
                break
            except OSError:
                if time.monotonic() - started >= timeout:
                    raise TimeoutError("配置文件正被其他任务更新") from None
                time.sleep(0.025)
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                locker.locking(stream.fileno(), locker.LK_UNLCK, 1)
            else:
                locker.flock(stream.fileno(), locker.LOCK_UN)
