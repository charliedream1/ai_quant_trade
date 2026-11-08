from io import BytesIO
from pathlib import Path

from docx import Document
from loguru import logger

from src.integration.mcp_client import MCPServiceManager


def test_backend_detail_log_includes_context_and_masks_query(client):
    messages: list[str] = []
    sink_id = logger.add(lambda message: messages.append(str(message)), format="{level.name}|{message}", level="DEBUG")
    try:
        response = client.get(
            "/api-meta",
            params={"api_key": "secret-value", "symbol": "600519"},
            headers={"User-Agent": "pytest-agent"},
        )
        frontend = client.get(
            "/app",
            follow_redirects=False,
            headers={
                "Accept": "text/html",
                "Referer": "http://127.0.0.1:8000/app/",
                "User-Agent": "pytest-agent",
            },
        )
        missing = client.get(
            "/not-found-for-log-test",
            headers={
                "Accept": "text/html",
                "Referer": "http://127.0.0.1:8000/app/",
                "User-Agent": "pytest-agent",
            },
        )
        manifest = client.get(
            "/manifest.json",
            headers={
                "Accept": "*/*",
                "Referer": "http://127.0.0.1:8000/app/",
                "User-Agent": "pytest-agent",
            },
        )
        logger.complete()
    finally:
        logger.remove(sink_id)

    assert response.status_code == 200
    assert frontend.status_code == 307
    assert frontend.headers["location"] == "/app/"
    assert missing.status_code == 404
    assert manifest.status_code == 404
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Process-Time-Ms"]
    joined = "\n".join(messages)
    assert "DEBUG|backend request begin" in joined
    assert "DEBUG|backend request completed" in joined
    assert "WARNING|backend request completed" in joined
    assert "INFO|backend request completed" not in joined
    assert "request_id=" in joined
    assert "path=/api-meta" in joined
    assert "endpoint=src.api.app.api_meta" in joined
    assert "api_key=<configured>" in joined
    assert "secret-value" not in joined
    assert "symbol=600519" in joined
    assert "pytest-agent" in joined
    assert "path=/app" in joined
    assert "status=307" in joined
    assert "path=/not-found-for-log-test" in joined
    assert "status=404" in joined
    assert "route_missing=True" in joined
    assert "path=/manifest.json" not in joined
    assert "referer=http://127.0.0.1:8000/app/" in joined
    assert "accept=text/html" in joined
    assert "uvicorn.access" not in joined


def test_health_and_market_routes(client):
    health = client.get("/api/v1/health").json()
    assert health["code"] == 0
    assert health["data"]["database"]["writable"] is True
    assert health["data"]["scheduler"]["running"] is True
    assert "trading_calendar" in health["data"]
    assert health["data"]["trading_calendar"]["status"] in {"ok", "missing", "missing_market", "error"}
    assert "system_alerts" in health["data"]
    assert isinstance(health["data"]["system_alerts"], list)

    indices = client.get("/api/v1/market/indices").json()
    assert indices["code"] == 0
    assert len(indices["data"]) >= 1

    engines = client.get("/api/v1/backtest-engines").json()
    assert engines["code"] == 0
    assert {item["key"] for item in engines["data"]} >= {"simple", "qlib"}

    factor_monitor = client.get(
        "/api/v1/factors/monitor", params={"universe": "600519,300750,000001,688981,300124"}
    ).json()
    assert factor_monitor["code"] == 0
    assert factor_monitor["data"]["metrics"]
    assert factor_monitor["data"]["ic_decay"]
    assert factor_monitor["data"]["quantile_history"]
    assert factor_monitor["data"]["style_exposure"]
    assert "capacity_hint" in factor_monitor["data"]["metrics"][0]
    assert "qlib" in factor_monitor["data"]

    qlib_status = client.get("/api/v1/qlib-workflows/status").json()
    assert qlib_status["code"] == 0
    assert qlib_status["data"]["config"]["workflow_path"]
    qlib_run = client.post(
        "/api/v1/qlib-workflows/runs",
        json={"run_type": "workflow", "params": {"experiment_name": "pytest_qlib"}},
    ).json()
    assert qlib_run["code"] == 0
    assert qlib_run["data"]["run_id"] > 0
    qlib_runs = client.get("/api/v1/qlib-workflows/runs").json()
    assert qlib_runs["code"] == 0
    assert qlib_runs["data"]["items"][0]["experiment_name"] == "pytest_qlib"

    group = client.post("/api/v1/watchlist/groups", json={"name": "观察池"}).json()
    assert group["code"] == 0
    group_id = group["data"]["id"]
    added = client.post(f"/api/v1/watchlist/groups/{group_id}/symbols", json={"symbols": ["300750"]}).json()
    assert added["code"] == 0
    quotes = client.get("/api/v1/watchlist/quotes").json()
    assert quotes["code"] == 0
    assert quotes["data"][0]["symbol"] == "300750"


