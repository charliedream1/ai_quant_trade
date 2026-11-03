"""Built-in scheduled job handlers."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from src.core.kb_chunks import ensure_document_chunks
from src.core.logger import get_logger
from src.core.repository import Repository
from src.core.timeutil import utc_now, utc_now_iso
from src.engine.backtest import BacktestRunner
from src.engine.market import MarketReportGenerator, NewsAggregator, QuoteService, Recommender
from src.engine.paper import PaperAccountService
from src.scheduler.calendar_updater import (
    refresh_official_trading_calendar,
    refresh_trading_calendar,
    trading_calendar_alerts,
    validate_announcement_profiles,
)

SUCCESS_STATUS = "成功"
SKIPPED_STATUS = "跳过"
DEFAULT_MAINTAIN_NEWS_DAYS = 180
DEFAULT_EXECUTION_KEEP_PER_JOB = 500
DEFAULT_REMOTE_CACHE_DAYS = 180
DEFAULT_QA_HISTORY_DAYS = 365
KB_SYNC_CHUNK_BACKFILL_LIMIT = 100_000
FTS_MAINTAIN_TARGETS = (
    (
        "news_items",
        "news_items_fts",
        "title, summary",
        "SELECT id, title, COALESCE(summary, '') FROM news_items",
    ),
    (
        "kb_documents",
        "kb_documents_fts",
        "title, summary, content",
        "SELECT id, title, COALESCE(summary, ''), COALESCE(content, '') FROM kb_documents",
    ),
    (
        "kb_document_chunks",
        "kb_document_chunks_fts",
        "title, heading, content",
        """SELECT c.id,
                  COALESCE(d.title, ''),
                  COALESCE(c.heading, ''),
                  COALESCE(c.content, '')
             FROM kb_document_chunks c
             JOIN kb_documents d ON c.doc_id = d.id""",
    ),
)


def execute_scheduled_job(job: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a scheduled job to a concrete built-in handler."""

    job_type = str(job.get("job_type") or "").strip()
    params = job.get("target") or {}
    if not isinstance(params, dict):
        params = {}
    if job_type == "news_fetch":
        return _run_news_fetch(params)
    if job_type == "market_refresh":
        return _run_market_refresh(params)
    if job_type == "recommend":
        return _run_recommend(params)
    if job_type == "report":
        return _run_report(params)
    if job_type == "backtest":
        return _run_backtest(params)
    if job_type == "paper_check":
        return _run_paper_check(params)
    if job_type == "data_maintain":
        return _run_data_maintain(params)
    if job_type == "calendar_refresh":
        return _run_calendar_refresh(params)
    if job_type == "calendar_reference_refresh":
        return _run_calendar_reference_refresh(params)
    if job_type == "calendar_announcement_profile_check":
        return _run_calendar_announcement_profile_check(params)
    if job_type == "system_health_check":
        return _run_system_health_check(params)
    if job_type == "kb_sync":
        return _run_kb_sync(params)
    custom_result = _run_custom_executor(job, params, job_type)
    if custom_result is not None:
        return custom_result
    return {
        "status": SKIPPED_STATUS,
        "summary": f"任务类型 {job_type or '-'} 暂无内置执行体，已记录为跳过。",
        "details": {"job_type": job_type},
    }


def _run_news_fetch(params: dict[str, Any]) -> dict[str, Any]:
    category = str(params.get("category") or "").strip()
    if category in {"", "全部"}:
        category = ""
    result = NewsAggregator().list_news(
        category=category or None,
        keyword=str(params.get("keyword") or "").strip() or None,
        source=str(params.get("source") or "").strip() or None,
        page=1,
        page_size=int(params.get("page_size") or 30),
        refresh=True,
    )
    total = int(result.get("total") or 0)
    return {"status": SUCCESS_STATUS, "summary": f"新闻采集完成，当前匹配 {total} 条。", "details": {"total": total}}


def _run_market_refresh(params: dict[str, Any]) -> dict[str, Any]:
    service = QuoteService()
    board = str(params.get("board") or "industry")
    limit = max(1, min(int(params.get("limit") or 20), 100))
    indices = service.indices(refresh=True)
    sectors = service.sectors(board=board, limit=limit)
    return {
        "status": SUCCESS_STATUS,
        "summary": f"行情刷新完成，指数 {len(indices)} 个，板块 {len(sectors)} 个。",
        "details": {"indices": len(indices), "sectors": len(sectors), "board": board},
    }


