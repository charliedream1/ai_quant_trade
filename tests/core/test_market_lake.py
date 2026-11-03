import importlib.util

import pandas as pd
import pytest

from src.core.config import Settings
from src.core.market_lake import MarketDataLake


def test_market_data_lake_writes_parquet_and_reports_status(tmp_path):
    pytest.importorskip("pyarrow")
    settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "all_in_one.db",
        market_parquet_dir=tmp_path / "market_lake" / "parquet",
        duckdb_path=tmp_path / "market_lake" / "market.duckdb",
    )
    lake = MarketDataLake(settings=settings)

    target = lake.write_records(
        "quotes",
        [{"symbol": "600519", "close": 1518.2}, {"symbol": "000001", "close": 11.42}],
        market="CN",
        partition="20261010",
    )

    assert target.exists()
    frame = pd.read_parquet(target)
    assert list(frame["symbol"]) == ["600519", "000001"]
    rows = lake.status_rows()
    assert rows[0]["组件"] == "Parquet 行情湖"
    assert "可写" in rows[0]["状态"]
    assert rows[1]["组件"] == "DuckDB 查询引擎"


def test_market_data_lake_duckdb_query_when_available(tmp_path):
    if importlib.util.find_spec("duckdb") is None:
        pytest.skip("duckdb is optional in the current runtime")
    pytest.importorskip("pyarrow")
    settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "all_in_one.db",
        market_parquet_dir=tmp_path / "market_lake" / "parquet",
        duckdb_path=tmp_path / "market_lake" / "market.duckdb",
    )
    lake = MarketDataLake(settings=settings)
    target = lake.write_records("quotes", [{"symbol": "600519", "close": 1518.2}], partition="20261010")

    result = lake.query("SELECT COUNT(*) AS n FROM read_parquet(?)", [target.as_posix()])

    assert int(result.iloc[0]["n"]) == 1
