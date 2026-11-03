"""Validate actionable outputs and exact evidence independently from model opinions."""

import math

from .evidence import reference_index, validate_reference


def opinion(value: dict, context: dict) -> dict:
    if not isinstance(value.get("summary"), str) or not value["summary"].strip():
        raise ValueError("角色缺少研究结论")
    validate_reference(value.get("evidence_ids"), reference_index(context), set(value["read_ids"]))
    return value


def decisions(value: dict, context: dict) -> dict:
    market = context["market"]
    candidates, holdings = set(market["candidates"]), set(market["holdings"])
    rows, seen = value.get("decisions"), set()
    if not isinstance(rows, list) or not isinstance(value.get("summary"), str):
        raise ValueError("研究决定结构不合法")
    for row in rows:
        symbol, action, score = row.get("symbol"), row.get("action"), row.get("score")
        if symbol in seen or symbol not in candidates | holdings or action not in {"select", "watch", "reject", "exit"}:
            raise ValueError("研究决定证券或动作不合法")
        if (action == "select" and symbol not in candidates) or (action == "exit" and symbol not in holdings):
            raise ValueError("研究决定越过候选/持仓边界")
        if (
            isinstance(score, bool)
            or not isinstance(score, (float, int))
            or not math.isfinite(score)
            or not 0 <= score <= 1
        ):
            raise ValueError("研究相对评分必须在0到1内")
        if (
            row.get("horizon") != market["horizon"]
            or not isinstance(row.get("reason"), str)
            or not row["reason"].strip()
        ):
            raise ValueError("研究决定缺少理由或持有期不一致")
        validate_reference(row.get("evidence_ids"), reference_index(context), set(value["read_ids"]))
        seen.add(symbol)
    if not candidates <= seen:
        raise ValueError("研究决定遗漏候选")
    return value


def observations(value: dict, context: dict, actor: str) -> list[dict]:
    rows = value.get("observations")
    if not isinstance(rows, list):
        raise ValueError("数据角色缺少观察列表")
    result = []
    for index, row in enumerate(rows):
        symbol, key = row.get("symbol"), row.get("source_id")
        if (
            symbol not in context["market"]["candidates"]
            or type(row.get("direction")) is not int
            or row["direction"] not in {-1, 1}
        ):
            raise ValueError("数据观察证券或方向无效")
        if (
            row.get("horizon") != context["market"]["horizon"]
            or not isinstance(row.get("text"), str)
            or not row["text"].strip()
        ):
            raise ValueError("观察缺少正文或持有期不符")
        validate_reference([key], {**context, **context.get("documents", {})}, set(value["read_ids"]))
        if key != "market":
            source = context["documents"].get(key)
            if source and row.get("quote_id"):
                quote = source.get("quotes", {}).get(row["quote_id"])
                if not quote:
                    raise ValueError("引用了不存在的原文片段ID")
                row = {**row, "quote": quote, "quote_resolution": "source_fragment_id"}
            if (
                not source
                or symbol not in source["symbols"]
                or not row.get("quote")
                or row["quote"] not in source["text"]
            ):
                raise ValueError("数据观察没有证券关联的准确原文")
        result.append({**row, "actor": actor, "id": actor + ":" + str(index)})
    return result
