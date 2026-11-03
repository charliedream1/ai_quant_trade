"""Bounded run storage and idempotent matured scores; external inputs never select SQL tables."""

import json
import os
from pathlib import Path
from threading import RLock
from uuid import uuid4

from src.alpha_mining.config import contained, digest
from src.core.config import get_settings
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso
from src.documents.access import compact_path

LOCK = RLock()


class StrategyStore:
    def __init__(self, repo=None):
        self.repo = repo or Repository()
        self.repo.db.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        root = contained(get_settings().data_dir / "reports/agent_strategies")
        root.mkdir(parents=True, exist_ok=True)
        self.root = compact_path(root)

    def get(self, run_id: int) -> dict:
        row = self.repo.get("agent_strategy_runs", run_id)
        for key in ("request", "config", "evidence", "result"):
            row[key] = json_loads(row[key], {})
        if digest([row["config"], row["evidence"], row["request"]]) != row["digest"]:
            raise ValueError("研究冻结内容摘要不一致")
        return row

    def create(self, request: dict, cfg: dict, evidence: dict, lineage: str) -> dict:
        stamp = utc_now_iso()
        row = self.repo.insert(
            "agent_strategy_runs",
            {
                "recipe": cfg["recipe"],
                "status": "created",
                "request": request,
                "config": cfg,
                "evidence": evidence,
                "result": {},
                "digest": digest([cfg, evidence, request]),
                "lineage": lineage,
                "as_of": request["as_of"],
                "created_at": stamp,
                "updated_at": stamp,
            },
        )
        return self.get(row["id"])

    def update(self, run_id: int, status: str, result: dict) -> dict:
        self.repo.update(
            "agent_strategy_runs", run_id, {"status": status, "result": result, "updated_at": utc_now_iso()}
        )
        return self.get(run_id)

    def event(self, run_id: int, kind: str, payload: dict) -> dict:
        return self.repo.insert(
            "agent_strategy_events", {"run_id": run_id, "kind": kind, "payload": payload, "created_at": utc_now_iso()}
        )

    def events(self, run_id: int, after: int = 0, limit: int = 300) -> list[dict]:
        return [
            {**row, "payload": json_loads(row["payload"], {})}
            for row in self.repo.db.query(
                "SELECT * FROM agent_strategy_events WHERE run_id=? AND id>? ORDER BY id LIMIT ?",
                (run_id, after, min(max(limit, 1), 1000)),
            )
        ]

    def history(self, limit=30) -> list[dict]:
        return [self.get(row["id"]) for row in self.repo.list("agent_strategy_runs", limit=min(limit, 100))]

    def artifact(self, run_id: int, name: str) -> Path:
        self.get(run_id)
        if Path(name).name != name or name.startswith(".") or not name:
            raise ValueError("产物名称不合法")
        return contained(self.root / str(run_id) / name)

    def write(self, run_id: int, name: str, value) -> Path:
        target = self.artifact(run_id, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
        temporary = target.with_name("write-" + uuid4().hex[:12] + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, target)
        return target
