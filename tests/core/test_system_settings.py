from pathlib import Path

import yaml

from src.core.file_storage import FileStorage
from src.core.kb_importer import _document_path
from src.core.system_settings import global_settings_payload, save_global_settings


def test_global_settings_save_yaml_and_report_sources(tmp_path, monkeypatch):
    config_path = tmp_path / "egs" / "config.yaml"
    monkeypatch.delenv("ALL_IN_ONE_DATA_DIR", raising=False)
    result = save_global_settings(
        {
            "data_dir": "data",
            "db_path": "data/all_in_one.db",
            "document_storage_dir": "data/docs",
            "market_parquet_dir": "data/market_lake/parquet",
            "duckdb_path": "data/market_lake/market.duckdb",
            "data_timeout_seconds": 10,
            "data_http_retries": 2,
            "data_cache_ttl_seconds": 120,
            "trading_calendar_path": "egs/trading_calendar.yaml",
            "scheduler_executors_path": "egs/scheduler_executors.yaml",
        },
        config_path=config_path,
    )

    saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert saved["market_parquet_dir"] == "data/market_lake/parquet"
    assert saved["data_cache_ttl_seconds"] == 120
    assert result["values"]["data_http_retries"] == 2
    sources = {row["键"]: row["来源"] for row in result["rows"]}
    assert sources["market_parquet_dir"] == "YAML"

    monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", "env_data")
    payload = global_settings_payload(config_path=config_path)
    assert payload["values"]["data_dir"] == "env_data"
    assert {row["键"]: row["来源"] for row in payload["rows"]}["data_dir"] == "环境变量"


def test_file_storage_uses_configured_document_directory(tmp_path):
    storage = FileStorage(base_dir=tmp_path / "data")
    storage.document_dir = tmp_path / "external_docs"
    storage.document_dir.mkdir(parents=True, exist_ok=True)

    path = _document_path(storage, "研究资料")
    assert Path(path).is_absolute()
    storage.write_text(path, "正文")

    assert (tmp_path / "external_docs").exists()
    assert storage.read_text(path) == "正文"