def _run_recommend(params: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "plan": params.get("plan") or "balanced",
        "path": params.get("path") or params.get("mode") or "quick",
        "count": params.get("count") or params.get("top_n") or 10,
    }
    result = Recommender().create_task(payload)
    return {
        "status": SUCCESS_STATUS,
        "summary": f"候选池刷新完成，推荐任务 {result['task_id']} 已生成。",
        "details": {"task_id": result["task_id"], "path": result.get("path"), "plan": payload["plan"]},
    }


def _run_report(params: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "report_type": params.get("report_type") or "daily",
        "topic": params.get("topic") or params.get("keyword") or "市场复盘",
        "use_llm": bool(params.get("use_llm", False)),
    }
    result = MarketReportGenerator().create(payload)
    return {
        "status": SUCCESS_STATUS,
        "summary": f"模型报告生成完成，报告 {result['report_id']} 已入库。",
        "details": {"report_id": result["report_id"], "report_type": result.get("report_type")},
    }


def _run_backtest(params: dict[str, Any]) -> dict[str, Any]:
    strategy_id = _optional_int(params.get("strategy_id"))
    if not strategy_id:
        return {"status": SKIPPED_STATUS, "summary": "定期回测缺少 strategy_id，已跳过。", "details": {}}
    payload = {
        "strategy_id": strategy_id,
        "engine": params.get("engine") or "simple",
        "symbols": params.get("symbols") or params.get("universe") or "600519",
        "start_date": params.get("start_date") or "2026-01-01",
        "end_date": params.get("end_date") or "2026-03-01",
        "initial_capital": params.get("initial_capital") or params.get("initial_cash") or 1000000,
        "benchmark": params.get("benchmark") or "沪深300",
        "params": params.get("strategy_params") or params.get("params") or {},
    }
    task = BacktestRunner().create(payload)
    return {
        "status": SUCCESS_STATUS,
        "summary": f"定期回测完成，任务 {task['task_id']} 已生成。",
        "details": {"task_id": task["task_id"], "strategy_id": strategy_id, "engine": task.get("engine")},
    }


def _run_paper_check(params: dict[str, Any]) -> dict[str, Any]:
    repo = Repository()
    service = PaperAccountService(repo=repo)
    account_id = _optional_int(params.get("account_id"))
    if account_id:
        account = repo.get_optional("paper_accounts", account_id)
        if account is None:
            return {
                "status": SKIPPED_STATUS,
                "summary": f"模拟账户 {account_id} 不存在，已跳过。",
                "details": {"account_id": account_id},
            }
        accounts = [account]
    else:
        status = str(params.get("status") or "运行中")
        accounts = repo.list(
            "paper_accounts",
            where="status = ?",
            params=(status,),
            order_by="id ASC",
            limit=int(params.get("limit") or 100),
        )
    if not accounts:
        return {"status": SKIPPED_STATUS, "summary": "没有需要巡检的模拟账户，已跳过。", "details": {}}
    snapshots = [service.snapshot(int(account["id"])) for account in accounts]
    return {
        "status": SUCCESS_STATUS,
        "summary": f"模拟盘巡检完成，刷新 {len(snapshots)} 个账户净值。",
        "details": {"account_count": len(snapshots), "account_ids": [item["account_id"] for item in snapshots]},
    }


