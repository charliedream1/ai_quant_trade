"""Read bounded recorded results; never fetch quotes or call a model for a notification."""

from datetime import UTC, datetime, timedelta

from loguru import logger

from src.scheduler.calendar_updater import trading_calendar_alerts

from .config import config, target

TASK_QUERIES = {
    "backtest": "SELECT id,status,finished_at AS stamp FROM backtest_tasks WHERE finished_at>=? ORDER BY finished_at DESC LIMIT ?",
    "job": "SELECT id,status,created_at AS stamp FROM job_executions WHERE created_at>=? ORDER BY id DESC LIMIT ?",
    "alpha": "SELECT id,status,updated_at AS stamp FROM alpha_studies WHERE updated_at>=? ORDER BY updated_at DESC LIMIT ?",
    "agent": "SELECT id,status,updated_at AS stamp FROM agent_strategy_runs WHERE updated_at>=? ORDER BY updated_at DESC LIMIT ?",
}
TASK_TABLES = {
    "backtest": "backtest_tasks",
    "job": "job_executions",
    "alpha": "alpha_studies",
    "agent": "agent_strategy_runs",
}


def task(store, source, identifier, status, stamp=None):
    cfg = config()
    kind = (
        "success"
        if status in cfg["completed"]
        else "warning"
        if status in cfg["failed"] or status in cfg["partial"]
        else None
    )
    if not kind:
        return
    label = "task_done" if kind == "success" else "task_partial" if status in cfg["partial"] else "task_failed"
    destination = target(source if source in {"backtest", "job"} else "report", identifier)
    store.publish(
        source,
        identifier,
        kind,
        f"{cfg['sources'][source]} #{identifier} · {cfg['ui'][label]}",
        cfg["ui"]["task_message"],
        destination,
        stamp if source != "job" else None,
    )


def synchronize(store) -> list[str]:
    cfg = config()
    errors = []
    tables = {row["name"] for row in store.db.query("SELECT name FROM sqlite_master WHERE type='table'")}
    count = cfg["source_batch"]
    cutoff = (datetime.now(UTC) - timedelta(days=cfg["retention_days"])).isoformat()
    for source, query in TASK_QUERIES.items():
        if TASK_TABLES[source] not in tables:
            continue
        try:
            rows = store.db.query(query, (cutoff, count + 1))
            if len(rows) > count:
                errors.append("truncated")
            for row in rows[:count]:
                task(store, source, row["id"], row["status"], row["stamp"])
        except Exception as exc:
            logger.warning("提醒来源读取失败 | source={} error_type={}", source, type(exc).__name__)
            errors.append("source_error")
    try:
        rows = store.db.query("SELECT * FROM factor_alerts ORDER BY id DESC LIMIT ?", (count + 1,))
        for row in rows[:count]:
            if row["status"] == "open":
                store.publish(
                    "factor",
                    row["id"],
                    cfg["severity"].get(row["severity"], "warning"),
                    row["title"],
                    row["message"],
                    target("factor"),
                    row["triggered_at"],
                )
            else:
                store.resolve("factor", row["id"])
        if len(rows) > count:
            errors.append("truncated")
        # Reconcile older active alerts individually so a bounded recent window cannot falsely resolve them.
        for notice in store.db.query(
            "SELECT source_key FROM notifications WHERE source='factor' AND resolved_at IS NULL LIMIT ?", (count,)
        ):
            state = store.db.query_one("SELECT status FROM factor_alerts WHERE id=?", (notice["source_key"],))
            if state and state["status"] != "open":
                store.resolve("factor", notice["source_key"])
    except Exception as exc:
        logger.warning("因子提醒读取失败 | error_type={}", type(exc).__name__)
        errors.append("source_error")
    try:
        current = set()
        for row in trading_calendar_alerts():
            key = row["market"] + ":" + row["code"]
            current.add(key)
            store.publish(
                "system",
                key,
                cfg["severity"].get(row["severity"], "warning"),
                row["title"],
                row["message"],
                target("system"),
            )
        for row in store.db.query("SELECT source_key FROM notifications WHERE source='system' AND resolved_at IS NULL"):
            if row["source_key"] not in current:
                store.resolve("system", row["source_key"])
    except Exception as exc:
        logger.warning("系统提醒读取失败 | error_type={}", type(exc).__name__)
        errors.append("source_error")
    return sorted(set(errors))
