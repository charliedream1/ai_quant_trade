"""Catalogue privacy, billing provenance and backend freshness contracts."""

import json
from threading import Event, Thread

import pytest

from src.agent import cli_catalog
from src.frontend.common import composer_catalog


def test_catalogue_allowlist_and_rates():
    rows = cli_catalog.normalize_catalog(
        {
            "models": [
                {"id": "free", "free": True, "api_key": "private-do-not-publish"},
                {"id": "credits", "price_factor": 1.2},
                {"id": "unknown"},
                {"id": "subscription", "billing_type": "subscription"},
                {
                    "id": "tokens",
                    "billing_type": "tokens",
                    "pricing": {"input": 1, "output": 3, "currency": "USD", "unit": "per_million_tokens"},
                },
                {"id": "hidden", "hidden": True},
                {"id": "free", "free": False},
            ]
        },
        "qoder",
        "declared source",
    )
    assert len(rows) == 5
    assert "Free" in rows[0]["billing"]
    assert rows[1]["billing"] == "1.2× credits"
    assert rows[2]["billing"] == "Price unknown"
    assert "Subscription" in rows[3]["billing"]
    assert "1/3 USD" in rows[4]["billing"]
    assert "private-do-not-publish" not in json.dumps(rows)


def test_workbuddy_catalog_preserves_model_identity_and_credit_rate():
    rows = cli_catalog.normalize_catalog(
        {
            "models": [
                {"id": "hy4flash-free", "model": "hy4flash", "name": "Hy4 flash", "credits": "x0.00"},
                {"id": "hy4flash", "name": "Hy4 flash", "credits": "x0.03"},
            ]
        },
        "workbuddy",
        "declared source",
    )
    assert [(row["id"], row["billing"]) for row in rows] == [
        ("hy4flash-free", cli_catalog.catalog_config()["labels"]["free"]),
        ("hy4flash", "0.03× credits"),
    ]


def test_catalogue_cache_refresh_and_backend_isolation(monkeypatch, tmp_path):
    catalog = tmp_path / "models.json"
    catalog.write_text(json.dumps({"models": [{"id": "first"}]}), encoding="utf-8")
    monkeypatch.setenv("ALL_IN_ONE_CODEBUDDY_MODEL_CATALOG", str(catalog))
    first = cli_catalog.discover("codebuddy", True)
    catalog.write_text(json.dumps({"models": [{"id": "second", "price_factor": 2}]}), encoding="utf-8")
    assert cli_catalog.discover("codebuddy")["rows"] == first["rows"]
    assert cli_catalog.discover("codebuddy", True)["rows"][0]["id"] == "second"
    monkeypatch.setattr(cli_catalog, "executable", lambda backend: None)
    assert cli_catalog.discover("trae", True)["status"] == "missing"


def test_delayed_result_cannot_override_new_provider(monkeypatch):
    started, release = Event(), Event()

    def discover(backend, refresh):
        started.set()
        assert release.wait(3)
        return {"backend": backend, "rows": [], "status": "empty"}

    monkeypatch.setattr(composer_catalog, "discover", discover)
    selection = composer_catalog.CatalogSelection([])
    state, result = {}, []
    selection.begin("qoder", state)
    thread = Thread(target=lambda: result.append(selection.load(state)))
    thread.start()
    assert started.wait(1)
    selection.begin("codex", state)
    release.set()
    thread.join(3)
    assert result == [tuple({"__type__": "update"} for _ in range(5))]
    assert state["backend"] == "codex" and state["catalog"] == {}


@pytest.mark.parametrize("bad", [-1, float("nan"), True, "free"])
def test_invalid_rate_is_unknown(bad):
    assert cli_catalog.billing({"price_factor": bad}) == "Price unknown"


def test_model_efforts_are_intersected_and_unconfigured_workbuddy_is_unavailable(monkeypatch):
    catalog = {
        "backend": "workbuddy",
        "status": "ready",
        "rows": [{"id": "declared", "name": "Declared", "billing": "Price unknown", "efforts": ["low"]}],
    }
    monkeypatch.setattr(composer_catalog, "discover", lambda *args: catalog)
    for name in ("INSTALLATION", "AUTHENTICATION", "PRODUCT"):
        monkeypatch.setenv("ALL_IN_ONE_WORKBUDDY_" + name, "")
    state = {}
    selection = composer_catalog.CatalogSelection([])
    selection.begin("workbuddy", state)
    assert selection.load(state)[-1]["interactive"] is False
    assert "desktop login file" in composer_catalog.details(state["catalog"], "declared")
    assert composer_catalog.effort_update("codex", catalog, "declared")["choices"] == [("跟随后端", ""), ("低", "low")]
