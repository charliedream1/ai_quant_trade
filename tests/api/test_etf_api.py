"""ETF universe and snapshot API contract tests."""

from __future__ import annotations


def test_etf_universe_routes_return_asset_type_and_snapshot(client):
    universes = client.get("/api/v1/etf/universes").json()
    assert universes["code"] == 0
    assert {row["universe"] for row in universes["data"]} >= {"cn_core", "cn_sector"}
    detail = client.get("/api/v1/etf/universes/cn_core").json()
    assert detail["code"] == 0
    assert detail["data"]["asset_type"] == "etf"
    snapshot = client.get("/api/v1/etf/universes/cn_core/snapshot").json()
    assert snapshot["code"] == 0
    assert snapshot["data"]["asset_type"] == "etf"
    assert snapshot["data"]["available_count"] == 4
    assert all(row["status"] == "available" for row in snapshot["data"]["symbols"])