def _run_data_maintain(params: dict[str, Any]) -> dict[str, Any]:
    repo = Repository()
    log = get_logger("scheduler.jobs")
    stale_news = _delete_older_than(
        repo,
        "news_items",
        "fetched_at",
        _retention_days_param(params, "news_retain_days", DEFAULT_MAINTAIN_NEWS_DAYS),
    )
    deleted_remote_cache = _delete_older_than(
        repo,
        "remote_docs_cache",
        "fetched_at",
        _retention_days_param(params, "remote_cache_retain_days", DEFAULT_REMOTE_CACHE_DAYS),
    )
    deleted_qa_history = _delete_older_than(
        repo,
        "kb_qa_history",
        "created_at",
        _retention_days_param(params, "qa_history_retain_days", DEFAULT_QA_HISTORY_DAYS),
    )
    deleted_executions = _prune_job_executions(
        repo,
        _keep_count_param(params, "execution_keep_per_job", DEFAULT_EXECUTION_KEEP_PER_JOB),
    )
    pruned_backtests = _prune_grouped_records(
        repo,
        "backtest_tasks",
        "strategy_id",
        "created_at",
        _keep_count_param(params, "backtest_keep_per_strategy", None),
    )
    pruned_qlib_runs = _prune_grouped_records(
        repo,
        "qlib_runs",
        "run_type",
        "created_at",
        _keep_count_param(params, "qlib_keep_per_type", None),
    )
    pruned_workflows = _prune_grouped_records(
        repo,
        "quant_workflow_runs",
        "mode",
        "created_at",
        _keep_count_param(params, "workflow_keep_per_mode", None),
    )
    fts_details = _maintain_fts(
        repo,
        rebuild_on_mismatch=_bool_param(params, "rebuild_fts_on_mismatch", True),
        optimize=_bool_param(params, "optimize_fts", True),
    )
    sqlite_details = _maintain_sqlite(repo, params)
    rebuilt_fts = sum(1 for item in fts_details.values() if item["rebuilt"])
    log.info(
        "data maintain finished | news={} executions={} remote_cache={} qa_history={} "
        "backtests={} qlib_runs={} workflows={} fts_rebuilt={}",
        stale_news,
        deleted_executions,
        deleted_remote_cache,
        deleted_qa_history,
        pruned_backtests,
        pruned_qlib_runs,
        pruned_workflows,
        rebuilt_fts,
    )
    return {
        "status": SUCCESS_STATUS,
        "summary": (
            f"数据维护完成，清理新闻 {stale_news} 条、执行历史 {deleted_executions} 条、"
            f"远程缓存 {deleted_remote_cache} 条、问答历史 {deleted_qa_history} 条，"
            f"FTS 重建 {rebuilt_fts} 个。"
        ),
        "details": {
            "deleted_news": stale_news,
            "deleted_executions": deleted_executions,
            "deleted_remote_cache": deleted_remote_cache,
            "deleted_qa_history": deleted_qa_history,
            "pruned_backtests": pruned_backtests,
            "pruned_qlib_runs": pruned_qlib_runs,
            "pruned_workflows": pruned_workflows,
            "fts": fts_details,
            "sqlite": sqlite_details,
        },
    }


def _run_calendar_refresh(params: dict[str, Any]) -> dict[str, Any]:
    result = refresh_trading_calendar(params)
    details = result.to_dict()
    return {
        "status": SUCCESS_STATUS,
        "summary": (
            f"交易日历更新完成，市场 {result.market}，交易日 {result.trading_day_count} 个、"
            f"节假日 {result.holiday_count} 个、补班交易日 {result.weekend_trading_day_count} 个。"
        ),
        "details": details,
    }


def _run_calendar_reference_refresh(params: dict[str, Any]) -> dict[str, Any]:
    result = refresh_official_trading_calendar(params)
    return {
        "status": SUCCESS_STATUS,
        "summary": (
            f"官方参考日历更新完成，市场 {result.market}，节假日 {result.holiday_count} 个、"
            f"补班交易日 {result.weekend_trading_day_count} 个。"
        ),
        "details": result.to_dict(),
    }


def _run_calendar_announcement_profile_check(params: dict[str, Any]) -> dict[str, Any]:
    result = validate_announcement_profiles(params)
    error_count = int(result.get("error_count") or 0)
    warning_count = int(result.get("warning_count") or 0)
    checked_count = int(result.get("checked_profile_count") or 0)
    if error_count:
        summary = f"交易所公告源核验完成，检查 {checked_count} 个 profile，发现 {error_count} 个错误。"
    elif warning_count:
        summary = f"交易所公告源核验完成，检查 {checked_count} 个 profile，发现 {warning_count} 个关注项。"
    else:
        summary = f"交易所公告源核验完成，检查 {checked_count} 个 profile，未发现异常。"
    return {"status": SUCCESS_STATUS, "summary": summary, "details": result}