def test_skill_schema_validation_and_builtin_run(client):
    skills = client.get("/api/v1/skills").json()
    assert skills["code"] == 0
    news_skill = next(item for item in skills["data"] if item["name"] == "news_summary")
    skill_id = news_skill["skill_id"]
    assert news_skill["param_schema"]["properties"]["limit"]["maximum"] == 20

    enabled = client.post(f"/api/v1/skills/{skill_id}/enable").json()
    assert enabled["code"] == 0
    invalid = client.put(f"/api/v1/skills/{skill_id}/params", json={"params": {"limit": 0}}).json()
    assert invalid["code"] == 1002

    saved = client.put(
        f"/api/v1/skills/{skill_id}/params",
        json={"params": {"limit": 3, "keyword": "市场"}},
    ).json()
    assert saved["code"] == 0
    result = client.post(f"/api/v1/skills/{skill_id}/run", json={"params": {"limit": 3}}).json()
    assert result["code"] == 0
    assert result["data"]["name"] == "news_summary"
    assert result["data"]["status"] == "success"
    assert len(result["data"]["items"]) <= 3


def test_mcp_tool_call_route_validates_arguments_and_returns_result(client):
    created = MCPServiceManager().create(
        {
            "name": "api-mcp",
            "service_type": "测试",
            "transport": "stdio",
            "command": "missing-mcp-command",
            "enabled": True,
        }
    )
    invalid = client.post(
        f"/api/v1/mcp-servers/{created['server_id']}/tools/call",
        json={"name": "quote_lookup", "arguments": []},
    ).json()
    assert invalid["code"] == 1002

    result = client.post(
        f"/api/v1/mcp-servers/{created['server_id']}/tools/call",
        json={"name": "quote_lookup", "arguments": {"symbol": "600519"}},
    ).json()
    assert result["code"] == 0
    assert result["data"]["tool_name"] == "quote_lookup"
    assert result["data"]["success"] is False
    assert result["data"]["transport_success"] is False


