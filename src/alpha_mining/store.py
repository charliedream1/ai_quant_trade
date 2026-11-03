"""Frozen research contracts, complete attempt histories and hash-chained events."""

import json
import os
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from src.core.config import get_settings
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso
from src.documents.access import compact_path

from .config import config, contained, digest, invalid

LOCK = RLock()
JSON_FIELDS = {
    "alpha_studies": ("config", "result"),
    "alpha_datasets": ("payload", "provenance"),
    "alpha_candidates": ("hypothesis", "implementation"),
    "alpha_trials": ("evidence",),
    "alpha_reviews": ("evidence",),
    "alpha_events": ("payload",),
}


class AlphaStore:
    def __init__(self, repo: Repository | None = None):
        self.repo = repo or Repository()
        self.repo.db.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        self.root = contained(get_settings().data_dir / "reports/alpha_mining")
        self.root.mkdir(parents=True, exist_ok=True)
        self.root = compact_path(self.root)

    def get(self, table: str, identifier: int) -> dict[str, Any]:
        row = self.repo.get(table, identifier)
        for field in JSON_FIELDS.get(table, ()):
            row[field] = json_loads(row[field], {})
        if table == "alpha_studies" and digest(row["config"]) != row["digest"]:
            raise invalid("冻结研究配置摘要不一致")
        if table == "alpha_datasets" and digest(row["payload"]) != row["digest"]:
            raise invalid("冻结数据摘要不一致")
        if table == "alpha_candidates" and digest([row["hypothesis"], row["implementation"]]) != row["digest"]:
            raise invalid("冻结假设或实现摘要不一致")
        return row

    def list(self, table: str, study_id: int | None = None) -> list[dict[str, Any]]:
        rows = self.repo.list(
            table,
            "study_id=?" if study_id else "",
            (study_id,) if study_id else (),
            limit=config()["limits"]["event_limit"],
        )
        return [self.get(table, row["id"]) for row in rows]

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        return self.get(table, self.repo.insert(table, values)["id"])

    def event(self, study_id: int, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        with LOCK, self.repo.db.transaction():
            previous = self.repo.db.query_one(
                "SELECT digest FROM alpha_events WHERE study_id=? ORDER BY id DESC LIMIT 1", (study_id,)
            )
            stamp = utc_now_iso()
            prior = previous["digest"] if previous else ""
            return self.insert(
                "alpha_events",
                {
                    "study_id": study_id,
                    "kind": kind,
                    "payload": payload,
                    "previous_digest": prior,
                    "digest": digest([study_id, kind, payload, prior, stamp]),
                    "created_at": stamp,
                },
            )

    def transition(self, study_id: int, expected: set[str], status: str, result: dict | None = None) -> dict:
        with LOCK, self.repo.db.transaction():
            current = self.get("alpha_studies", study_id)
            if current["status"] not in expected:
                raise invalid("研究阶段不允许该操作：" + current["status"])
            values: dict[str, Any] = {"status": status, "updated_at": utc_now_iso()}
            if result is not None:
                values["result"] = result
            self.repo.update("alpha_studies", study_id, values)
            self.event(study_id, "status", {"from": current["status"], "to": status})
            return self.get("alpha_studies", study_id)

    def artifact(self, study_id: int, name: str) -> Path:
        self.get("alpha_studies", study_id)
        if Path(name).name != name or not name or name.startswith("."):
            raise invalid("研究产物名称不合法")
        target = self.root / str(study_id) / name
        checked = contained(target)
        if not checked.is_relative_to(self.root.resolve()):
            raise invalid("研究产物越界")
        return target

    def write(self, study_id: int, name: str, value: Any) -> Path:
        path = self.artifact(study_id, name)
        content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name("write-" + uuid4().hex[:16] + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
        return path

    def verify_events(self, study_id: int) -> bool:
        prior = ""
        for row in self.repo.db.query("SELECT * FROM alpha_events WHERE study_id=? ORDER BY id", (study_id,)):
            payload = json_loads(row["payload"], {})
            if (
                row["previous_digest"] != prior
                or digest([study_id, row["kind"], payload, prior, row["created_at"]]) != row["digest"]
            ):
                return False
            prior = row["digest"]
        return True
