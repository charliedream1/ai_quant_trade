"""Small, explicit accounting fixtures never enter production data paths."""

import copy
from pathlib import Path

import pytest
import yaml

from src.core.timeutil import utc_now_iso
from src.data.economics import EconomicDataSource
from src.engine.economics.config import economics_config

FIXTURE = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("statements.yaml").read_text(encoding="utf-8"))


@pytest.fixture()
def observations():
    cfg = economics_config()
    now = utc_now_iso()
    output = {}
    for kind in cfg["statements"]:
        rows = []
        for item in FIXTURE["periods"]:
            row = {
                "SECURITY_CODE": FIXTURE["symbol"],
                "SECURITY_NAME_ABBR": FIXTURE["name"],
                "INDUSTRY_NAME": FIXTURE["industry"],
                "REPORT_DATE": item["period"],
                "NOTICE_DATE": item["period"],
                "CURRENCY": "CNY",
            }
            for name, definition in cfg["fields"].items():
                if definition["statement"] == kind:
                    row[definition["fields"][0]] = item.get(name)
            rows.append(row)
        output[kind] = {
            "rows": rows,
            "first_seen_at": now,
            "checked_at": now,
            "version": "fixture",
            "url": "https://example.com/financial",
            "source": "explicit-test-fixture",
            "historical_pit_eligible": False,
        }
    return output


@pytest.fixture()
def economic_sources(client, observations, monkeypatch):
    def fetch(self, name, *, symbol="", refresh=False):
        if symbol:
            result = copy.deepcopy(observations[name])
            for row in result["rows"]:
                row["SECURITY_CODE"] = symbol.split(".")[0]
                if symbol.startswith("000001"):
                    row["INDUSTRY_NAME"] = "银行"
            return result
        definition = economics_config()["macro"][name]
        now = utc_now_iso()
        return {
            "rows": [{definition["date"]: FIXTURE["macro"]["period"], definition["field"]: FIXTURE["macro"]["value"]}],
            "first_seen_at": now,
            "checked_at": now,
            "version": "fixture",
            "url": "https://example.com/macro",
            "source": "explicit-test-fixture",
        }

    monkeypatch.setattr(EconomicDataSource, "fetch", fetch)
    return fetch