def test_strategy_and_backtest_flow(client):
    code = Path("egs/examples/strategy_examples/dual_ma_strategy.py").read_text(encoding="utf-8")
    strategy = client.post(
        "/api/v1/strategies",
        json={"name": "dual_ma_test", "description": "smoke", "code": code, "default_params": {"fast_window": 5}},
    ).json()
    assert strategy["code"] == 0
    strategy_id = strategy["data"]["strategy_id"]

    enabled = client.post(f"/api/v1/strategies/{strategy_id}/enable").json()
    assert enabled["data"]["status"] == "可用"

    backtest = client.post(
        "/api/v1/backtests",
        json={
            "strategy_id": strategy_id,
            "symbols": ["300750"],
            "start_date": "2026-01-01",
            "end_date": "2026-03-01",
            "initial_capital": 1000000,
            "order_type": "market",
            "price_adjustment": "qfq",
            "max_position_count": 2,
            "max_position_weight": 0.25,
            "lot_size": 100,
            "slippage_rate": 0.001,
        },
    ).json()
    assert backtest["code"] == 0
    task_id = backtest["data"]["task_id"]
    performance = client.get(f"/api/v1/backtests/{task_id}/performance").json()
    assert performance["code"] == 0
    assert "total_return" in performance["data"]
    assert performance["data"]["engine_mode"] == "event_kline"
    assert performance["data"]["data_source"] == "mock-local"
    assert performance["data"]["order_type"] == "market"
    assert performance["data"]["price_adjustment"] == "qfq"
    assert performance["data"]["max_position_count"] == 2
    assert performance["data"]["lot_size"] == 100
    assert performance["data"]["trade_count"] >= 1

    curve = client.get(f"/api/v1/backtests/{task_id}/equity-curve").json()
    assert curve["code"] == 0
    assert len(curve["data"]["dates"]) == len(curve["data"]["equity"])
    assert curve["data"]["equity"][-1] != 1000000

    trades = client.get(f"/api/v1/backtests/{task_id}/trades").json()
    assert trades["code"] == 0
    assert trades["data"]["total"] >= 1
    assert trades["data"]["items"][0]["order_type"] == "market"
    assert trades["data"]["items"][0]["signal"] != "simple-sim"

    attribution = client.get(f"/api/v1/backtests/{task_id}/attribution").json()
    assert attribution["code"] == 0
    assert attribution["data"]["summary"]
    assert attribution["data"]["by_symbol"]
    assert "max_drawdown" in attribution["data"]["drawdown"]

    modes = client.get("/api/v1/quant-workflows/modes").json()
    assert modes["code"] == 0
    assert {item["id"] for item in modes["data"]} >= {"simulation", "live"}

    sops = client.get("/api/v1/quant-workflows/sops", params={"mode": "simulation"}).json()
    assert sops["code"] == 0
    assert sops["data"][0]["id"] == "simulation_research_loop"

    snapshot = client.get(
        "/api/v1/quant-workflows/snapshot",
        params={"mode": "simulation", "strategy_id": strategy_id, "backtest_id": task_id},
    ).json()
    assert snapshot["code"] == 0
    assert snapshot["data"]["steps"]
    assert snapshot["data"]["insights"]
    assert snapshot["data"]["advice"]

    run = client.post(
        "/api/v1/quant-workflows/runs",
        json={
            "mode": "simulation",
            "sop_id": "simulation_research_loop",
            "strategy_id": strategy_id,
            "backtest_id": task_id,
        },
    ).json()
    assert run["code"] == 0
    run_id = run["data"]["run_id"]
    assert run["data"]["steps"]

    detail = client.get(f"/api/v1/quant-workflows/runs/{run_id}").json()
    assert detail["code"] == 0
    assert detail["data"]["run_id"] == run_id

    paper = client.post(
        "/api/v1/paper-accounts",
        json={"name": "live_gate_paper", "strategy_id": strategy_id, "initial_capital": 1000000},
    ).json()
    assert paper["code"] == 0
    paper_account_id = paper["data"]["account_id"]

    blocked_config = client.post(
        "/api/v1/live-configs",
        json={
            "name": "live_gate_missing",
            "strategy_id": strategy_id,
            "channel": "paper",
            "capital": 100000,
            "risk_controls": {"max_position_count": 3, "daily_loss_limit": 0.02},
        },
    ).json()
    assert blocked_config["code"] == 0
    blocked_config_id = blocked_config["data"]["config_id"]
    blocked_validation = client.get(f"/api/v1/live-configs/{blocked_config_id}/validation").json()
    assert blocked_validation["code"] == 0
    assert {row["状态"] for row in blocked_validation["data"]} >= {"拦截"}
    blocked_start = client.post("/api/v1/live-runs", json={"config_id": blocked_config_id}).json()
    assert blocked_start["code"] == 4003
    assert "回测验证" in blocked_start["message"]

    valid_config = client.post(
        "/api/v1/live-configs",
        json={
            "name": "live_gate_valid",
            "strategy_id": strategy_id,
            "channel": "paper",
            "capital": 100000,
            "params": {"_live_validation": {"backtest_id": task_id, "paper_account_id": paper_account_id}},
            "risk_controls": {"max_position_count": 3, "daily_loss_limit": 0.02},
        },
    ).json()
    assert valid_config["code"] == 0
    valid_config_id = valid_config["data"]["config_id"]
    valid_validation = client.get(f"/api/v1/live-configs/{valid_config_id}/validation").json()
    assert valid_validation["code"] == 0
    assert "拦截" not in {row["状态"] for row in valid_validation["data"]}
    adapters = client.get("/api/v1/live-broker-adapters").json()
    assert adapters["code"] == 0
    adapter_map = {item["channel"]: item for item in adapters["data"]}
    assert adapter_map["paper"]["available"] is True
    assert adapter_map["broker"]["available"] is False
    started = client.post("/api/v1/live-runs", json={"config_id": valid_config_id}).json()
    assert started["code"] == 0
    assert started["data"]["status"] == "running"
    assert started["data"]["status_label"] == "运行中"
    assert started["data"]["can_stop"] is True
    assert started["data"]["terminal"] is False
    assert started["data"]["uptime_seconds"] >= 0
    live_run_id = started["data"]["run_id"]
    duplicate_start = client.post("/api/v1/live-runs", json={"config_id": valid_config_id}).json()
    assert duplicate_start["code"] == 4001
    assert "已有运行" in duplicate_start["message"]
    queried = client.get(f"/api/v1/live-runs/{live_run_id}/status").json()
    assert queried["code"] == 0
    assert queried["data"]["status_label"] == "运行中"
    heartbeat_event = client.post(
        f"/api/v1/live-runs/{live_run_id}/broker-events",
        json={"event_type": "heartbeat", "message": "mock heartbeat"},
    ).json()
    assert heartbeat_event["code"] == 0
    assert heartbeat_event["data"]["status"] == "running"
    assert heartbeat_event["data"]["event_type"] == "heartbeat"
    event_frozen = client.post(
        f"/api/v1/live-runs/{live_run_id}/broker-events",
        json={"event_type": "error", "message": "broker disconnect"},
    ).json()
    assert event_frozen["code"] == 0
    assert event_frozen["data"]["status"] == "error"
    assert event_frozen["data"]["frozen"] is True
    assert "broker disconnect" in event_frozen["data"]["last_error"]
    event_recovered = client.post(f"/api/v1/live-runs/{live_run_id}/resume").json()
    assert event_recovered["code"] == 0
    assert event_recovered["data"]["status"] == "running"
    paused = client.post(f"/api/v1/live-runs/{live_run_id}/pause").json()
    assert paused["code"] == 0
    assert paused["data"]["status"] == "paused"
    assert paused["data"]["status_label"] == "已暂停"
    assert paused["data"]["can_resume"] is True
    assert paused["data"]["can_pause"] is False
    assert paused["data"]["can_stop"] is True
    duplicate_paused = client.post("/api/v1/live-runs", json={"config_id": valid_config_id}).json()
    assert duplicate_paused["code"] == 4001
    resumed = client.post(f"/api/v1/live-runs/{live_run_id}/resume").json()
    assert resumed["code"] == 0
    assert resumed["data"]["status"] == "running"
    frozen = client.post(f"/api/v1/live-runs/{live_run_id}/mark-error", json={"message": "人工演练异常"}).json()
    assert frozen["code"] == 0
    assert frozen["data"]["status"] == "error"
    assert frozen["data"]["frozen"] is True
    assert frozen["data"]["can_resume"] is True
    assert "人工演练异常" in frozen["data"]["last_error"]
    recovered = client.post(f"/api/v1/live-runs/{live_run_id}/resume").json()
    assert recovered["code"] == 0
    assert recovered["data"]["status"] == "running"
    assert recovered["data"]["last_error"] == ""
    frozen_again = client.post(f"/api/v1/live-runs/{live_run_id}/mark-error", json={"message": "停止前异常"}).json()
    assert frozen_again["code"] == 0
    assert frozen_again["data"]["status"] == "error"
    stopped = client.post(f"/api/v1/live-runs/{live_run_id}/stop").json()
    assert stopped["code"] == 0
    assert stopped["data"]["status"] == "stopped"
    assert stopped["data"]["status_label"] == "已停止"
    assert stopped["data"]["can_stop"] is False
    assert stopped["data"]["terminal"] is True
    stopped_again = client.post(f"/api/v1/live-runs/{live_run_id}/stop").json()
    assert stopped_again["code"] == 4001
    assert "终态" in stopped_again["message"]


