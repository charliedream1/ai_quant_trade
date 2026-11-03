"""Explicit deterministic LLM doubles; no external calls in contract tests."""

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.alpha_mining.config import prompts

FIXTURE = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("workflows.yaml").read_text(encoding="utf-8"))
NUMBERS = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("core.yaml").read_text(encoding="utf-8"))


class FixtureLLM:
    def __init__(self, **kwargs):
        self.calls = []

    def complete(self, prompt, *, purpose, history=None, **kwargs):
        role = purpose.split("-")[-1]
        self.calls.append({"role": role, "prompt": prompt})
        if not history:
            text = "".join(
                "<tool_use>" + json.dumps({"name": "read_evidence", "arguments": {"id": key}}) + "</tool_use>"
                for key in prompts()["roles"][role]["required"]
            )
        else:
            text = "<final>" + json.dumps(FIXTURE[role], ensure_ascii=False) + "</final>"
        return {"model": "explicit-unit-test-double", "text": text, "usage": {}}


@pytest.fixture()
def fixture_llm(monkeypatch):
    llm = FixtureLLM()
    monkeypatch.setattr("src.alpha_mining.agents.LLMClient", lambda **kwargs: llm)
    return llm


@pytest.fixture()
def market_payload():
    days = pd.bdate_range(FIXTURE["market"]["start"], periods=FIXTURE["market"]["periods"]).strftime("%Y-%m-%d")
    history = {}
    for symbol, values in NUMBERS["prices"].items():
        history[symbol] = [
            {
                "date": day,
                "open": values[index % len(values)],
                "close": values[index % len(values)],
                "high": values[index % len(values)] + 1,
                "low": values[index % len(values)] - 1,
                "volume": 1000000,
            }
            for index, day in enumerate(days)
        ]
    return {**FIXTURE["market"], "history": history, "market": "CN", "price_adjustment": "none"}


@pytest.fixture()
def workflow_fixture():
    return FIXTURE
