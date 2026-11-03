"""Local market data lake helpers built on Parquet and DuckDB."""

from __future__ import annotations

import importlib
import importlib.metadata
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.config import Settings, get_settings
from src.core.exceptions import BusinessError, ErrorCode
from src.core.logger import get_logger

LOG = get_logger("market.lake")


class MarketDataLake:
    """Write market tables to Parquet and query them with optional DuckDB."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.parquet_dir = self.settings.market_parquet_dir
        self.duckdb_path = self.settings.duckdb_path

    def status(self) -> dict[str, Any]:
        parquet_files = list(self.parquet_dir.rglob("*.parquet")) if self.parquet_dir.exists() else []
        return {
            "parquet_dir": self.parquet_dir.as_posix(),
            "duckdb_path": self.duckdb_path.as_posix(),
            "parquet_dir_exists": self.parquet_dir.exists(),
            "duckdb_file_exists": self.duckdb_path.exists(),
            "parquet_file_count": len(parquet_files),
            "pyarrow": _package_status("pyarrow"),
            "duckdb": _package_status("duckdb"),
        }

    def status_rows(self) -> list[dict[str, Any]]:
        status = self.status()
        pyarrow = status["pyarrow"]
        duckdb = status["duckdb"]
        return [
            {
                "组件": "Parquet 行情湖",
                "状态": "可写" if pyarrow["available"] else "缺少 pyarrow",
                "版本": pyarrow.get("version") or "-",
                "路径": status["parquet_dir"],
                "说明": f"已发现 {status['parquet_file_count']} 个 Parquet 文件。",
            },
            {
                "组件": "DuckDB 查询引擎",
                "状态": "可用" if duckdb["available"] else "缺少 duckdb",
                "版本": duckdb.get("version") or "-",
                "路径": status["duckdb_path"],
                "说明": "查询 Parquet 行情湖，无需常驻服务或 Docker。",
            },
        ]

    def write_records(
        self,
        dataset: str,
        rows: Sequence[dict[str, Any]],
        *,
        market: str = "CN",
        partition: str = "",
    ) -> Path:
        if not rows:
            raise BusinessError(ErrorCode.INVALID_PARAM, "写入 Parquet 的数据不能为空")
        if not _package_status("pyarrow")["available"]:
            raise BusinessError(ErrorCode.CONFIG_DEPENDENCY, "Parquet 写入依赖 pyarrow 未安装")
        safe_dataset = _safe_segment(dataset)
        safe_market = _safe_segment(market)
        safe_partition = _safe_segment(partition) if partition else time.strftime("%Y%m%d")
        target_dir = self.parquet_dir / safe_dataset / f"market={safe_market}" / f"dt={safe_partition}"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"part-{int(time.time() * 1000)}.parquet"
        frame = pd.DataFrame(list(rows))
        frame.to_parquet(target, index=False, engine="pyarrow")
        LOG.info(
            "market lake parquet written | dataset={} market={} rows={} path={}",
            safe_dataset,
            safe_market,
            len(frame),
            target,
        )
        return target

    def query(self, sql: str, parameters: Sequence[Any] = ()) -> pd.DataFrame:
        if not _package_status("duckdb")["available"]:
            raise BusinessError(ErrorCode.CONFIG_DEPENDENCY, "DuckDB 查询依赖 duckdb 未安装")
        duckdb = importlib.import_module("duckdb")
        self.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
        connection = duckdb.connect(str(self.duckdb_path))
        try:
            return connection.execute(sql, list(parameters)).fetchdf()
        finally:
            connection.close()


def _package_status(package: str) -> dict[str, Any]:
    try:
        version = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return {"available": False, "version": ""}
    return {"available": True, "version": version}


def _safe_segment(value: str) -> str:
    text = str(value or "").strip().replace("\\", "_").replace("/", "_")
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in text) or "default"
