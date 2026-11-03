"""Exact point-in-time document references and bounded market observations."""

import re
from datetime import UTC, datetime

import numpy as np

from src.alpha_mining.pit import timestamp
from src.alpha_mining.store import AlphaStore


def cutoff(as_of: str) -> str:
    return timestamp(as_of if "T" in as_of else as_of + "T23:59:59+00:00").isoformat()


def assemble(frame, candidates: list[str], cfg: dict, dataset_id: int | None = None) -> dict:
    requested = timestamp(cutoff(frame.as_of))
    if requested.date() > datetime.now(UTC).date():
        raise ValueError("研究时点不能是未来")
    when = min(requested, datetime.now(UTC))
    limit = cfg["limits"]
    selected = sorted(candidates)
    if len(selected) > limit["max_candidates"]:
        raise ValueError("研究候选超过预算")
    market = {
        "as_of": frame.as_of,
        "candidates": selected,
        "holdings": sorted(frame.account.get("positions") or {}),
        "horizon": cfg["policy"]["horizon"],
        "history": {
            symbol: [dict(row) for row in frame.history.get(symbol, ())[-limit["history_bars"] :]]
            for symbol in sorted(set(selected) | set(frame.account.get("positions") or {}))
        },
        "account": frame.account,
    }
    documents = []
    provenance = {}
    if dataset_id:
        dataset = AlphaStore().get("alpha_datasets", dataset_id)
        if dataset["kind"] != "documents":
            raise ValueError("研究资料必须为带可得时点的documents数据集")
        provenance = {
            "digest": dataset["digest"],
            "is_mock": dataset["payload"]["is_mock"],
            "source": dataset["provenance"],
        }
        documents = [
            row
            for row in dataset["payload"]["documents"]
            if timestamp(row["available_at"]) <= when
            and timestamp(row["published_at"]) <= when
            and set(row["symbols"]) & set(selected)
        ]
    documents = sorted(documents, key=lambda row: (row["available_at"], row["id"]), reverse=True)[
        : limit["max_documents"]
    ]
    refs = {}
    for row in documents:
        key = "doc:" + row["id"]
        refs[key] = {**row, "text": row["text"][: limit["max_document_chars"]]}
        fragments = [part.strip() for part in re.findall(r"[^。！？]+[。！？]?", refs[key]["text"]) if part.strip()]
        refs[key]["quotes"] = {
            "q" + str(index): text for index, text in enumerate(fragments[: limit["quote_fragments"]])
        }
    missing_by_symbol = {}
    for symbol in selected:
        categories = {str(row.get("category", "news")) for row in documents if symbol in row["symbols"]}
        if frame.metadata.get(symbol, {}).get("sector"):
            categories.add("sector")
        missing_by_symbol[symbol] = sorted(set(cfg["definition"]["required"]) - categories)
    missing = sorted({kind for values in missing_by_symbol.values() for kind in values})
    return {
        "market": market,
        "documents": refs,
        "provenance": provenance,
        "missing": missing,
        "missing_by_symbol": missing_by_symbol,
        "decision_cutoff": when.isoformat(),
        "coverage_status": "partial" if missing else "complete",
        "metadata": {s: dict(frame.metadata.get(s, {})) for s in selected},
    }


def validate_reference(ids: object, available: dict, reads: set[str]) -> None:
    if (
        not isinstance(ids, list)
        or not ids
        or any(not isinstance(key, str) or key not in available or key not in reads for key in ids)
    ):
        raise ValueError("引用不存在或未实际读取的研究证据")


def reference_index(context: dict) -> dict:
    return {
        **context,
        **context.get("documents", {}),
        **context.get("peers", {}),
        **{
            row["id"]: row
            for row in context.get("factors", [])
            if isinstance(row, dict) and isinstance(row.get("id"), str)
        },
    }


def market_view(market: dict, cfg: dict) -> dict:
    summaries = {}
    for symbol, rows in market["history"].items():
        if not rows:
            continue
        values = np.asarray([row["close"] for row in rows], dtype=float)
        summaries[symbol] = {
            "last_date": rows[-1]["date"],
            "close": float(values[-1]),
            "historical_returns": {
                str(window): float(values[-1] / values[-window - 1] - 1)
                for window in cfg["limits"]["summary_windows"]
                if len(values) > window
            },
            "scope": "deterministic_trailing_history_not_future_labels",
        }
    return {
        **market,
        "history": {s: rows[-cfg["limits"]["model_bars"] :] for s, rows in market["history"].items()},
        "history_summary": summaries,
        "full_history_archived": True,
    }