def test_knowledge_qa_and_scheduler(client, tmp_path, keyword_model):
    category = client.post("/api/v1/kb/categories", json={"name": "论文"}).json()
    assert category["code"] == 0
    category_id = category["data"]["category_id"]
    doc = client.post(
        "/api/v1/kb/notes",
        json={
            "title": "因子研究笔记",
            "category_id": category_id,
            "content": "# 因子研究笔记\n\n" + "动量因子在趋势市场更稳定，分层收益需要连续观察。\n\n" * 70,
            "tags": ["factor"],
            "chunk_chars": 1200,
        },
    ).json()
    assert doc["code"] == 0
    assert doc["data"]["chunk_count"] > 1

    search = client.get("/api/v1/kb/search", params={"keyword": "动量"}).json()
    assert search["code"] == 0
    assert search["data"]["total"] >= 1
    assert search["data"]["items"][0]["chunk_id"]
    assert search["data"]["items"][0]["chunk_index"] >= 0

    uploaded = client.post(
        "/api/v1/kb/documents",
        data={"title": "上传研究文档", "category_id": str(category_id), "tags": "upload, factor"},
        files={"file": ("factor_upload.md", "# 上传研究\n\n上传动量因子资料。".encode(), "text/markdown")},
    ).json()
    assert uploaded["code"] == 0
    assert uploaded["data"]["title"] == "上传研究文档"
    assert uploaded["data"]["status"] == "ready"
    assert uploaded["data"]["file_path"].startswith("knowledge/documents/")
    assert uploaded["data"]["tags"] == ["upload", "factor"]
    assert uploaded["data"]["chunk_count"] >= 1

    upload_search = client.get("/api/v1/kb/search", params={"keyword": "上传动量", "scope": "local"}).json()
    assert upload_search["code"] == 0
    assert {item["title"] for item in upload_search["data"]["items"]} == {"上传研究文档"}
    assert {item["chunk_id"] for item in upload_search["data"]["items"]}
    detail = client.get(f"/api/v1/kb/documents/{uploaded['data']['doc_id']}").json()
    assert detail["code"] == 0
    assert "上传动量因子资料" in detail["data"]["content"]
    assert detail["data"]["chunk_count"] >= 1
    assert detail["data"]["chunks"][0]["content"]

    docx_buffer = BytesIO()
    docx_document = Document()
    docx_document.add_paragraph("Word 因子解析资料")
    docx_document.add_paragraph("多因子监控需要记录 IC 和分层收益。")
    docx_document.save(docx_buffer)
    uploaded_docx = client.post(
        "/api/v1/kb/documents",
        data={"title": "Word研究文档", "category_id": str(category_id), "tags": "word, factor"},
        files={
            "file": (
                "factor_upload.docx",
                docx_buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    ).json()
    assert uploaded_docx["code"] == 0
    assert uploaded_docx["data"]["title"] == "Word研究文档"
    assert uploaded_docx["data"]["encoding"] == "docx-text"
    assert uploaded_docx["data"]["tags"] == ["word", "factor"]
    assert uploaded_docx["data"]["chunk_count"] >= 1
    docx_search = client.get("/api/v1/kb/search", params={"keyword": "多因子监控", "scope": "local"}).json()
    assert docx_search["code"] == 0
    assert {item["title"] for item in docx_search["data"]["items"]} >= {"Word研究文档"}

    papers = client.get("/api/v1/papers/search", params={"keyword": "Factor"}).json()
    assert papers["code"] == 0
    assert papers["data"]["items"]
    paper_id = papers["data"]["items"][0]["id"]
    imported_paper = client.post(
        "/api/v1/papers/import",
        json={"paper_id": paper_id, "category_id": category_id, "tags": ["paper", "factor"]},
    ).json()
    assert imported_paper["code"] == 0
    assert imported_paper["data"]["doc_type"] == "论文"
    assert imported_paper["data"]["file_path"].startswith("knowledge/papers/")
    assert imported_paper["data"]["tags"] == ["paper", "factor"]
    assert imported_paper["data"]["chunk_count"] >= 1

    paper_search = client.get("/api/v1/kb/search", params={"keyword": "Regime", "scope": "local"}).json()
    assert paper_search["code"] == 0
    assert {item["doc_id"] for item in paper_search["data"]["items"]} >= {imported_paper["data"]["doc_id"]}

    qa = client.post("/api/v1/kb/qa", json={"question": "动量", "top_k": 3, "session_id": "kb-smoke"}).json()
    assert qa["code"] == 0
    assert "answer" in qa["data"]
    assert qa["data"]["session_id"] == "kb-smoke"
    assert qa["data"]["references"][0]["chunk_id"]
    follow_up = client.post(
        "/api/v1/kb/qa",
        json={"question": "它的风险是什么？", "top_k": 3, "context_turns": 2, "session_id": "kb-smoke"},
    ).json()
    assert follow_up["code"] == 0
    assert follow_up["data"]["context_used"] is True
    assert follow_up["data"]["context_turns"] >= 1
    assert follow_up["data"]["references"][0]["chunk_id"]
    sessions = client.get("/api/v1/kb/qa/sessions").json()
    assert sessions["code"] == 0
    assert {item["session_id"] for item in sessions["data"]["items"]} >= {"kb-smoke"}
    updated_session = client.put(
        "/api/v1/kb/qa/sessions",
        json={"session_id": "kb-smoke", "name": "动量追问", "summary": "用于验证知识问答上下文"},
    ).json()
    assert updated_session["code"] == 0
    assert updated_session["data"]["name"] == "动量追问"
    sessions_after_update = client.get("/api/v1/kb/qa/sessions").json()
    session_rows = [item for item in sessions_after_update["data"]["items"] if item["session_id"] == "kb-smoke"]
    assert session_rows[0]["summary"] == "用于验证知识问答上下文"
    isolated_follow_up = client.post(
        "/api/v1/kb/qa",
        json={"question": "它的风险是什么？", "top_k": 3, "context_turns": 2, "session_id": "isolated"},
    ).json()
    assert isolated_follow_up["code"] == 0
    assert isolated_follow_up["data"]["context_used"] is False
    cleared = client.post("/api/v1/kb/qa/clear", json={"session_id": "kb-smoke"}).json()
    assert cleared["code"] == 0
    assert cleared["data"]["deleted"] >= 2
    sessions_after_clear = client.get("/api/v1/kb/qa/sessions").json()
    assert {item["session_id"] for item in sessions_after_clear["data"]["items"]} >= {"kb-smoke"}
    after_clear = client.post(
        "/api/v1/kb/qa",
        json={"question": "它的风险是什么？", "top_k": 3, "context_turns": 2, "session_id": "kb-smoke"},
    ).json()
    assert after_clear["code"] == 0
    assert after_clear["data"]["context_used"] is False

    invalid_job = client.post("/api/v1/jobs", json={"name": "bad", "job_type": "news_fetch", "cron": "bad"}).json()
    assert invalid_job["code"] == 1002

    job = client.post(
        "/api/v1/jobs",
        json={"name": "新闻采集", "job_type": "news_fetch", "cron": "*/10 * * * *", "target": {"page_size": 5}},
    ).json()
    assert job["code"] == 0
    assert job["data"]["next_run_at"]
    triggered = client.post(f"/api/v1/jobs/{job['data']['job_id']}/trigger").json()
    assert triggered["code"] == 0
    assert triggered["data"]["status"] == "成功"
    assert "新闻采集完成" in triggered["data"]["result_summary"]
    histories = client.get(f"/api/v1/jobs/{job['data']['job_id']}/histories").json()
    assert histories["code"] == 0
    assert histories["data"]["items"][0]["history_id"] == triggered["data"]["history_id"]

    from src.core.repository import Repository
    from src.scheduler import scheduler_runtime
    from src.scheduler.policies import market_date

    Repository().update("scheduled_jobs", job["data"]["job_id"], {"next_run_at": "2000-01-01T00:00:00Z"})
    assert scheduler_runtime.run_due_once() >= 1
    cron_histories = client.get(f"/api/v1/jobs/{job['data']['job_id']}/histories").json()
    assert cron_histories["data"]["items"][0]["trigger_type"] == "cron"

    calendar_path = tmp_path / "trading_calendar.yaml"
    calendar_path.write_text(
        "\n".join(
            [
                "markets:",
                "  cn_stock:",
                "    holidays:",
                f"      - {market_date().isoformat()}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    calendar_job = client.post(
        "/api/v1/jobs",
        json={
            "name": "交易日过滤",
            "job_type": "news_fetch",
            "cron": "*/10 * * * *",
            "target": {
                "page_size": 5,
                "trading_day_only": True,
                "calendar_path": str(calendar_path),
            },
        },
    ).json()
    calendar_job_id = calendar_job["data"]["job_id"]
    Repository().update("scheduled_jobs", calendar_job_id, {"next_run_at": "2000-01-01T00:00:00Z"})
    assert scheduler_runtime.run_due_once() >= 1
    calendar_histories = client.get(f"/api/v1/jobs/{calendar_job_id}/histories").json()
    assert calendar_histories["data"]["items"][0]["status"] == "跳过"
    assert "非交易日" in calendar_histories["data"]["items"][0]["result_summary"]
    calendar_detail = client.get(f"/api/v1/jobs/{calendar_job_id}").json()
    assert calendar_detail["data"]["next_run_at"] != "2000-01-01T00:00:00Z"

    kb_sync = client.post(
        "/api/v1/jobs",
        json={
            "name": "知识库同步",
            "job_type": "kb_sync",
            "cron": "0 3 * * 0",
            "target": {"sync_remote_sources": False},
        },
    ).json()
    kb_sync_result = client.post(f"/api/v1/jobs/{kb_sync['data']['job_id']}/trigger").json()
    assert kb_sync_result["data"]["status"] == "成功"
    assert "知识库同步完成" in kb_sync_result["data"]["result_summary"]
    assert Repository().db.scalar("SELECT COUNT(*) FROM kb_document_chunks_fts") >= 1

    paper = client.post("/api/v1/paper-accounts", json={"name": "scheduler_paper", "initial_capital": 1000000}).json()
    paper_job = client.post(
        "/api/v1/jobs",
        json={
            "name": "模拟盘巡检",
            "job_type": "paper_check",
            "cron": "*/15 * * * *",
            "target": {"account_id": paper["data"]["account_id"]},
        },
    ).json()
    paper_result = client.post(f"/api/v1/jobs/{paper_job['data']['job_id']}/trigger").json()
    assert paper_result["data"]["status"] == "成功"
    assert "模拟盘巡检完成" in paper_result["data"]["result_summary"]
    missing_paper_job = client.post(
        "/api/v1/jobs",
        json={
            "name": "缺失模拟盘巡检",
            "job_type": "paper_check",
            "cron": "*/15 * * * *",
            "target": {"account_id": 999999},
        },
    ).json()
    missing_paper_result = client.post(f"/api/v1/jobs/{missing_paper_job['data']['job_id']}/trigger").json()
    assert missing_paper_result["data"]["status"] == "跳过"
    assert "不存在" in missing_paper_result["data"]["result_summary"]

    code = Path("egs/examples/strategy_examples/dual_ma_strategy.py").read_text(encoding="utf-8")
    strategy = client.post(
        "/api/v1/strategies",
        json={"name": "scheduler_dual_ma", "description": "scheduler", "code": code, "default_params": {}},
    ).json()
    strategy_id = strategy["data"]["strategy_id"]
    client.post(f"/api/v1/strategies/{strategy_id}/enable")
    backtest_job = client.post(
        "/api/v1/jobs",
        json={
            "name": "定期回测",
            "job_type": "backtest",
            "cron": "0 20 * * 1-5",
            "target": {
                "strategy_id": strategy_id,
                "symbols": ["600519"],
                "start_date": "2026-01-01",
                "end_date": "2026-03-01",
            },
        },
    ).json()
    backtest_result = client.post(f"/api/v1/jobs/{backtest_job['data']['job_id']}/trigger").json()
    assert backtest_result["data"]["status"] == "成功"
    assert "定期回测完成" in backtest_result["data"]["result_summary"]

    retry_job = client.post(
        "/api/v1/jobs",
        json={
            "name": "失败重试",
            "job_type": "backtest",
            "cron": "0 20 * * 1-5",
            "target": {"strategy_id": 999999, "retry_times": 1, "retry_interval_seconds": 0},
        },
    ).json()
    retry_result = client.post(f"/api/v1/jobs/{retry_job['data']['job_id']}/trigger").json()
    assert retry_result["data"]["status"] == "失败"
    assert "已重试 1 次" in retry_result["data"]["result_summary"]

    maintain_job = client.post(
        "/api/v1/jobs",
        json={
            "name": "数据维护",
            "job_type": "data_maintain",
            "cron": "0 4 * * *",
            "target": {"news_retain_days": 180, "execution_keep_per_job": 100},
        },
    ).json()
    maintain_result = client.post(f"/api/v1/jobs/{maintain_job['data']['job_id']}/trigger").json()
    assert maintain_result["data"]["status"] == "成功"
    assert "数据维护完成" in maintain_result["data"]["result_summary"]
    assert Repository().db.scalar("SELECT COUNT(*) FROM kb_document_chunks_fts") >= 1


def test_paper_account_rejects_invalid_sells_and_charges_fees(client):
    account = client.post("/api/v1/paper-accounts", json={"name": "risk_test", "initial_capital": 1000000}).json()
    account_id = account["data"]["account_id"]

    rejected = client.post(
        f"/api/v1/paper-accounts/{account_id}/orders",
        json={"symbol": "600519", "side": "sell", "order_type": "market", "quantity": 1},
    ).json()
    assert rejected["code"] == 3006
    assert rejected["message"] == "可卖持仓不足"

    bought = client.post(
        f"/api/v1/paper-accounts/{account_id}/orders",
        json={"symbol": "600519", "side": "buy", "order_type": "market", "quantity": 100},
    ).json()
    assert bought["code"] == 0
    buy_price = bought["data"]["avg_price"]
    buy_fee = round(buy_price * 100 * 0.0003, 2)

    overview = client.get(f"/api/v1/paper-accounts/{account_id}/overview").json()["data"]
    assert overview["cash"] == 1000000 - buy_price * 100 - buy_fee

    over_sell = client.post(
        f"/api/v1/paper-accounts/{account_id}/orders",
        json={"symbol": "600519", "side": "sell", "order_type": "market", "quantity": 101},
    ).json()
    assert over_sell["code"] == 3006
    assert over_sell["message"] == "可卖持仓不足"

    orders = client.get(f"/api/v1/paper-accounts/{account_id}/orders").json()["data"]
    assert orders["total"] == 1

    pending = client.post(
        f"/api/v1/paper-accounts/{account_id}/orders",
        json={"symbol": "600519", "side": "buy", "order_type": "limit", "price": 1, "quantity": 100},
    ).json()
    assert pending["code"] == 0
    assert pending["data"]["status"] == "待撮合"
    assert pending["data"]["filled_qty"] == 0

    match_result = client.post(f"/api/v1/paper-accounts/{account_id}/orders/match").json()
    assert match_result["code"] == 0
    assert match_result["data"]["matched_count"] == 0
    assert match_result["data"]["skipped"][0]["reason"] == "限价未触发"

    cancelled = client.delete(f"/api/v1/paper-accounts/{account_id}/orders/{pending['data']['order_id']}").json()
    assert cancelled["code"] == 0


def test_websocket_subscribe_and_ping(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"action": "subscribe", "topic": "market", "seq": 1})
        subscribed = ws.receive_json()
        assert subscribed["type"] == "subscribed"
        assert subscribed["topic"] == "market"
        assert subscribed["payload"]["seq"] == 1

        ws.send_json({"action": "ping", "topic": "market", "seq": 2})
        pong = ws.receive_json()
        assert pong["type"] == "pong"
        assert pong["topic"] == "market"
        assert pong["payload"]["seq"] == 2
