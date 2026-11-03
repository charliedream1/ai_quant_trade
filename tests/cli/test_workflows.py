"""Run the source CLI in independent processes against an isolated HTTP service."""

import pytest


@pytest.fixture()
def command(cli_command):
    return cli_command


def test_strategy_backtest_paper_and_resource_loop(command, tmp_path):
    strategy = command(
        "strategy", "examples", "import", "--example", "egs/strategy_examples/dual_ma_strategy.py", "--name", "cli-loop"
    )["data"]
    strategy_id = strategy["strategy_id"]
    command("strategy", "enable", strategy_id)
    resolved = command("strategy", "params", "resolve", strategy_id, "--set", "params.fast_window=5")["data"]
    assert resolved
    result = command(
        "backtest",
        "run",
        "--strategy-id",
        strategy_id,
        "--symbols",
        "300750",
        "--start-date",
        "2026-01-01",
        "--end-date",
        "2026-03-01",
    )["data"]
    task_id = result["task_id"]
    metrics = command("backtest", "metrics", task_id)["data"]
    assert metrics["data_source"] == "mock-local" and metrics["trade_count"] > 0
    curve = command("backtest", "curve", task_id)["data"]
    assert len(curve["dates"]) == len(curve["equity"])
    trades = command("backtest", "trades", task_id, "--all", "--page-size", 1)
    assert len(trades["data"]["items"]) == trades["data"]["total"]
    assert command("backtest", "attribution", task_id)["data"]["by_symbol"]
    assert command("backtest", "snapshot", task_id)["data"]["data"]["market"] == "CN"
    assert len(command("backtest", "compare", "--ids", f"{task_id},{task_id}")["data"]) == 2
    exported = tmp_path / "trades.csv"
    command("backtest", "export", task_id, "--output", exported)
    assert "symbol" in exported.read_text(encoding="utf-8-sig")
    command("backtest", "metrics", task_id, "--require-real", expected=7)
    command("backtest", "run", "--strategy-id", strategy_id, "--require-real", expected=7)
    command("api", "call", "--method", "POST", "--path", "/backtests", "--require-real", expected=7)
    command("backtest", "delete", task_id, expected=2)
    command("api", "call", "--method", "DELETE", "--path", f"/backtests/{task_id}", expected=2)
    command("api", "call", "--method", "GET", "--path", f"/backtests/{task_id}")
    account = command("paper", "create", "--name", "cli-paper", "--initial-capital", 1000000)["data"]["account_id"]
    assert command("paper", "list")["data"]["items"][0]["account_id"] == account
    command(
        "paper", "order", account, "--symbol", "300750", "--side", "buy", "--order-type", "market", "--quantity", 100
    )
    assert command("paper", "positions", account)["data"]
    pool = command("pool", "create", "--name", "cli-pool")["data"]["id"]
    command("pool", "add", pool, "--symbols", "510300,510500")
    assert len(command("pool", "items", pool)["data"]) == 2


def test_business_commands_and_ai_stream(command, tmp_path):
    assert command("system", "capabilities")["data"]["is_mock"] is True
    assert command("market", "indices", "--market", "US")["data"]
    assert command("system", "capabilities")["data"]["market"] == "CN"
    command("security", "search", "--query", "510300")
    command("factor", "monitor", "--universe", "600519,300750,000001")
    command("news", "list", "--page-size", 2)
    command("model", "list")
    command("settings", "show")
    command("env", "list")
    command("qlib", "run", "--run-type", "workflow", expected=6)
    category = command("kb", "category", "create", "--name", "cli-kb")["data"]["id"]
    command(
        "kb", "document", "create", "--title", "ETF CLI", "--content", "ETF轮动遵循风险预算", "--category-id", category
    )
    assert command("kb", "search", "--keyword", "ETF")["data"]
    note = tmp_path / "memo.md"
    note.write_text("# CLI\nETF风险预算", encoding="utf-8")
    command("kb", "document", "upload", "--file", note, "--category-id", category)
    command("kb", "ask", "--question", "ETF风险预算是什么")
    session = command("ai", "session", "create", "--title", "cli-research")["data"]["id"]
    events = command("ai", "ask", "--session-id", session, "--message", "请读取附件", "--attachment", note, stream=True)
    assert events[0]["type"] == "status" and events[-1]["type"] == "result"
    assert events[-1]["data"]["data"]["status"] == "mock"
    assert events[-1]["data"]["meta"]["exit_code"] == 0
    rejected = command(
        "ai", "ask", "--session-id", session, "--message", "hello", "--require-real", expected=7, stream=True
    )
    assert rejected[-1]["data"]["meta"]["exit_code"] == 7
    command("ai", "ask", "--session-id", session, "--message", "hello", "--backend", "trae", expected=6)
    generic_events = command(
        "api",
        "call",
        "--method",
        "POST",
        "--path",
        f"/ai-workspace/sessions/{session}/messages",
        "--set",
        "message=generic route",
        stream=True,
    )
    assert generic_events[-1]["data"]["data"]["session_id"] == session
    history = command("ai", "session", "show", session)["data"]["messages"]
    assert [item["role"] for item in history] == ["user", "assistant"] * 4


def test_missing_mcp_tool_is_business_failure(command):
    server = command(
        "mcp",
        "create",
        "--name",
        "cli-mcp",
        "--service-type",
        "测试",
        "--transport",
        "stdio",
        "--command",
        "missing-cli-test-mcp-executable",
        "--enabled",
        "true",
    )["data"]["server_id"]
    failure = command("mcp", "call", server, "--name", "quote_lookup", "--arguments", "{}", expected=5)
    assert failure["data"]["success"] is False
