"""Global system settings backed by project YAML configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values

import src.core.config as config_module
from src.core.config import PROJECT_ROOT, Settings
from src.core.logger import get_logger

LOG = get_logger("system.settings")
CONFIG_PATH = PROJECT_ROOT / "egs" / "config.yaml"


@dataclass(frozen=True, slots=True)
class GlobalSettingField:
    key: str
    label: str
    group: str
    value_type: str
    env_name: str
    default: Any
    description: str
    restart_required: bool = True


GLOBAL_SETTING_FIELDS: tuple[GlobalSettingField, ...] = (
    GlobalSettingField("data_dir", "数据根目录", "数据与存储", "path", "ALL_IN_ONE_DATA_DIR", "data", "系统数据目录。"),
    GlobalSettingField(
        "db_path",
        "SQLite 主库路径",
        "数据与存储",
        "path",
        "ALL_IN_ONE_DB_PATH",
        "data/all_in_one.db",
        "系统元数据、配置、任务、索引和轻量业务记录。",
    ),
    GlobalSettingField(
        "document_storage_dir",
        "文档存储目录",
        "数据与存储",
        "path",
        "ALL_IN_ONE_DOCUMENT_STORAGE_DIR",
        "data/knowledge/documents",
        "PDF、Word、Markdown 等文档正文文件目录；数据库只保存路径和索引。",
    ),
    GlobalSettingField(
        "market_parquet_dir",
        "Parquet 行情湖目录",
        "数据与存储",
        "path",
        "ALL_IN_ONE_MARKET_PARQUET_DIR",
        "data/market_lake/parquet",
        "行情、因子和回测面板的列式文件目录。",
    ),
    GlobalSettingField(
        "duckdb_path",
        "DuckDB 查询库路径",
        "数据与存储",
        "path",
        "ALL_IN_ONE_DUCKDB_PATH",
        "data/market_lake/market.duckdb",
        "用于查询 Parquet 行情湖的本地 DuckDB 文件。",
    ),
    GlobalSettingField(
        "data_timeout_seconds",
        "请求超时秒数",
        "网络与缓存",
        "float",
        "ALL_IN_ONE_DATA_TIMEOUT_SECONDS",
        12.0,
        "外部行情和资讯请求超时时间。",
    ),
    GlobalSettingField(
        "data_http_retries",
        "HTTP 重试次数",
        "网络与缓存",
        "int",
        "ALL_IN_ONE_DATA_HTTP_RETRIES",
        1,
        "仅用于 429/5xx 退避重试；连接和读取异常快速失败。",
    ),
    GlobalSettingField(
        "data_cache_ttl_seconds",
        "行情缓存 TTL 秒数",
        "网络与缓存",
        "int",
        "ALL_IN_ONE_DATA_CACHE_TTL_SECONDS",
        300,
        "真实行情短时缓存上限，避免外部接口抖动拖慢页面。",
    ),
    GlobalSettingField(
        "trading_calendar_path",
        "交易日历路径",
        "调度与日历",
        "path",
        "ALL_IN_ONE_TRADING_CALENDAR_PATH",
        "egs/trading_calendar.yaml",
        "定时任务交易日过滤使用的全局日历文件。",
    ),
    GlobalSettingField(
        "scheduler_executors_path",
        "自定义执行体白名单",
        "调度与日历",
        "path",
        "ALL_IN_ONE_SCHEDULER_EXECUTORS_PATH",
        "egs/scheduler_executors.yaml",
        "定时任务 custom executor_key 可调用函数白名单。",
    ),
)


def global_settings_payload(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Return current grouped settings with source metadata."""

    runtime = (
        config_module.get_settings()
        if config_path.resolve() == CONFIG_PATH.resolve()
        else Settings.load(config_file=config_path)
    )
    yaml_payload = _read_yaml(config_path)
    dotenv = dotenv_values(PROJECT_ROOT / ".env")
    values = {field.key: _display_value(getattr(runtime, field.key)) for field in GLOBAL_SETTING_FIELDS}
    rows = []
    for field in GLOBAL_SETTING_FIELDS:
        env_defined = field.env_name in os.environ or field.env_name in dotenv
        yaml_defined = field.key in yaml_payload
        source = "环境变量" if env_defined else "YAML" if yaml_defined else "默认值"
        rows.append(
            {
                "分组": field.group,
                "配置项": field.label,
                "键": field.key,
                "当前值": values[field.key],
                "来源": source,
                "环境变量": field.env_name,
                "重启生效": "是" if field.restart_required else "否",
                "说明": field.description,
            }
        )
    return {
        "values": values,
        "rows": rows,
        "config_path": str(config_path),
        "env_overrides": [field.env_name for field in GLOBAL_SETTING_FIELDS if field.env_name in os.environ],
    }


def save_global_settings(payload: dict[str, Any], config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Persist editable global settings into ``egs/config.yaml``."""

    allowed = {field.key: field for field in GLOBAL_SETTING_FIELDS}
    unknown = sorted(set(payload) - set(allowed))
    if unknown:
        raise ValueError(f"未知系统设置：{', '.join(unknown)}")
    current = _read_yaml(config_path)
    for key, raw_value in payload.items():
        field = allowed[key]
        current[key] = _coerce_value(raw_value, field)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(current, allow_unicode=True, sort_keys=False), encoding="utf-8")
    config_module._SETTINGS = None
    LOG.info("global settings saved | path={} keys={}", config_path, sorted(payload))
    return global_settings_payload(config_path)


def global_setting_values() -> dict[str, Any]:
    return global_settings_payload()["values"]


def _read_yaml(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _display_value(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _coerce_value(value: Any, field: GlobalSettingField) -> Any:
    if field.value_type == "int":
        return max(0, int(value))
    if field.value_type == "float":
        return max(0.0, float(value))
    if field.value_type == "path":
        text = str(value or "").strip()
        if not text:
            return str(field.default)
        return text.replace("\\", "/")
    return str(value or "")


def runtime_storage_rows(settings: Settings | None = None) -> list[dict[str, str]]:
    cfg = settings or config_module.get_settings()
    return [
        {
            "存储对象": "SQLite 主库",
            "路径": cfg.db_path.as_posix(),
            "用途": "系统元数据、配置、任务、策略记录、知识库索引和轻量业务表。",
            "适配场景": "个人单机、低并发写入、事务型元数据。",
        },
        {
            "存储对象": "文档文件",
            "路径": cfg.document_storage_dir.as_posix(),
            "用途": "PDF、Word、Markdown、报告等原文文件。",
            "适配场景": "大文件由文件系统维护，SQLite 只保存路径、摘要、标签和分块索引。",
        },
        {
            "存储对象": "Parquet 行情湖",
            "路径": cfg.market_parquet_dir.as_posix(),
            "用途": "历史行情、因子截面、回测面板等列式数据。",
            "适配场景": "单机大批量分析、按日期/标的分区扫描。",
        },
        {
            "存储对象": "DuckDB 查询引擎",
            "路径": cfg.duckdb_path.as_posix(),
            "用途": "直接查询 Parquet 文件并做本地分析聚合。",
            "适配场景": "无需 Docker 和服务端数据库的本地 OLAP 查询。",
        },
    ]
