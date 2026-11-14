"""Minimal synthetic worker that stalls after a completed checkpoint."""

import json
import sys
from pathlib import Path
from time import sleep

from filelock import FileLock

folder = Path(sys.argv[1])
request = json.loads((folder / "request.json").read_text(encoding="utf-8"))
graph = {
    "nodes": [{"id": request["symbol"], "name": "Explicit synthetic target", "type": "stock"}],
    "edges": [],
    "summary": {},
    "symbol": request["symbol"],
    "market": request["market"],
    "is_mock": True,
    "stage": "Controlled stalled source",
    "mode": "rules",
}
(folder / "checkpoint.json").write_text(json.dumps(graph), encoding="utf-8")
if len(sys.argv) > 2:
    with FileLock(str(folder.parent.parent / "provider_locks/eastmoney.lock"), timeout=60):
        sleep(60)
sleep(60)
