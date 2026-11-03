"""Observable event/state behavior, source truth and API isolation."""

from pathlib import Path

import yaml

from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.notifications.config import config
from src.notifications.service import public_config, report_saved
from src.notifications.sources import synchronize
from src.notifications.store import NotificationStore

DATA = yaml.safe_load(Path(__file__).with_name("fixtures.yaml").read_text(encoding="utf-8"))


def publish(store, key="one", **updates):
    values = {
        "source": "factor",
        "source_key": key,
        "severity": "warning",
        "title": DATA["title"],
        "message": DATA["message"],
        "destination": DATA["target"],
        **updates,
    }
    return store.publish(**values)


def test_dedup_change_and_true_recurrence(client):
    store = NotificationStore()
    original = publish(store)
    assert publish(store)["id"] == original["id"]
    changed = publish(store, title=DATA["changed"])
    assert changed["id"] > original["id"] and store.repo.get("notifications", original["id"])["resolved_at"]
    store.resolve("factor", "one")
    recurrence = publish(store, title=DATA["changed"])
    assert recurrence["id"] > changed["id"] and not recurrence["resolved_at"]


def test_dismiss_read_and_resolution_are_separate_and_client_scoped(client):
    store = NotificationStore()
    row = publish(store, severity="critical")
    store.action(DATA["client"], row["id"], "dismiss")
    shown = store.feed(DATA["client"])
    assert shown["unread"] == 1 and len(shown["critical"]) == 1
    assert shown["items"][0]["dismissed_at"] and not shown["items"][0]["read_at"]
    assert not store.feed(DATA["other_client"])["items"][0]["dismissed_at"]
    store.read_all(DATA["client"])
    assert store.feed(DATA["client"])["unread"] == 0
    assert len(store.feed(DATA["client"])["critical"]) == 1
    store.resolve("factor", "one")
    assert store.feed(DATA["client"])["critical"] == []


def test_incremental_cursor_does_not_skip_over_a_page_and_bootstrap_does_not_replay(client):
    store = NotificationStore()
    count = 105
    for index in range(count):
        publish(store, key=str(index))
    first = store.feed(DATA["client"], initial=True)
    assert first["events"] == [] and first["cursor"] == count
    page = store.feed(DATA["client"])
    second = store.feed(DATA["client"], after=page["cursor"])
    assert len(page["events"]) == 100 and len(second["events"]) == 5
    store.read_all(DATA["client"])
    assert store.feed(DATA["client"])["unread"] == 0


def test_unresolved_critical_does_not_expire_with_ordinary_history(client):
    store = NotificationStore()
    important = publish(store, "old-critical", severity="critical")
    ordinary = publish(store, "old-warning", severity="warning")
    for row in (important, ordinary):
        store.repo.update("notifications", row["id"], {"created_at": "2000-01-01T00:00:00Z"})
    feed = store.feed(DATA["client"])
    assert [row["id"] for row in feed["items"]] == [important["id"]]
    store.read_all(DATA["client"])
    assert store.feed(DATA["client"])["unread"] == 0
    assert store.feed(DATA["client"])["critical"]
    store.resolve("factor", "old-critical")
    assert store.feed(DATA["client"])["items"] == []


def test_calendar_resolves_from_source_and_never_fetches_quotes(client, monkeypatch):
    store = NotificationStore()
    monkeypatch.setattr("src.notifications.sources.trading_calendar_alerts", lambda: DATA["calendar"])
    assert synchronize(store) == []
    assert len(store.feed(DATA["client"])["critical"]) == 1
    monkeypatch.setattr("src.notifications.sources.trading_calendar_alerts", lambda: [])
    synchronize(store)
    assert store.feed(DATA["client"])["critical"] == []


def test_task_hook_is_idempotent_and_failure_never_breaks_report_save(client, monkeypatch):
    report = {"run_id": "explicit-fixture", "status": "completed", "created_at": utc_now_iso()}
    report_saved(report)
    report_saved(report)
    assert Repository().db.scalar("SELECT COUNT(*) FROM notifications") == 1
    monkeypatch.setattr(
        NotificationStore, "publish", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fixture"))
    )
    report_saved({**report, "status": "failed"})


