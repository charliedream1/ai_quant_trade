"""Runtime settings.

Configuration order for this first backend slice:
defaults -> YAML file if present -> environment variables.
Database-backed settings are exposed through the settings route.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    db_path: Path = PROJECT_ROOT / "data" / "all_in_one.db"
    document_storage_dir: Path = PROJECT_ROOT / "data" / "knowledge" / "documents"
    market_parquet_dir: Path = PROJECT_ROOT / "data" / "market_lake" / "parquet"
    duckdb_path: Path = PROJECT_ROOT / "data" / "market_lake" / "market.duckdb"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    ui_theme: str = "light"
    backend_slow_request_ms: float = 1000.0
    frontend_root_path: str = ""
    help_docs_mount_path: str = "/help-docs"
    help_docs_site_dir: Path = PROJECT_ROOT / "data" / "help_site"
    help_docs_auto_build: bool = True
    chan_analyzer_root: Path | None = None
    scheduler_executors_path: Path | None = None
    trading_calendar_path: Path | None = None
    data_mode: str = "real"
    data_timeout_seconds: float = 12.0
    data_http_trust_env: bool = False
    data_http_retries: int = 1
    data_http_backoff_seconds: float = 0.2
    data_cache_ttl_seconds: int = 300
    api_prefix: str = "/api/v1"
    app_name: str = "AIQuant智投"
    version: str = "0.1.0"

    @classmethod
    def load(cls, config_file: Path | None = None) -> "Settings":
        payload: dict[str, Any] = {}
        dotenv = dotenv_values(PROJECT_ROOT / ".env")

        def env(name: str, fallback: Any) -> Any:
            return os.environ.get(name, dotenv.get(name, fallback))

        if config_file is None:
            config_file = PROJECT_ROOT / "egs/config/platform/config.yaml"
        if config_file.exists():
            loaded = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                payload.update(loaded)

        data_dir = Path(env("ALL_IN_ONE_DATA_DIR", payload.get("data_dir", PROJECT_ROOT / "data")))
        db_path = Path(env("ALL_IN_ONE_DB_PATH", payload.get("db_path", data_dir / "all_in_one.db")))
        document_storage_dir = Path(
            env(
                "ALL_IN_ONE_DOCUMENT_STORAGE_DIR",
                payload.get("document_storage_dir", data_dir / "knowledge" / "documents"),
            )
        )
        market_parquet_dir = Path(
            env(
                "ALL_IN_ONE_MARKET_PARQUET_DIR",
                payload.get("market_parquet_dir", data_dir / "market_lake" / "parquet"),
            )
        )
        duckdb_path = Path(
            env(
                "ALL_IN_ONE_DUCKDB_PATH",
                payload.get("duckdb_path", data_dir / "market_lake" / "market.duckdb"),
            )
        )
        help_docs_mount_path = _normalize_root_path(
            env("ALL_IN_ONE_HELP_DOCS_MOUNT_PATH", payload.get("help_docs_mount_path", "/help-docs"))
        )
        help_docs_site_dir = Path(
            env("ALL_IN_ONE_HELP_DOCS_SITE_DIR", payload.get("help_docs_site_dir", data_dir / "help_site"))
        )
        chan_root_value = env("ALL_IN_ONE_CHAN_ANALYZER_ROOT", payload.get("chan_analyzer_root", None))
        chan_analyzer_root = Path(str(chan_root_value)) if chan_root_value else None
        scheduler_executors_value = env(
            "ALL_IN_ONE_SCHEDULER_EXECUTORS_PATH",
            payload.get("scheduler_executors_path", None),
        )
        scheduler_executors_path = Path(str(scheduler_executors_value)) if scheduler_executors_value else None
        trading_calendar_value = env(
            "ALL_IN_ONE_TRADING_CALENDAR_PATH",
            payload.get("trading_calendar_path", None),
        )
        trading_calendar_path = Path(str(trading_calendar_value)) if trading_calendar_value else None
        return cls(
            data_dir=data_dir,
            db_path=db_path,
            document_storage_dir=document_storage_dir,
            market_parquet_dir=market_parquet_dir,
            duckdb_path=duckdb_path,
            host=str(env("ALL_IN_ONE_HOST", payload.get("host", "127.0.0.1"))),
            port=int(env("ALL_IN_ONE_PORT", payload.get("port", 8000))),
            log_level=str(env("ALL_IN_ONE_LOG_LEVEL", payload.get("log_level", "INFO"))),
            ui_theme=_normalize_ui_theme(env("ALL_IN_ONE_UI_THEME", payload.get("ui_theme", "light"))),
            backend_slow_request_ms=float(
                env(
                    "ALL_IN_ONE_BACKEND_SLOW_REQUEST_MS",
                    payload.get("backend_slow_request_ms", 1000.0),
                )
            ),
            frontend_root_path=_normalize_root_path(
                env("ALL_IN_ONE_FRONTEND_ROOT_PATH", payload.get("frontend_root_path", ""))
            ),
            help_docs_mount_path=help_docs_mount_path or "/help-docs",
            help_docs_site_dir=help_docs_site_dir,
            help_docs_auto_build=_as_bool(
                env("ALL_IN_ONE_HELP_DOCS_AUTO_BUILD", payload.get("help_docs_auto_build", True))
            ),
            chan_analyzer_root=chan_analyzer_root,
            scheduler_executors_path=scheduler_executors_path,
            trading_calendar_path=trading_calendar_path,
            data_mode=str(env("ALL_IN_ONE_DATA_MODE", payload.get("data_mode", "real"))),
            data_timeout_seconds=float(
                env(
                    "ALL_IN_ONE_DATA_TIMEOUT_SECONDS",
                    payload.get("data_timeout_seconds", 12.0),
                )
            ),
            data_http_trust_env=_as_bool(
                env(
                    "ALL_IN_ONE_DATA_HTTP_TRUST_ENV",
                    payload.get("data_http_trust_env", False),
                )
            ),
            data_http_retries=max(
                0,
                int(
                    env(
                        "ALL_IN_ONE_DATA_HTTP_RETRIES",
                        payload.get("data_http_retries", 1),
                    )
                ),
            ),
            data_http_backoff_seconds=max(
                0.0,
                float(
                    env(
                        "ALL_IN_ONE_DATA_HTTP_BACKOFF_SECONDS",
                        payload.get("data_http_backoff_seconds", 0.2),
                    )
                ),
            ),
            data_cache_ttl_seconds=max(
                1,
                int(
                    env(
                        "ALL_IN_ONE_DATA_CACHE_TTL_SECONDS",
                        payload.get("data_cache_ttl_seconds", 300),
                    )
                ),
            ),
        )


def _normalize_root_path(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text == "/":
        return ""
    if not text.startswith("/"):
        text = f"/{text}"
    return text.rstrip("/")


def _normalize_ui_theme(value: Any) -> str:
    """Normalize the configured UI theme while keeping invalid values safe."""
    theme = str(value or "light").strip().lower()
    return theme if theme in {"light", "dark", "system"} else "light"


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "y"}


_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings.load()
    return _SETTINGS