def _run_system_health_check(params: dict[str, Any]) -> dict[str, Any]:
    alerts = trading_calendar_alerts(params)
    _publish_system_alerts(alerts)
    if not alerts:
        return {
            "status": SUCCESS_STATUS,
            "summary": "系统健康检查完成，暂无交易日历告警。",
            "details": {"alert_count": 0, "alerts": []},
        }
    severities = {str(item.get("severity") or "") for item in alerts}
    level = "严重" if "critical" in severities else "关注"
    return {
        "status": SUCCESS_STATUS,
        "summary": f"系统健康检查完成，发现 {len(alerts)} 条{level}告警，已推送到 notify。",
        "details": {"alert_count": len(alerts), "alerts": alerts},
    }


def _run_kb_sync(params: dict[str, Any]) -> dict[str, Any]:
    repo = Repository()
    documents = repo.list("kb_documents", order_by="id ASC")
    backfilled_chunks = ensure_document_chunks(repo.db, limit=KB_SYNC_CHUNK_BACKFILL_LIMIT)
    repo.db.execute("DELETE FROM kb_documents_fts")
    for doc in documents:
        repo.db.execute(
            "INSERT INTO kb_documents_fts(rowid, title, summary, content) VALUES (?, ?, ?, ?)",
            (doc["id"], doc.get("title") or "", doc.get("summary") or "", doc.get("content") or ""),
        )
    chunks = repo.db.query(
        """SELECT c.id, d.title, c.heading, c.content
             FROM kb_document_chunks c
             JOIN kb_documents d ON c.doc_id = d.id
             ORDER BY c.id ASC"""
    )
    repo.db.execute("DELETE FROM kb_document_chunks_fts")
    for chunk in chunks:
        repo.db.execute(
            "INSERT INTO kb_document_chunks_fts(rowid, title, heading, content) VALUES (?, ?, ?, ?)",
            (chunk["id"], chunk.get("title") or "", chunk.get("heading") or "", chunk.get("content") or ""),
        )
    synced_sources = 0
    if bool(params.get("sync_remote_sources", True)):
        now = utc_now_iso()
        sources = repo.list("remote_sources", where="enabled = ?", params=(1,), order_by="id ASC")
        for source in sources:
            repo.update(
                "remote_sources", int(source["id"]), {"status": "connected", "last_sync_at": now, "updated_at": now}
            )
        synced_sources = len(sources)
    return {
        "status": SUCCESS_STATUS,
        "summary": (
            f"知识库同步完成，重建索引 {len(documents)} 篇、分块 {len(chunks)} 段，刷新远程源 {synced_sources} 个。"
        ),
        "details": {
            "document_count": len(documents),
            "chunk_count": len(chunks),
            "backfilled_chunks": backfilled_chunks,
            "remote_sources": synced_sources,
        },
    }


def _run_custom_executor(job: dict[str, Any], params: dict[str, Any], job_type: str) -> dict[str, Any] | None:
    executor_key = str(params.get("executor_key") or params.get("executor") or "").strip()
    if not executor_key and job_type != "custom":
        executor_key = job_type
    if not executor_key:
        return {
            "status": SKIPPED_STATUS,
            "summary": "自定义任务缺少 executor_key，已跳过。",
            "details": {"job_type": job_type},
        }
    from src.scheduler.registry import CustomExecutorRegistry

    result = CustomExecutorRegistry().execute(executor_key, params, job)
    if result is None:
        return {
            "status": SKIPPED_STATUS,
            "summary": f"自定义执行体 {executor_key} 未注册，已跳过。",
            "details": {"job_type": job_type, "executor_key": executor_key},
        }
    return result


def _publish_system_alerts(alerts: list[dict[str, Any]]) -> None:
    if not alerts:
        return
    from src.api.ws_hub import ws_hub

    now = utc_now_iso()
    for alert in alerts:
        payload = {"task_type": "system_health", "created_at": now, **alert}
        ws_hub.broadcast_nowait("notify", "system_alert", payload)


def _delete_older_than(repo: Repository, table: str, column: str, retain_days: int | None) -> int:
    if retain_days is None:
        return 0
    cutoff = _cutoff_iso(retain_days)
    stale_count = int(repo.db.scalar(f"SELECT COUNT(*) FROM {table} WHERE {column} < ?", (cutoff,)) or 0)
    if stale_count:
        repo.db.execute(f"DELETE FROM {table} WHERE {column} < ?", (cutoff,))
    return stale_count


