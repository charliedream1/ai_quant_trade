"""Auditable multi-agent review of an existing backtest, without order access."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

import yaml

from src.agent.llm_client import LLMClient
from src.agent.providers import provider_snapshot
from src.agent.providers.contracts import merge_selection
from src.agent.research_protocol import run_role
from src.core.config import PROJECT_ROOT, get_settings
from src.core.exceptions import BusinessError, ErrorCode
from src.core.logger import get_logger
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.data.etf import ETFUniverseService
from src.engine.backtest import BacktestRunner

CONFIG_PATH = PROJECT_ROOT / "egs" / "research_team.yaml"
LOG = get_logger("agent.research_team")
ROLE_ORDER = ("analyst", "risk", "reviewer", "chair")


class ResearchTeam:
    def __init__(self, repo: Repository | None = None, llm: LLMClient | None = None) -> None:
        self.repo = repo or Repository()
        self.llm = llm or LLMClient(repo=self.repo)
        self.config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

    def run(
        self,
        backtest_id: int,
        objective: str,
        model_id: int | None = None,
        workflow: str = "backtest_review",
        provider: dict | None = None,
        role_models: dict | None = None,
        cancelled=None,
    ) -> dict[str, Any]:
        return list(self.run_stream(backtest_id, objective, model_id, workflow, provider, role_models, cancelled))[-1]

    def run_stream(
        self,
        backtest_id: int,
        objective: str,
        model_id: int | None = None,
        workflow: str = "backtest_review",
        provider: dict | None = None,
        role_models: dict | None = None,
        cancelled=None,
    ):
        if not str(objective).strip() or len(str(objective)) > int(self.config["max_summary_chars"]):
            raise BusinessError(ErrorCode.INVALID_PARAM, "研究目标不能为空或超过长度限制")
        workflow = str(workflow or "backtest_review").strip()
        if workflow not in {"backtest_review", "etf_review"}:
            raise BusinessError(ErrorCode.INVALID_PARAM, f"不支持的多 Agent 工作流：{workflow}")
        evidence = self._evidence(backtest_id, workflow)
        workflow_config = self._workflow_config(workflow)
        provider = provider or {"backend": "api", "model_id": model_id}
        selections = {role: merge_selection(provider, (role_models or {}).get(role, {})) for role in ROLE_ORDER}
        if set(role_models or {}) - set(ROLE_ORDER):
            raise ValueError("未知研究角色")
        started = perf_counter()
        report: dict[str, Any] = {
            "run_id": uuid4().hex,
            "backtest_id": backtest_id,
            "objective": objective,
            "workflow": workflow,
            "created_at": utc_now_iso(),
            "status": "running",
            "roles": {},
            "events": [],
            "evidence": evidence,
            "hard_flags": self._hard_flags(evidence),
            "can_trade": False,
            "providers": {
                role: provider_snapshot(value, client=self.llm, probe=value.get("backend") != "api")
                for role, value in selections.items()
            },
        }
        self._save(report)
        yield deepcopy(report)
        try:
            for role in ROLE_ORDER:
                report["events"].append({"role": role, "status": "running", "time": utc_now_iso()})
                yield deepcopy(report)

                def emit(kind, payload):
                    report["events"].append({"kind": kind, **payload, "time": utc_now_iso()})
                    self._save(report)

                result = run_role(
                    role,
                    objective,
                    evidence,
                    dict(report["roles"]),
                    workflow_config,
                    self.llm,
                    model_id,
                    selections[role],
                    emit,
                    cancelled,
                    report["providers"][role],
                )
                report["roles"][role] = result
                report["events"].append({"role": role, "status": "finished", "time": utc_now_iso()})
                LOG.info(
                    "research role completed | run_id={} role={} verdict={}", report["run_id"], role, result["verdict"]
                )
                self._save(report)
                yield deepcopy(report)
            verdicts = [value["verdict"] for value in report["roles"].values()]
            report["verdict"] = (
                "reject"
                if "reject" in verdicts
                else "watch"
                if report["hard_flags"] or "watch" in verdicts
                else "approve"
            )
            report["status"] = "finished"
        except Exception as exc:
            report.update(status="failed", verdict="reject", error=str(exc))
            LOG.warning("research team failed | run_id={} error={}", report["run_id"], exc)
        report["duration_ms"] = round((perf_counter() - started) * 1000)
        self._save(report)
        yield deepcopy(report)

    def _workflow_config(self, workflow: str) -> dict[str, Any]:
        config = deepcopy(self.config)
        if workflow == "etf_review":
            selected = config.get("workflows", {}).get("etf_review") or {}
            config["roles"] = selected.get("roles") or config["roles"]
            config["prompt"] = selected.get("prompt") or config["prompt"]
            for key in ("max_tool_calls", "max_turns"):
                if selected.get(key) is not None:
                    config[key] = selected[key]
        return config

    def _evidence(self, backtest_id: int, workflow: str = "backtest_review") -> dict[str, Any]:
        runner = BacktestRunner(repo=self.repo)
        task = runner.detail(backtest_id)
        if task["status"] != "finished":
            raise ValueError("请选择已完成的回测")
        metrics = runner.performance(backtest_id)
        evidence = {
            "task": task,
            "metrics": {key: value for key, value in metrics.items() if key != "model_diagnostics"},
            "model": metrics.get("model_diagnostics") or {},
            "attribution": runner.attribution(backtest_id),
            "trades": runner.trades(backtest_id, page_size=100),
        }
        if workflow == "etf_review" or metrics.get("asset_type") == "etf":
            params = (task.get("parameter_snapshot") or {}).get("resolved_params") or {}
            try:
                evidence["etf"] = ETFUniverseService().snapshot(str(params.get("universe") or "cn_core"))
            except Exception as exc:
                evidence["etf"] = {"status": "unavailable", "error": str(exc)}
        return evidence

    def _hard_flags(self, evidence: dict[str, Any]) -> list[str]:
        metrics = evidence["metrics"]
        flags = []
        if str(metrics.get("data_source") or "").startswith(("mock", "synthetic")):
            flags.append("当前为合成数据，只能验证流程")
        if int(metrics.get("trade_count") or 0) < int(self.config["rules"]["minimum_trades"]):
            flags.append("交易样本不足")
        if abs(float(metrics.get("max_drawdown") or 0)) > float(self.config["rules"]["maximum_drawdown"]):
            flags.append("最大回撤超过研究阈值")
        if self.config["rules"]["require_fitted_model"] and not (evidence["model"].get("fit_count") or 0):
            flags.append("缺少真实模型训练证据")
        if "etf" in evidence:
            if int(evidence["etf"].get("available_count") or 0) <= 0:
                flags.append("ETF 池没有可验证的行情快照")
            if metrics.get("asset_type") == "etf" and metrics.get("tracking_error") is None:
                flags.append("ETF 跟踪误差证据缺失")
        return flags

    def _directory(self) -> Path:
        return get_settings().data_dir / "reports" / "research_team"

    def _save(self, report: dict[str, Any]) -> None:
        directory = self._directory()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{report['run_id']}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    def detail(self, run_id: str) -> dict[str, Any]:
        try:
            key = UUID(run_id).hex
        except ValueError as exc:
            raise BusinessError(ErrorCode.INVALID_PARAM, "复核运行标识格式无效") from exc
        path = self._directory() / f"{key}.json"
        if not path.is_file():
            raise BusinessError(ErrorCode.NOT_FOUND, "复核报告不存在")
        return json.loads(path.read_text(encoding="utf-8"))
