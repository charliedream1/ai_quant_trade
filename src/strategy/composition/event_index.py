"""Bounded tail indexes avoid reparsing the complete run trace on every UI tick."""

import json
from collections import OrderedDict
from copy import deepcopy
from threading import RLock

from src.strategy.composition.config import config
from src.strategy.composition.graph_config import graph_config
from src.strategy.composition.store import LOCK as TRACE_LOCK

LOCK = RLock()
INDEXES: OrderedDict[str, dict] = OrderedDict()


def preview(value, depth=0):
    limits = graph_config()["limits"]
    if isinstance(value, dict):
        return {key: preview(item, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [preview(item, depth + 1) for item in value[-limits["event_preview_items"] :]]
    if isinstance(value, str) and len(value) > limits["max_text_chars"]:
        return value[: limits["max_text_chars"]] + "…"
    return value


def indexed_events(store, run_id):
    path = store.directory(run_id) / "events.jsonl"
    key = str(path)
    with LOCK:
        index = INDEXES.setdefault(key, {"offset": 0, "cursor": 0, "nodes": {}})
        INDEXES.move_to_end(key)
        while len(INDEXES) > config()["defaults"]["history_limit_runs"]:
            INDEXES.popitem(last=False)
        if path.exists():
            with TRACE_LOCK, path.open(encoding="utf-8") as stream:
                stream.seek(index["offset"])
                while True:
                    start = stream.tell()
                    line = stream.readline()
                    if not line or not line.endswith("\n"):
                        stream.seek(start)
                        break
                    event = json.loads(line)
                    index["cursor"] += 1
                    data = event.get("data")
                    if not isinstance(data, dict):
                        continue
                    node = data.get("node") or (
                        event["text"] if event["kind"] in {"stage", "model_fit", "model_cache"} else ""
                    )
                    if node:
                        identity = (str(data.get("scope") or ""), str(node))
                        values = index["nodes"].setdefault(identity, [])
                        values.append(preview({**event, "sequence": index["cursor"]}))
                        del values[: -graph_config()["limits"]["evidence_rows"]]
                index["offset"] = stream.tell()
        return index["cursor"], deepcopy([event for events in index["nodes"].values() for event in events])
