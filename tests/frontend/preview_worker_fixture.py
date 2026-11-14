"""A real owned converter substitute that waits while holding a source lock."""

import json
import os
import sys
from pathlib import Path
from threading import Event

from filelock import FileLock

folder = Path(sys.argv[1])
with FileLock(str(folder / "preview-source.lock")):
    (folder / "preview-started.json").write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    Event().wait(120)