def test_recorded_backtest_job_and_factor_sources_preserve_original_state(client, monkeypatch):
    store = NotificationStore()
    stamp = utc_now_iso()
    monkeypatch.setattr("src.notifications.sources.trading_calendar_alerts", lambda: [])
    strategy = store.repo.insert("strategies", {**DATA["strategy"], "created_at": stamp, "updated_at": stamp})
    backtest = store.repo.insert(
        "backtest_tasks",
        {
            "strategy_id": strategy["id"],
            "symbols": "[]",
            "start_date": stamp[:10],
            "end_date": stamp[:10],
            "initial_cash": 10000,
            "commission_rate": 0,
            "created_at": stamp,
            "finished_at": stamp,
            "status": "failed",
        },
    )
    job = store.repo.insert(
        "scheduled_jobs",
        {
            "name": DATA["title"],
            "cron_expr": "0 0 * * *",
            "job_type": "fixture",
            "created_at": stamp,
            "updated_at": stamp,
        },
    )
    store.repo.insert(
        "job_executions", {"job_id": job["id"], "triggered_at": stamp, "created_at": stamp, "status": "成功"}
    )
    factor = store.repo.insert(
        "factor_definitions",
        {
            "factor_key": "fixture",
            "name": DATA["title"],
            "expression_key": "fixture",
            "created_at": stamp,
            "updated_at": stamp,
        },
    )
    alert = store.repo.insert(
        "factor_alerts",
        {
            "factor_key": factor["factor_key"],
            "severity": "critical",
            "title": DATA["title"],
            "message": DATA["message"],
            "status": "open",
            "triggered_at": stamp,
        },
    )
    synchronize(store)
    feed = store.feed(DATA["client"])
    assert {row["source"] for row in feed["items"]} == {"factor", "backtest", "job"}
    task_row = next(row for row in feed["items"] if row["source"] == "backtest")
    assert task_row["target"]["task_id"] == str(backtest["id"])
    store.action(DATA["client"], task_row["id"], "dismiss")
    assert store.repo.get("backtest_tasks", backtest["id"])["status"] == "failed"
    store.repo.update("factor_alerts", alert["id"], {"status": "resolved", "resolved_at": stamp})
    synchronize(store)
    assert store.feed(DATA["client"])["critical"] == []


def test_http_state_origin_validation_and_assets(client, monkeypatch):
    monkeypatch.setattr("src.notifications.sources.trading_calendar_alerts", lambda: [])
    store = NotificationStore()
    row = publish(store, message=DATA["hostile"])
    feed = client.get("/api/v1/notifications", params={"client_id": DATA["client"]}).json()
    assert feed["code"] == 0 and feed["data"]["items"][0]["message"] == DATA["hostile"]
    assert client.get("/api/v1/notifications", params={"client_id": "not-uuid"}).json()["code"] != 0
    endpoint = f"/api/v1/notifications/{row['id']}/state"
    payload = {"client_id": DATA["client"], "action": "dismiss"}
    assert client.post(endpoint, json=payload, headers={"Origin": "https://elsewhere.invalid"}).json()["code"] != 0
    assert client.post(endpoint, json=payload).json()["code"] == 0
    assert client.post("/api/v1/notifications/read-all", json={**payload, "action": "read"}).json()["code"] == 0
    assert client.get("/api/v1/notifications/config").json()["data"]["avatar"]["style"] == "robot"
    assert client.get("/static/assistant-robot.svg").status_code == 200


def test_custom_asset_rejects_outside_and_svg(client, monkeypatch):
    cfg = public_config()

    values = config()
    values["avatar"]["custom_image"] = "../../../../README.md"
    monkeypatch.setattr("src.notifications.service.config", lambda: values)
    assert "custom" not in public_config()["avatar"]["images"]
    assert cfg["avatar"]["images"]["robot"].endswith(".svg")
