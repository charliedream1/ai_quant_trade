"""Append-only published plans, optimistic paper states and project-contained artifacts."""

import json
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import UUID

import yaml

from src.core.config import PROJECT_ROOT, get_settings
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso
from src.strategy.strategy_store import StrategyStore

from .config import CONFIG_PATH, config, fail
from .validation import compile_plan, digest

LOCK = RLock()


def source_manifest() -> dict[str, str]:
    roots = [
        PROJECT_ROOT / "src" / p
        for p in (
            "strategy/composition",
            "alpha_mining",
            "agent_strategies",
            "strategy/components",
            "strategy/factors",
            "portfolio",
            "risk",
            "engine/composition",
            "engine/execution",
        )
    ]
    files = [
        PROJECT_ROOT / "egs/execution_costs.yaml",
        PROJECT_ROOT / "egs/alpha_mining.yaml",
        PROJECT_ROOT / "egs/alpha_mining_prompts.yaml",
        PROJECT_ROOT / "egs/agent_strategies.yaml",
        PROJECT_ROOT / "egs/agent_strategy_prompts.yaml",
        PROJECT_ROOT / "src/data/backtest_history.py",
        PROJECT_ROOT / "egs/backtest.yaml",
        PROJECT_ROOT / "src/agent/decision_team.py",
        PROJECT_ROOT / "src/engine/insights/backend.py",
        PROJECT_ROOT / "src/strategy/codex_cli.py",
        PROJECT_ROOT / "src/data/eastmoney.py",
        PROJECT_ROOT / "egs/model_strategies.yaml",
        PROJECT_ROOT / "egs/strategy_entrypoints/composition.py",
    ]
    files.extend((PROJECT_ROOT / "src/strategy/models").glob("*.py"))
    files.extend(path for root in roots for path in root.rglob("*.py"))
    result = {
        path.relative_to(PROJECT_ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in sorted(files)
        if path.is_file()
    }
    settings = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    result["egs/strategy_components.yaml:computation"] = digest(
        {key: value for key, value in settings.items() if key not in {"ui", "messages"}}
    )
    factors = yaml.safe_load((PROJECT_ROOT / "egs/factor_research.yaml").read_text(encoding="utf-8"))
    result["egs/factor_research.yaml:computation"] = digest(
        {key: value for key, value in factors.items() if key not in {"cache", "messages"}}
    )
    return result


class PipelineStore:
    def __init__(self, repo: Repository | None = None):
        self.repo = repo or Repository()
        self.repo.db.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        self.root = (get_settings().data_dir / "reports/pipelines").resolve()
        if not self.root.is_relative_to(PROJECT_ROOT.resolve()):
            raise fail("invalid", "artifact root")
        self.root.mkdir(parents=True, exist_ok=True)

    def catalog(self) -> list[dict[str, Any]]:
        return [
            {**row, "definition": json_loads(row["definition"], {})} for row in self.repo.list("strategy_pipelines")
        ]

    def set_enabled(self, pipeline_id: int, enabled: bool) -> dict[str, Any]:
        row = self.repo.update(
            "strategy_pipelines",
            pipeline_id,
            {"status": "published" if enabled else "disabled", "updated_at": utc_now_iso()},
        )
        return {**row, "definition": json_loads(row["definition"], {})}

    def save_draft(self, definition: dict[str, Any], pipeline_id: int | None = None) -> dict[str, Any]:
        compile_plan(definition)
        now = utc_now_iso()
        values = {
            "name": definition["name"],
            "definition": json.dumps(definition, ensure_ascii=False),
            "status": "draft",
            "updated_at": now,
        }
        if pipeline_id:
            row = self.repo.update("strategy_pipelines", pipeline_id, values)
        else:
            row = self.repo.insert("strategy_pipelines", {**values, "created_at": now})
        return {**row, "definition": definition}

    def publish(self, pipeline_id: int) -> dict[str, Any]:
        with LOCK:
            row = self.repo.get("strategy_pipelines", pipeline_id)
            definition = json_loads(row["definition"], {})
            compiled = compile_plan(definition)
            version = (
                int(
                    self.repo.db.scalar(
                        "SELECT COALESCE(MAX(version),0) FROM strategy_pipeline_versions WHERE pipeline_id=?",
                        (pipeline_id,),
                    )
                )
                + 1
            )
            value = self.repo.insert(
                "strategy_pipeline_versions",
                {
                    "pipeline_id": pipeline_id,
                    "version": version,
                    "definition": json.dumps(definition, ensure_ascii=False),
                    "compiled": json.dumps(compiled, ensure_ascii=False),
                    "digest": digest(compiled),
                    "manifest": json.dumps(source_manifest()),
                    "created_at": utc_now_iso(),
                },
            )
            source = (PROJECT_ROOT / config()["defaults"]["entrypoint"]).read_text(encoding="utf-8")
            strategy = StrategyStore(repo=self.repo).create(
                {
                    "name": f"{compiled['name']}#{value['id']}",
                    "code": source,
                    "description": compiled.get("description", ""),
                    "version": str(version),
                    "status": "可用",
                    "tags": ["组合"],
                    "default_params": {"pipeline_id": pipeline_id, "pipeline_version": value["id"]},
                },
                origin="组合方案",
            )
            self.repo.update("strategy_pipeline_versions", value["id"], {"strategy_id": strategy["strategy_id"]})
            self.repo.update("strategy_pipelines", pipeline_id, {"status": "published", "updated_at": utc_now_iso()})
            return self.version(value["id"])

    def version(self, version_id: int, verify: bool = False) -> dict[str, Any]:
        row = self.repo.get("strategy_pipeline_versions", version_id)
        for key in ("compiled", "definition", "manifest"):
            row[key] = json_loads(row[key], {})
        if digest(row["compiled"]) != row["digest"] or verify and row["manifest"] != source_manifest():
            raise fail("invalid", "published source/config changed; publish a new version")
        if verify and row.get("strategy_id"):
            strategy = StrategyStore(repo=self.repo).get(row["strategy_id"])
            original = (PROJECT_ROOT / config()["defaults"]["entrypoint"]).read_text(encoding="utf-8")
            if strategy["code"] != original:
                raise fail("invalid", "published strategy entrypoint changed")
        return row

    def versions(self, pipeline_id: int) -> list[dict[str, Any]]:
        return [
            self.version(row["id"])
            for row in self.repo.list(
                "strategy_pipeline_versions", "pipeline_id=?", (pipeline_id,), order_by="version DESC"
            )
        ]

    def directory(self, run_id: str) -> Path:
        try:
            key = UUID(run_id).hex
        except (ValueError, TypeError, AttributeError) as exc:
            raise fail("invalid", "run_id") from exc
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise fail("invalid", "run path")
        return path

    def artifact(self, run_id: str, name: str) -> Path:
        if name not in {
            "report.html",
            "result.json",
            "events.jsonl",
            "snapshot.json",
            "request.json",
            "definition.json",
            "ledger.json",
        }:
            raise fail("invalid", "artifact")
        directory = self.directory(run_id)
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or not path.is_file():
            raise fail("missing", name)
        return path

    def write(self, run_id: str, name: str, value: Any) -> None:
        directory = self.directory(run_id)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8"
        )

    def append(self, run_id: str, kind: str, text: str, data: Any = None) -> dict[str, Any]:
        event = {"time": utc_now_iso(), "kind": kind, "text": text, "data": data}
        directory = self.directory(run_id)
        directory.mkdir(parents=True, exist_ok=True)
        with LOCK:
            with (directory / "events.jsonl").open("a", encoding="utf-8") as output:
                output.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
        return event

    def events(self, run_id: str) -> list[dict[str, Any]]:
        with LOCK:
            path = self.directory(run_id) / "events.jsonl"
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    def run(self, run_id: str) -> dict[str, Any]:
        key = self.directory(run_id).name
        row = self.repo.db.query_one("SELECT * FROM strategy_pipeline_runs WHERE id=?", (key,))
        if not row:
            raise fail("missing", key)
        return {**row, "request": json_loads(row["request"], {}), "result": json_loads(row["result"], {})}

    def runs(self, limit: int = 30) -> list[dict[str, Any]]:
        return [
            self.run(row["id"])
            for row in self.repo.list("strategy_pipeline_runs", order_by="created_at DESC", limit=limit)
        ]

    def save_account(self, account_id: int, expected_version: int, state: dict[str, Any], as_of: str) -> None:
        cursor = self.repo.db.execute(
            "UPDATE strategy_pipeline_accounts SET state=?,last_as_of=?,version=version+1,updated_at=? WHERE id=? AND version=?",
            (
                json.dumps(state, ensure_ascii=False, allow_nan=False),
                as_of,
                utc_now_iso(),
                account_id,
                expected_version,
            ),
        )
        if cursor.rowcount != 1:
            raise fail("invalid", "account concurrently changed")
