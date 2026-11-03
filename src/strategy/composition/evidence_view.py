"""Read saved scoped node evidence without executing or regenerating a strategy."""

from typing import Any

from src.strategy.composition.event_index import indexed_events, preview
from src.strategy.composition.graph_config import graph_config
from src.strategy.composition.service import PipelineService


def evidence(run_id: str, after: int = 0) -> dict[str, Any]:
    if not run_id:
        return {}
    service = PipelineService()
    row = service.detail(run_id)
    version = service.store.version(row["version_id"])
    result = row.get("result") or {}
    nodes: dict[str, dict] = {}

    def collect(value, path="main"):
        for stage in value.get("stages") or []:
            key = path + "/" + stage["node"]
            nodes.setdefault(key, {"stages": [], "events": []})["stages"].append(stage)
        for key, detail in (value.get("model_diagnostics") or {}).items():
            nodes.setdefault(path + "/" + key, {"stages": [], "events": []})["model"] = detail
        for key, detail in (value.get("factor_diagnostics") or {}).items():
            nodes.setdefault(path + "/" + key, {"stages": [], "events": []})["factor_research"] = detail
        for decision in value.get("decisions") or []:
            key = str(decision.get("node") or "").replace(":", "/")
            nodes.setdefault(key, {"stages": [], "events": []})["decision"] = decision
        for key, child in (value.get("children") or {}).items():
            collect(child, key)
        for kind in ("portfolio", "risk", "execution"):
            nodes.setdefault(path + "/@" + kind, {"stages": [], "events": []})["allocations"] = value.get(
                "allocations", []
            )[-graph_config()["limits"]["evidence_rows"] :]

    collect(result.get("diagnostics") or {})
    cursor, events = indexed_events(service.store, run_id)
    if after < 0 or after > cursor:
        raise ValueError("Invalid event cursor")
    for event in events:
        data = event.get("data")
        if not isinstance(data, dict):
            continue
        node = data.get("node") or (event["text"] if event["kind"] in {"stage", "model_fit", "model_cache"} else "")
        if not node:
            continue
        scope = data.get("scope")
        if scope is None and version["compiled"].get("sleeves"):
            continue  # Old unscoped events cannot be assigned to a child honestly.
        key = str(scope or "main") + "/" + str(node)
        record = nodes.setdefault(key, {"stages": [], "events": []})
        record["events"].append(event)
        if event["kind"] == "stage" and data.get("status") == "completed":
            record["stages"].append(data)
    for detail in nodes.values():
        detail["events"] = [event for event in detail["events"] if event.get("sequence", 0) > after][
            -graph_config()["limits"]["evidence_rows"] :
        ]
        detail["stages"] = detail["stages"][-graph_config()["limits"]["evidence_rows"] :]
    return preview(
        {
            "run_id": run_id,
            "status": row["status"],
            "definition_digest": version["digest"],
            "nodes": nodes,
            "error": result.get("error", ""),
            "dates": (result.get("curve") or {}).get("dates", []),
            "cursor": cursor,
            "events_after": after,
            "preview_limits": graph_config()["limits"]["event_preview_items"],
        }
    )
