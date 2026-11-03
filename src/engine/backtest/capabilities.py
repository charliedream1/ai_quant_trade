"""Resolve execution capabilities using the loaded port and frozen composition binding."""

from typing import Any

from src.core.exceptions import BusinessError, ErrorCode
from src.core.repository import Repository
from src.strategy import StrategyLoader, StrategyStore
from src.strategy.execution_policy import execution_kind
from src.strategy.validator import StrategyValidator

from .engines import normalize_engine_key


def strategy_capability(strategy_id: int, params: dict[str, Any], repo: Repository) -> dict[str, Any]:
    row = repo.get("strategies", strategy_id)
    storage = StrategyStore(repo=repo).storage
    path = storage.resolve(row["file_path"])
    kind = execution_kind(path)
    if kind == "reviewed_worker":
        validation = StrategyValidator().validate_source(path.read_text(encoding="utf-8"))
        return {
            "order_type": "market",
            "warmup": False,
            "execution": {},
            "risk": {},
            "engine": "simple",
            "entry": validation.get("entry_class") or validation.get("entry_func"),
            "pipeline_id": None,
            "version": row.get("version"),
            "capabilities": validation["capabilities"],
        }
    adapter = StrategyLoader(storage).load_from_file(row["file_path"], params=params).adapter
    composition = adapter.entry_name == "CompositePipelineStrategy"
    version = None
    if composition:
        from src.strategy.composition.store import PipelineStore

        store = PipelineStore(repo=repo)
        version = store.version(int(params["pipeline_version"]), True)
        if int(version["pipeline_id"]) != int(params["pipeline_id"]) or int(version["strategy_id"]) != strategy_id:
            raise BusinessError(ErrorCode.INVALID_PARAM, "组合策略与冻结版本绑定不一致")
    runtime = getattr(getattr(adapter, "instance", None), "runtime", None)
    return {
        "order_type": getattr(runtime, "required_order_type", "market"),
        "warmup": callable(getattr(runtime, "warmup", None)),
        "execution": version["compiled"]["execution"] if version else {},
        "risk": version["compiled"]["risk"] if version else {},
        "engine": "composition" if composition else "simple",
        "entry": adapter.entry_name,
        "pipeline_id": params.get("pipeline_id") if composition else None,
        "version": version["id"] if version else row.get("version"),
        "capabilities": adapter.capabilities,
    }


def resolve_engine(requested: Any, capability: dict[str, Any]) -> str:
    engine = capability["engine"] if requested in (None, "", "auto") else normalize_engine_key(requested)
    if (capability["engine"] == "composition") != (engine == "composition"):
        raise BusinessError(
            ErrorCode.INVALID_PARAM, f"该策略需要{capability['engine']}引擎；请选择“跟随策略”或兼容引擎"
        )
    if engine == "qlib":
        from src.engine.research.qlib_workflow import QlibWorkflowService

        status = QlibWorkflowService().status()
        if not status.get("ready"):
            raise BusinessError(
                ErrorCode.CONFIG_DEPENDENCY,
                str(status.get("blocker") or status.get("next_step") or "Qlib Workflow/provider 尚未配置完整"),
            )
    return engine
