"""Project-local jobs survive for inspection; processes do not become daemons."""

import json
import os
from pathlib import Path
from threading import RLock
from time import time
from uuid import UUID

from src.core.config import get_settings
from src.core.exceptions import BusinessError, ErrorCode

from .catalog import settings

LOCK = RLock()


class SkillRunStore:
    def __init__(self):
        self.root = (get_settings().data_dir / "skill_runs").resolve()
        if not self.root.is_relative_to(get_settings().project_root.resolve()):
            raise ValueError("Skill运行目录必须位于本项目内")

    def directory(self, run_id: str) -> Path:
        try:
            if UUID(run_id).hex != run_id:
                raise ValueError("非法Skill运行ID")
        except (ValueError, TypeError, AttributeError) as exc:
            raise BusinessError(ErrorCode.INVALID_PARAM, "非法Skill运行ID") from exc
        directory = (self.root / run_id).resolve()
        if not directory.is_relative_to(self.root):
            raise BusinessError(ErrorCode.INVALID_PARAM, "Skill运行路径越界")
        return directory

    def save(self, row: dict) -> dict:
        directory = self.directory(row["run_id"])
        directory.mkdir(parents=True, exist_ok=True)
        with LOCK:
            target = directory / "state.json"
            pending = directory / "state.pending"
            pending.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(pending, target)
        return row

    def get(self, run_id: str) -> dict:
        with LOCK:
            path = self.directory(run_id) / "state.json"
            if not path.is_file():
                raise BusinessError(ErrorCode.NOT_FOUND, "Skill运行不存在")
            row = json.loads(path.read_text(encoding="utf-8"))
            heartbeat = path.with_name("heartbeat")
            if (
                row["status"] == "running"
                and heartbeat.is_file()
                and time() - heartbeat.stat().st_mtime > settings()["limits"]["stale_seconds"]
            ):
                row.update(status="interrupted", error=settings()["messages"]["interrupted"])
                self.save(row)
            return row

    def heartbeat(self, run_id: str) -> None:
        (self.directory(run_id) / "heartbeat").touch()

    def event(self, run_id: str, kind: str, payload) -> None:
        with LOCK, (self.directory(run_id) / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"kind": kind, "data": payload}, ensure_ascii=False) + "\n")

    def events(self, run_id: str) -> list[dict]:
        self.get(run_id)
        path = self.directory(run_id) / "events.jsonl"
        with LOCK:
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    def cancel(self, run_id: str) -> dict:
        row = self.get(run_id)
        if row["status"] == "running":
            (self.directory(run_id) / "cancel.requested").write_text("cancel", encoding="utf-8")
        return {"run_id": run_id, "requested": row["status"] == "running"}

    def cancelled(self, run_id: str) -> bool:
        return (self.directory(run_id) / "cancel.requested").is_file()

    def files(self, run_id: str) -> list[dict]:
        self.get(run_id)
        return [
            {"name": path.name, "path": str(path), "bytes": path.stat().st_size}
            for path in sorted(self.directory(run_id).iterdir())
            if path.is_file() and path.resolve().is_relative_to(self.root)
        ]
