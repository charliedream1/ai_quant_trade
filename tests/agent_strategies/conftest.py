"""Explicit text-ReAct doubles and dated market/evidence fixtures."""

import ast
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml

from src.alpha_mining.service import AlphaService
from src.strategy.composition.contracts import Frame

FIXTURE = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("workflows.yaml").read_text(encoding="utf-8"))


class FixtureLLM:
    def __init__(self, **kwargs):
        self.calls = []
        self.session = SimpleNamespace(close=lambda: None)

    def complete(self, prompt, *, purpose, history=None, **kwargs):
        role = purpose.split("-")[-1]
        self.calls.append(role)
        spec = FIXTURE["model"]
        if not history:
            index = ast.literal_eval(re.search(r"证据目录：(.*?)；", prompt).group(1))
            text = "".join(
                "<tool_use>" + json.dumps({"name": "read_evidence", "arguments": {"id": key}}) + "</tool_use>"
                for key in index
            )
        else:
            raw = prompt.split("工具观察：", 1)[1].rsplit("。继续查证", 1)[0]
            context = {row["id"]: row["content"] for row in json.loads(raw)}
            result = {"summary": spec["summary"], "evidence_ids": ["market"], "concerns": []}
            if role in {"events", "context", "fundamentals"}:
                result["observations"] = []
                for symbol in context["market"]["candidates"]:
                    source = next(
                        ((key, row) for key, row in context["documents"].items() if symbol in row["symbols"]), None
                    )
                    result["observations"].append(
                        {
                            "symbol": symbol,
                            "direction": spec["direction"],
                            "horizon": context["market"]["horizon"],
                            "text": spec["summary"] + symbol,
                            "source_id": source[0] if source else "market",
                            "quote": source[1]["text"] if source else "",
                        }
                    )
            elif role == "judge":
                result["ratings"] = [
                    {"proposal": key, "quality": spec["quality"], "reason": spec["summary"]}
                    for key in context["proposals"]
                ]
            elif role in {"chair", "continuation", "defensive", "sector"}:
                result["decisions"] = [
                    {
                        "symbol": symbol,
                        "action": "select" if symbol == spec["selections"][role] else "watch",
                        "score": spec["score"],
                        "horizon": context["market"]["horizon"],
                        "reason": spec["summary"],
                        "evidence_ids": ["market"],
                    }
                    for symbol in context["market"]["candidates"]
                ]
            text = "<final>" + json.dumps(result, ensure_ascii=False) + "</final>"
        return {"model": spec["name"], "text": text, "usage": {}}


@pytest.fixture
def workflow_data(client):
    return seed_workflow_data()


def seed_workflow_data():
    cfg = FIXTURE["market"]
    days = pd.bdate_range(cfg["start"], periods=cfg["periods"]).strftime("%Y-%m-%d").tolist()
    history = {}
    for symbol, spec in cfg["assets"].items():
        rows = []
        for index, day in enumerate(days):
            value = spec["base"] + spec["step"] * index + spec["wave"] * (index % cfg["wave_period"])
            rows.append(
                {
                    "date": day,
                    "open": value,
                    "close": value,
                    "high": value + spec["wave"],
                    "low": value - spec["wave"],
                    "volume": cfg["volume"],
                }
            )
        history[symbol] = rows
    documents = [
        {
            "id": symbol + ":" + category,
            "symbols": [symbol],
            "category": category,
            "text": FIXTURE["documents"]["text"].format(symbol=symbol),
            **{key: FIXTURE["documents"][key] for key in ("published_at", "available_at", "source")},
        }
        for symbol in history
        for category in FIXTURE["documents"]["categories"]
    ]
    service = AlphaService()
    if not service.store.repo.list("llm_models"):
        service.store.repo.insert("llm_models", FIXTURE["registration"])
    data = service.register_dataset(
        "explicit test market", "market", {"history": history, "market": "CN", "is_mock": True}
    )
    docs = service.register_dataset("explicit test documents", "documents", {"documents": documents, "is_mock": True})
    metadata = {
        symbol: {"sector": "explicit-fixture", "available_at": FIXTURE["documents"]["available_at"]}
        for symbol in history
    }
    return {"history": history, "metadata": metadata, "days": days, "market_id": data["id"], "documents_id": docs["id"]}


@pytest.fixture
def fixture_llm():
    return FixtureLLM()


@pytest.fixture
def frame(workflow_data):
    return Frame.create(workflow_data["days"][-1], workflow_data["history"], workflow_data["metadata"])
