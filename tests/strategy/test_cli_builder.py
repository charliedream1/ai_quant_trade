import json

from src.strategy.cli_builder import CLI_PROVIDERS, CliBuilder


def test_cli_builder_normalizes_supported_provider_aliases():
    assert CliBuilder.normalize_cli_type("codex cli") == "codex"
    assert CliBuilder.normalize_cli_type("workbuddy-cli") == "workbuddy"
    assert CliBuilder.normalize_cli_type("unknown") == "trae"
    assert set(CLI_PROVIDERS) == {"trae", "workbuddy", "codex"}


def test_cli_builder_creates_codex_session_logs_and_artifact(client):
    session = CliBuilder().create_session({"cli_type": "codex_cli", "requirement": "生成低换手趋势策略"})

    assert session["cli_type"] == "codex"
    assert session["cli_name"] == "codex cli"
    assert session["status"] == "completed"
    assert session["artifact_count"] == 1

    builder = CliBuilder()
    logs = builder.logs(session["session_id"])
    assert logs["ended"] is True
    assert any("provider: codex cli" in item["content"] for item in logs["logs"])

    artifacts = builder.artifacts(session["session_id"])
    assert artifacts == session["artifacts"]
    assert artifacts[0].endswith("generated_strategy.py")
    assert "on_bar" in builder.storage.read_text(artifacts[0])

    stored = builder.repo.get("cli_sessions", session["session_id"])
    assert json.loads(stored["artifacts"]) == artifacts