def _prune_job_executions(repo: Repository, keep_per_job: int | None) -> int:
    if keep_per_job is None:
        return 0
    job_ids = [int(row["job_id"]) for row in repo.db.query("SELECT DISTINCT job_id FROM job_executions")]
    deleted = 0
    for job_id in job_ids:
        rows = repo.db.query(
            "SELECT id FROM job_executions WHERE job_id = ? ORDER BY triggered_at DESC, id DESC",
            (job_id,),
        )
        stale_ids = [int(row["id"]) for row in rows[keep_per_job:]]
        for execution_id in stale_ids:
            repo.db.execute("DELETE FROM job_executions WHERE id = ?", (execution_id,))
        deleted += len(stale_ids)
    return deleted


def _prune_grouped_records(
    repo: Repository,
    table: str,
    group_column: str,
    order_column: str,
    keep_per_group: int | None,
) -> int:
    if keep_per_group is None:
        return 0
    rows = repo.db.query(f"SELECT DISTINCT {group_column} AS group_value FROM {table}")
    deleted = 0
    for row in rows:
        group_value = row["group_value"]
        where = f"{group_column} = ?"
        params: tuple[Any, ...] = (group_value,)
        if group_value is None:
            where = f"{group_column} IS NULL"
            params = ()
        grouped_rows = repo.db.query(
            f"SELECT id FROM {table} WHERE {where} ORDER BY {order_column} DESC, id DESC",
            params,
        )
        stale_ids = [int(item["id"]) for item in grouped_rows[keep_per_group:]]
        for row_id in stale_ids:
            repo.db.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
        deleted += len(stale_ids)
    return deleted


def _maintain_fts(repo: Repository, rebuild_on_mismatch: bool, optimize: bool) -> dict[str, dict[str, Any]]:
    details: dict[str, dict[str, Any]] = {}
    ensure_document_chunks(repo.db, limit=KB_SYNC_CHUNK_BACKFILL_LIMIT)
    for source_table, fts_table, columns, select_sql in FTS_MAINTAIN_TARGETS:
        source_count = int(repo.db.scalar(f"SELECT COUNT(*) FROM {source_table}") or 0)
        fts_count = int(repo.db.scalar(f"SELECT COUNT(*) FROM {fts_table}") or 0)
        rebuilt = False
        if rebuild_on_mismatch and source_count != fts_count:
            repo.db.execute(f"DELETE FROM {fts_table}")
            repo.db.execute(f"INSERT INTO {fts_table}(rowid, {columns}) {select_sql}")
            fts_count = int(repo.db.scalar(f"SELECT COUNT(*) FROM {fts_table}") or 0)
            rebuilt = True
        if optimize:
            repo.db.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES ('optimize')")
        details[fts_table] = {
            "source_count": source_count,
            "fts_count": fts_count,
            "rebuilt": rebuilt,
            "optimized": optimize,
        }
    return details


def _maintain_sqlite(repo: Repository, params: dict[str, Any]) -> dict[str, Any]:
    details: dict[str, Any] = {}
    if _bool_param(params, "wal_checkpoint", True):
        rows = repo.db.query("PRAGMA wal_checkpoint(PASSIVE)")
        details["wal_checkpoint"] = rows[0] if rows else {}
    if _bool_param(params, "database_optimize", True):
        repo.db.execute("PRAGMA optimize")
        details["pragma_optimize"] = True
    if _bool_param(params, "vacuum", False):
        repo.db.execute("VACUUM")
        details["vacuum"] = True
    return details


def _retention_days_param(params: dict[str, Any], key: str, default: int | None) -> int | None:
    value = params.get(key, default)
    if value in (None, ""):
        return None
    days = int(str(value))
    if days <= 0:
        return None
    return days


def _keep_count_param(params: dict[str, Any], key: str, default: int | None) -> int | None:
    value = params.get(key, default)
    if value in (None, ""):
        return None
    count = int(str(value))
    if count <= 0:
        return None
    return count


def _bool_param(params: dict[str, Any], key: str, default: bool) -> bool:
    value = params.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "启用", "是"}
    return bool(value)


def _cutoff_iso(retain_days: int) -> str:
    return (utc_now() - timedelta(days=retain_days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)
