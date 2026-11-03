import threading
import time


def test_scheduler_timeout_and_notify_event(client, monkeypatch):
    import src.scheduler.executor as executor_module

    def slow_job(_job):
        time.sleep(0.1)
        return {"status": "成功", "summary": "should be timed out"}

    monkeypatch.setattr(executor_module, "execute_scheduled_job", slow_job)
    job = client.post(
        "/api/v1/jobs",
        json={
            "name": "超时通知",
            "job_type": "news_fetch",
            "cron": "*/10 * * * *",
            "target": {"timeout_seconds": 0.01},
        },
    ).json()
    assert job["code"] == 0

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"action": "subscribe", "topic": "notify", "seq": 1})
        subscribed = ws.receive_json()
        assert subscribed["type"] == "subscribed"
        assert subscribed["topic"] == "notify"

        result = client.post(f"/api/v1/jobs/{job['data']['job_id']}/trigger").json()
        assert result["code"] == 0
        assert result["data"]["status"] == "超时"

        event = ws.receive_json()
        assert event["topic"] == "notify"
        assert event["type"] == "task_failed"
        assert event["payload"]["task_type"] == "scheduler"
        assert event["payload"]["job_id"] == job["data"]["job_id"]
        assert event["payload"]["status"] == "超时"


def test_system_health_check_pushes_calendar_alert(client, tmp_path):
    calendar_path = tmp_path / "missing-calendar.yaml"
    job = client.post(
        "/api/v1/jobs",
        json={
            "name": "系统健康告警",
            "job_type": "system_health_check",
            "cron": "15 8 * * 1-5",
            "target": {"calendar_path": str(calendar_path)},
        },
    ).json()
    assert job["code"] == 0

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"action": "subscribe", "topic": "notify", "seq": 1})
        subscribed = ws.receive_json()
        assert subscribed["type"] == "subscribed"
        assert subscribed["topic"] == "notify"

        result = client.post(f"/api/v1/jobs/{job['data']['job_id']}/trigger").json()
        assert result["code"] == 0
        assert result["data"]["status"] == "成功"
        assert "健康检查完成" in result["data"]["result_summary"]

        events = [ws.receive_json(), ws.receive_json()]
        alert_event = next(item for item in events if item["type"] == "system_alert")
        assert alert_event["topic"] == "notify"
        assert alert_event["payload"]["task_type"] == "system_health"
        assert alert_event["payload"]["code"] == "calendar_missing"
        assert alert_event["payload"]["severity"] == "critical"


def test_scheduler_mutex_group_skips_concurrent_job(client, monkeypatch):
    import src.scheduler.executor as executor_module
    from src.scheduler.executor import SchedulerService

    entered = threading.Event()
    release = threading.Event()

    def slow_job(_job):
        entered.set()
        release.wait(timeout=2)
        return {"status": "成功", "summary": "互斥组首个任务完成"}

    monkeypatch.setattr(executor_module, "execute_scheduled_job", slow_job)
    first = client.post(
        "/api/v1/jobs",
        json={
            "name": "互斥任务一",
            "job_type": "news_fetch",
            "cron": "*/10 * * * *",
            "target": {"mutex_group": "backtest-heavy"},
        },
    ).json()
    second = client.post(
        "/api/v1/jobs",
        json={
            "name": "互斥任务二",
            "job_type": "market_refresh",
            "cron": "*/10 * * * *",
            "target": {"mutex_group": "backtest-heavy"},
        },
    ).json()
    assert first["code"] == 0
    assert second["code"] == 0

    service = SchedulerService()
    result_holder: dict[str, object] = {}

    def trigger_first():
        try:
            result_holder["result"] = service.trigger(first["data"]["job_id"])
        except Exception as exc:  # pragma: no cover - surfaced after join
            result_holder["error"] = exc

    thread = threading.Thread(target=trigger_first, daemon=True)
    thread.start()
    assert entered.wait(timeout=2)

    skipped = SchedulerService().trigger(second["data"]["job_id"])
    assert skipped["status"] == "跳过"
    assert "互斥组 backtest-heavy" in skipped["result_summary"]

    release.set()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert "error" not in result_holder
    assert result_holder["result"]["status"] == "成功"
