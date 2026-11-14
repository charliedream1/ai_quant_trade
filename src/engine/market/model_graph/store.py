"""Atomic task records and immutable results inside configured private data."""

import json
import os
from threading import RLock
from uuid import UUID, uuid4

from src.core.config import get_settings
from src.core.timeutil import utc_now_iso

from .config import config

LOCK = RLock()


class GraphStore:
    def __init__(self, directory_name="relation_graph_runs"):
        base = get_settings().data_dir.resolve()
        self.root = (base / directory_name).resolve()
        if not self.root.is_relative_to(base):
            raise ValueError("Graph storage escapes the configured data directory")
        self.root.mkdir(parents=True, exist_ok=True)

    def directory(self, identifier):
        if UUID(str(identifier)).hex != identifier:
            raise ValueError("Invalid graph run ID")
        path = (self.root / identifier).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Graph run directory escapes storage")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save(self, row):
        with LOCK:
            path = self.directory(row["run_id"]) / "run.json"
            pending = path.with_name(uuid4().hex + ".pending")
            pending.write_text(json.dumps(row, ensure_ascii=False, allow_nan=False), encoding="utf-8")
            os.replace(pending, path)

    def get(self, identifier):
        with LOCK:
            path = self.directory(identifier) / "run.json"
            if not path.is_file():
                raise ValueError("Graph run not found")
            return json.loads(path.read_text(encoding="utf-8"))

    def event(self, identifier, kind, data):
        with LOCK, (self.directory(identifier) / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"time": utc_now_iso(), "kind": kind, "data": data}, ensure_ascii=False) + "\n")

    def events(self, identifier):
        path = self.directory(identifier) / "events.jsonl"
        with LOCK:
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    def history(self):
        paths = sorted(self.root.glob("*/run.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        return [self.get(path.parent.name) for path in paths[: config()["limits"]["history"]]]

    def cancel(self, identifier):
        row = self.get(identifier)
        if row["status"] in {"queued", "running"}:
            (self.directory(identifier) / "cancel").touch()
        return row

    def cancelled(self, identifier):
        return (self.directory(identifier) / "cancel").exists()

    def result(self, identifier):
        row = self.get(identifier)
        path = self.directory(identifier) / "graph.json"
        if row["status"] not in {"completed", "partial"} or not path.exists():
            raise ValueError("No completed graph artifact")
        return json.loads(path.read_text(encoding="utf-8"))
