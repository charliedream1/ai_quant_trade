"""Project-bounded task state and append-only actual execution events."""

import json
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import UUID

from loguru import logger

from src.core.config import get_settings
from src.core.timeutil import utc_now_iso
from src.notifications.service import report_saved

from .config import insight_config

STORE_LOCK = RLock()


class InsightStore:
    def __init__(self, root: Path | None = None):
        self.root = (root or get_settings().data_dir / "reports" / "insights").resolve()
        if not self.root.is_relative_to(get_settings().project_root.resolve()):
            raise ValueError(insight_config()["messages"]["bad_resource"])
        self.root.mkdir(parents=True, exist_ok=True)

    def directory(self, run_id: str) -> Path:
        try:
            key = UUID(run_id).hex
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(insight_config()["messages"]["bad_resource"]) from exc
        return self.root / key

    def save(self, report: dict[str, Any]) -> None:
        directory = self.directory(report["run_id"])
        directory.mkdir(parents=True, exist_ok=True)
        with STORE_LOCK:
            (directory / "run.json").write_text(
                json.dumps(report, ensure_ascii=False, allow_nan=False), encoding="utf-8"
            )
        if report.get("status") in {"completed", "partial", "failed"}:
            report_saved(report)

    def detail(self, run_id: str) -> dict[str, Any]:
        with STORE_LOCK:
            path = self.directory(run_id) / "run.json"
            if not path.is_file():
                raise ValueError(insight_config()["messages"]["not_found"])
            return dict(json.loads(path.read_text(encoding="utf-8")))

    def append(self, run_id: str, kind: str, text: str, data: Any = None) -> dict[str, Any]:
        path = self.directory(run_id) / "events.jsonl"
        event = {"time": utc_now_iso(), "kind": kind, "text": text, "data": data}
        with STORE_LOCK:
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
        return event

    def events(self, run_id: str) -> list[dict[str, Any]]:
        path = self.directory(run_id) / "events.jsonl"
        with STORE_LOCK:
            if not path.is_file():
                return []
            rows = []
            for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict) or not all(key in row for key in ("time", "kind", "text")):
                        raise ValueError("invalid event shape")
                    rows.append(row)
                except ValueError:
                    logger.warning("忽略无法读取的报告事件 | run={} line={}", run_id, index + 1)
            return rows

    def history(self, limit: int) -> list[dict[str, Any]]:
        rows = []
        candidates = []
        for path in self.root.glob("*/run.json"):
            try:
                candidates.append((path.stat().st_mtime, path))
            except OSError:
                continue
        for _, path in sorted(candidates, key=lambda item: item[0], reverse=True):
            try:
                row = self.detail(path.parent.name)
                if (
                    self.directory(row["run_id"]) != path.parent
                    or not isinstance(row["created_at"], str)
                    or row["status"] not in {"running", "completed", "partial", "failed"}
                    or not isinstance(row["request"]["kind"], str)
                ):
                    raise ValueError("invalid report shape")
                rows.append(row)
                if len(rows) >= limit:
                    break
            except (OSError, ValueError, KeyError, TypeError):
                logger.warning("忽略无法读取的报告记录 | path={}", path)
                continue
        return rows

    def artifact(self, run_id: str, name: str) -> Path:
        if name not in {"report.html", "events.jsonl", "evidence.json", "request.json", "prompt.txt", "report.json"}:
            raise ValueError(insight_config()["messages"]["bad_resource"])
        directory = self.directory(run_id)
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or not path.is_file():
            raise ValueError(insight_config()["messages"]["not_found"])
        return path
