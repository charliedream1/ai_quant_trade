"""Opt-in real-source monitor and Qlib comparison with retained market evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from time import perf_counter

from loguru import logger


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path)
    args = parser.parse_args()
    args.runtime.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        ALL_IN_ONE_DATA_MODE="real",
        ALL_IN_ONE_DATA_DIR=str(args.runtime / "data"),
        ALL_IN_ONE_DB_PATH=str(args.runtime / "acceptance.db"),
    )
    from src.core.config import PROJECT_ROOT
    from src.data import DataSourceManager
    from src.engine.research.factor_monitor import FactorMonitorService

    class ArchiveSource:
        def __init__(self):
            self.source = DataSourceManager(mode="real")
            self.source_name, self.is_mock = self.source.source_name, self.source.is_mock
            self.saved = {}

        def stock_detail(self, symbol, **kwargs):
            if symbol not in self.saved:
                self.saved[symbol] = self.source.strategy_snapshot(symbol=symbol, **kwargs)
            return self.saved[symbol]

    source = ArchiveSource()
    service = FactorMonitorService(data=source)
    universe = service.default_universe_text()
    started = perf_counter()
    builtin = service.monitor(universe, persist=False)
    builtin_seconds = perf_counter() - started
    started = perf_counter()
    qlib = service.monitor(universe, backend="qlib", persist=False)
    qlib_seconds = perf_counter() - started

    def keyed(report):
        return {(row["factor_key"], row["date"]): row for row in report["ic_history"]}

    left, right = keyed(builtin), keyed(qlib)
    assert left and left.keys() == right.keys()
    max_error = max(abs(left[key][metric] - right[key][metric]) for key in left for metric in ("ic", "rank_ic"))
    assert max_error < 1e-9
    assert not source.is_mock and source.saved
    evidence = {
        "builtin_seconds": builtin_seconds,
        "qlib_seconds": qlib_seconds,
        "max_ic_error": max_error,
        "cross_sections": len(left),
        "universe": universe,
        "source": source.source_name,
        "coverage": builtin["coverage"],
        "root": str(PROJECT_ROOT),
    }
    for name, value in (
        ("market.json", source.saved),
        ("builtin.json", builtin),
        ("qlib.json", qlib),
        ("acceptance.json", evidence),
    ):
        (args.output / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
        )
    logger.info("Real monitor acceptance: {}", evidence)


if __name__ == "__main__":
    main()
