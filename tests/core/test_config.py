import src.core.config as config_module
from src.core.config import Settings
from src.data.manager import DataSourceManager


def test_settings_loads_dotenv_without_overriding_process_environment(tmp_path, monkeypatch):
    for key in (
        "ALL_IN_ONE_DATA_DIR",
        "ALL_IN_ONE_DB_PATH",
        "ALL_IN_ONE_DOCUMENT_STORAGE_DIR",
        "ALL_IN_ONE_MARKET_PARQUET_DIR",
        "ALL_IN_ONE_DUCKDB_PATH",
        "ALL_IN_ONE_HELP_DOCS_AUTO_BUILD",
    ):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        "ALL_IN_ONE_HOST=127.0.0.2\n"
        "ALL_IN_ONE_PORT=8123\n"
        "ALL_IN_ONE_LOG_LEVEL=DEBUG\n"
        "ALL_IN_ONE_UI_THEME=dark\n"
        "ALL_IN_ONE_FRONTEND_ROOT_PATH=proxy/app\n"
        "ALL_IN_ONE_HELP_DOCS_MOUNT_PATH=help\n"
        "ALL_IN_ONE_HELP_DOCS_SITE_DIR=./runtime_help\n"
        "ALL_IN_ONE_HELP_DOCS_AUTO_BUILD=false\n"
        "ALL_IN_ONE_CHAN_ANALYZER_ROOT=./chan\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("ALL_IN_ONE_HOST", raising=False)
    monkeypatch.delenv("ALL_IN_ONE_PORT", raising=False)
    monkeypatch.delenv("ALL_IN_ONE_LOG_LEVEL", raising=False)
    monkeypatch.delenv("ALL_IN_ONE_UI_THEME", raising=False)
    monkeypatch.delenv("ALL_IN_ONE_DATA_HTTP_TRUST_ENV", raising=False)
    monkeypatch.delenv("ALL_IN_ONE_DATA_HTTP_RETRIES", raising=False)
    monkeypatch.delenv("ALL_IN_ONE_DATA_HTTP_BACKOFF_SECONDS", raising=False)
    monkeypatch.delenv("ALL_IN_ONE_DATA_CACHE_TTL_SECONDS", raising=False)

    settings = Settings.load(config_file=tmp_path / "missing.yaml")
    assert settings.host == "127.0.0.2"
    assert settings.port == 8123
    assert settings.log_level == "DEBUG"
    assert settings.ui_theme == "dark"
    assert settings.backend_slow_request_ms == 1000.0
    assert settings.frontend_root_path == "/proxy/app"
    assert settings.help_docs_mount_path == "/help"
    assert settings.help_docs_site_dir.as_posix().endswith("runtime_help")
    assert settings.help_docs_auto_build is False
    assert settings.chan_analyzer_root is not None
    assert settings.chan_analyzer_root.as_posix().endswith("chan")
    assert settings.document_storage_dir == tmp_path / "data" / "knowledge" / "documents"
    assert settings.market_parquet_dir == tmp_path / "data" / "market_lake" / "parquet"
    assert settings.duckdb_path == tmp_path / "data" / "market_lake" / "market.duckdb"
    assert settings.data_http_trust_env is False
    assert settings.data_http_retries == 1
    assert settings.data_http_backoff_seconds == 0.2
    assert settings.data_cache_ttl_seconds == 300

    monkeypatch.setenv("ALL_IN_ONE_PORT", "9000")
    assert Settings.load(config_file=tmp_path / "missing.yaml").port == 9000
    monkeypatch.setenv("ALL_IN_ONE_BACKEND_SLOW_REQUEST_MS", "250")
    assert Settings.load(config_file=tmp_path / "missing.yaml").backend_slow_request_ms == 250.0
    monkeypatch.setenv("ALL_IN_ONE_UI_THEME", "system")
    assert Settings.load(config_file=tmp_path / "missing.yaml").ui_theme == "system"
    monkeypatch.setenv("ALL_IN_ONE_UI_THEME", "invalid")
    assert Settings.load(config_file=tmp_path / "missing.yaml").ui_theme == "light"
    monkeypatch.setenv("ALL_IN_ONE_DATA_HTTP_TRUST_ENV", "true")
    monkeypatch.setenv("ALL_IN_ONE_DATA_HTTP_RETRIES", "0")
    monkeypatch.setenv("ALL_IN_ONE_DATA_HTTP_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("ALL_IN_ONE_DATA_CACHE_TTL_SECONDS", "120")
    network_settings = Settings.load(config_file=tmp_path / "missing.yaml")
    assert network_settings.data_http_trust_env is True
    assert network_settings.data_http_retries == 0
    assert network_settings.data_http_backoff_seconds == 0.0
    assert network_settings.data_cache_ttl_seconds == 120

    monkeypatch.delenv("ALL_IN_ONE_HELP_DOCS_MOUNT_PATH", raising=False)
    monkeypatch.delenv("ALL_IN_ONE_HELP_DOCS_SITE_DIR", raising=False)
    monkeypatch.delenv("ALL_IN_ONE_HELP_DOCS_AUTO_BUILD", raising=False)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    default_help_settings = Settings.load(config_file=tmp_path / "missing.yaml")
    assert default_help_settings.help_docs_mount_path == "/help-docs"
    assert default_help_settings.help_docs_site_dir == tmp_path / "data" / "help_site"
    assert default_help_settings.help_docs_auto_build is True


def test_real_data_is_default_and_mock_requires_explicit_mode(monkeypatch):
    monkeypatch.delenv("ALL_IN_ONE_DATA_MODE", raising=False)
    settings = Settings.load()

    assert settings.data_mode == "real"
    assert DataSourceManager(mode="real").is_mock is False
    assert DataSourceManager(mode="mock").is_mock is True
