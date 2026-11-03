"""Local CLI session simulator for supported AI CLI integrations."""

import json
from typing import Any

from src.core.file_storage import FileStorage
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso

CLI_PROVIDERS = {
    "trae": "trae cli",
    "workbuddy": "workbuddy cli",
    "codex": "codex cli",
}
CLI_PROVIDER_ALIASES = {
    "trae_cli": "trae",
    "workbuddy_cli": "workbuddy",
    "codex_cli": "codex",
}


class CliBuilder:
    def __init__(self, repo: Repository | None = None, storage: FileStorage | None = None) -> None:
        self.repo = repo or Repository()
        self.storage = storage or FileStorage()
        self.storage.ensure_dirs()

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now_iso()
        cli_type = self.normalize_cli_type(payload.get("cli_type"))
        requirement = payload.get("requirement") or ""
        log_path = f"logs/cli_{now.replace(':', '').replace('-', '')}.log"
        artifact = "strategies/cli_generated/generated_strategy.py"
        provider_name = CLI_PROVIDERS[cli_type]
        self.storage.write_text(
            log_path,
            "\n".join(
                [
                    f"[{now}] INFO provider: {provider_name}",
                    f"[{now}] INFO session created",
                    f"[{now}] INFO requirement: {requirement}",
                    f"[{now}] INFO artifact: {artifact}",
                    f"[{now}] INFO status: completed",
                ]
            )
            + "\n",
        )
        self.storage.write_text(artifact, self._generated_code(requirement))
        row = self.repo.insert(
            "cli_sessions",
            {
                "cli_type": cli_type,
                "requirement": requirement,
                "status": "completed",
                "strategy_id": None,
                "log_path": log_path,
                "artifacts": json.dumps([artifact], ensure_ascii=False),
                "error_msg": "",
                "created_at": now,
                "finished_at": now,
            },
        )
        return self.status(row["id"])

    def status(self, session_id: int) -> dict[str, Any]:
        row = self.repo.get("cli_sessions", session_id)
        artifacts = json.loads(row.get("artifacts") or "[]")
        return {
            "session_id": row["id"],
            "cli_type": row["cli_type"],
            "cli_name": CLI_PROVIDERS.get(row["cli_type"], row["cli_type"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "finished_at": row.get("finished_at"),
            "elapsed_seconds": 0,
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
        }

    def list_sessions(self, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        result = self.repo.page("cli_sessions", page, page_size, order_by="created_at DESC")
        for item in result["items"]:
            artifacts = json.loads(item.get("artifacts") or "[]")
            item["session_id"] = item["id"]
            item["cli_name"] = CLI_PROVIDERS.get(item.get("cli_type"), item.get("cli_type"))
            item["artifact_count"] = len(artifacts)
            item["artifacts"] = artifacts
        return result

    def retry_session(self, session_id: int) -> dict[str, Any]:
        row = self.repo.get("cli_sessions", session_id)
        retry = self.create_session(
            {
                "cli_type": row["cli_type"],
                "requirement": row["requirement"],
            }
        )
        log_path = self.repo.get("cli_sessions", int(retry["session_id"]))["log_path"]
        text = self.storage.read_text(log_path)
        self.storage.write_text(log_path, f"[{utc_now_iso()}] INFO retry_from: {session_id}\n{text}")
        return self.status(int(retry["session_id"]))

    def logs(self, session_id: int, offset: int = 0, limit: int = 100) -> dict[str, Any]:
        row = self.repo.get("cli_sessions", session_id)
        text = self.storage.read_text(row["log_path"])
        lines = text.splitlines()
        sliced = lines[offset : offset + limit]
        return {
            "logs": [
                {"line_no": offset + idx + 1, "level": "INFO", "content": line, "time": row["created_at"]}
                for idx, line in enumerate(sliced)
            ],
            "next_offset": offset + len(sliced),
            "ended": row["status"] in ("completed", "failed", "cancelled"),
        }

    def artifacts(self, session_id: int) -> list[str]:
        row = self.repo.get("cli_sessions", session_id)
        return json.loads(row.get("artifacts") or "[]")

    def import_artifact(
        self, session_id: int, file_path: str, name: str, description: str, strategy_store
    ) -> dict[str, Any]:
        row = self.repo.get("cli_sessions", session_id)
        code = self.storage.read_text(file_path)
        strategy = strategy_store.create(
            {"name": name, "description": description, "code": code, "status": "草稿"}, origin="CLI 生成"
        )
        self.repo.update("cli_sessions", row["id"], {"strategy_id": strategy["id"]})
        return strategy

    def _generated_code(self, requirement: str) -> str:
        return """from src.strategy.strategy_base import StrategyBase


class GeneratedStrategy(StrategyBase):
    name = "GeneratedStrategy"
    version = "v1"
    description = "Generated from local CLI simulator."
    params_schema = [{"name": "lookback", "type": "int", "default": 20}]

    def on_bar(self, bar):
        if bar.get("close", 0) > bar.get("open", 0):
            return [{"symbol": bar.get("symbol"), "side": "buy", "quantity": 100}]
        return []
"""

    @staticmethod
    def normalize_cli_type(value: Any) -> str:
        text = str(value or "trae").strip().lower().replace(" ", "_").replace("-", "_")
        normalized = CLI_PROVIDER_ALIASES.get(text, text)
        if normalized not in CLI_PROVIDERS:
            return "trae"
        return normalized
