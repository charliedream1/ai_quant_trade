"""Shared graph stages, with exact parent-run and same-date evidence binding."""

from datetime import UTC, datetime, timedelta

from src.alpha_mining.config import digest
from src.core.timeutil import utc_now_iso

from .config import freeze
from .service import AgentStrategyService


def stage(node: dict, frame, incoming: dict, request: dict, emit, repo=None) -> dict:
    service = AgentStrategyService()
    params = node["params"]
    options = {
        **{key: params[key] for key in ("depth", "predictor", "calls")},
        **request.get("agent_strategy_options", {}),
    }
    if node["component"] in {"cn_analysis", "contest_data"}:
        payload = {
            key: request[key]
            for key in (
                "backend",
                "model_id",
                "model_name",
                "reasoning_effort",
                "market",
                "scope",
                "execution_costs",
                "execution_cost_snapshot",
                "execution",
                "risk",
            )
            if key in request
        }
        payload.update(
            scope=request.get("_agent_strategy_scope", request.get("scope", "default")),
            recipe=params["recipe"],
            documents_dataset_id=request.get("agent_documents_dataset_id")
            or (int(params["documents_dataset"]) if params["documents_dataset"] else None),
            options=options,
            symbols=sorted(incoming),
            as_of=frame.as_of,
            validation_mode="historical_research" if request.get("agent_mode") == "research" else "current_research",
        )
        run = service.prepare(payload, frame)
        run = service.phase(
            run["id"], False, frame, emit, request.get("_cancelled"), request.get("_agent_strategy_budget")
        )
        rows = [
            {
                "symbol": s,
                "action": "select",
                "score": float(incoming[s].value or 0),
                "horizon": run["config"]["policy"]["horizon"],
                "reason": "evidence_prepared",
                "evidence_ids": ["E1"],
            }
            for s in sorted(incoming)
        ]
    else:
        identifiers = {row.evidence.get("agent_strategy", {}).get("run_id") for row in incoming.values()}
        if len(identifiers) != 1 or None in identifiers:
            raise ValueError("研究终阶段必须绑定唯一上游证据阶段")
        run = service.store.get(identifiers.pop())
        current = freeze(params["recipe"], options)
        if run["as_of"] != frame.as_of or run["config"]["version"] != current["version"]:
            raise ValueError("阶段时点或冻结研究方案不一致")
        for symbol, rows_in in run["evidence"]["market"]["history"].items():
            if digest(rows_in) != digest(
                [dict(row) for row in frame.history.get(symbol, ())[-run["config"]["limits"]["history_bars"] :]]
            ):
                raise ValueError("研究终阶段的行情与上游不一致")
        run = service.phase(
            run["id"], True, frame, emit, request.get("_cancelled"), request.get("_agent_strategy_budget")
        )
        rows = [{**row, "evidence_ids": ["E1", "E2"]} for row in run["result"]["decision"]["decisions"]]
    now = datetime.now(UTC)
    return {
        "summary": run["config"]["definition"]["name"],
        "decisions": rows,
        "generated_at": utc_now_iso(),
        "valid_until": (now + timedelta(days=run["config"]["policy"]["validity_days"])).isoformat(),
        "as_of": frame.as_of,
        "model": run["config"].get("provider_snapshot", {}),
        "role_providers": run["config"].get("role_model_snapshots", {}),
        "agent_strategy": {
            "run_id": run["id"],
            "recipe": run["recipe"],
            "phase": node["component"],
            "status": run["status"],
            "coverage_status": run["evidence"]["coverage_status"],
        },
    }
