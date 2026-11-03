"""Result composition and explicit pagination; never recompute model metrics."""

from copy import deepcopy
from typing import Any

from .client import Client
from .errors import CliError


def request_data(client: Client, path: str) -> dict[str, Any]:
    return client.request({"method": "GET", "path": path, "query": {}, "body": {}})


def collect(client: Client, request: dict[str, Any], definition: dict[str, Any], options: Any) -> dict[str, Any]:
    if options.all and (
        not {"page", "page_size"}.issubset(definition.get("query", {}))
        or "page" in definition.get("unsupported_query", [])
    ):
        raise CliError("该接口不支持自动分页")
    limit = options.max_items if options.max_items is not None else client.config["limits"]["max_items"]
    if limit <= 0:
        raise CliError("max-items 必须为正数")
    current = deepcopy(request)
    if options.all:
        current["query"].setdefault("page", 1)
        current["query"].setdefault("page_size", min(limit, client.config["limits"]["page_size"]))
    rows: list[Any] = []
    seen = set()
    while True:
        result = client.request(
            current,
            execution=definition.get("execution", False),
            upload=options.file if definition.get("upload") else None,
        )
        if not options.all or result["code"] != 0:
            return result
        data = result["data"]
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise CliError("接口未返回预期分页结构")
        added = 0
        for item in data["items"]:
            key = repr(item.get("id", item.get("task_id", item))) if isinstance(item, dict) else repr(item)
            if key not in seen:
                seen.add(key)
                rows.append(item)
                added += 1
        more = len(data["items"]) >= int(current["query"]["page_size"]) and int(current["query"]["page"]) * int(
            current["query"]["page_size"]
        ) < int(data.get("total", len(rows) + 1))
        if len(rows) >= limit or not more or not added:
            result["data"] = {**data, "items": rows[:limit]}
            result["meta"].update(
                truncated=len(rows) > limit or more, returned=len(rows[:limit]), consistent_snapshot=False
            )
            return result
        current["query"]["page"] += 1


def compose(client: Client, args: Any, options: Any) -> dict[str, Any]:
    if args._command_name == "backtest compare":
        try:
            ids = [int(value) for value in str(options.ids or "").split(",")]
        except ValueError as exc:
            raise CliError("compare 需要 --ids 逗号分隔的正整数") from exc
        rows = []
        for task_id in ids:
            if task_id <= 0:
                raise CliError("任务 ID 必须为正数")
            task = request_data(client, f"/backtests/{task_id}")
            metrics = request_data(client, f"/backtests/{task_id}/performance")
            for result in (task, metrics):
                if result["code"] != 0:
                    return result
            rows.append({"task": task["data"], "metrics": metrics["data"]})
        return {"code": 0, "message": "保留日期、股票池、执行和数据来源差异，请核对可比条件", "data": rows}
    result = request_data(client, f"/backtests/{args.task_id}")
    if result["code"] == 0:
        result["data"] = result["data"].get("parameter_snapshot") or {
            "legacy": True,
            "message": "历史任务未保存完整快照",
            "params": result["data"].get("params"),
        }
    return result


def real_evidence(value: Any) -> tuple[bool, bool]:
    """Return (has_source, contains_mock) from source fields, not user prose."""
    found = False
    mocked = False
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "status" and isinstance(item, str) and item in {"mock", "mock-disabled"}:
                found = mocked = True
            if (
                key in {"data_source", "source_name", "model"} or (key == "source" and "fingerprint" in value)
            ) and isinstance(item, str):
                found |= bool(item.strip() and item.strip().lower() not in {"-", "unknown", "none"})
                mocked |= "mock" in item.lower() or "synthetic" in item.lower() or "fixture" in item.lower()
            if key == "is_mock" and isinstance(item, bool):
                found = True
                mocked |= item
            subfound, submocked = real_evidence(item)
            found |= subfound
            mocked |= submocked
    elif isinstance(value, list):
        for item in value:
            subfound, submocked = real_evidence(item)
            found |= subfound
            mocked |= submocked
    return found, mocked
