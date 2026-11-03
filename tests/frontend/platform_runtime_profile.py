"""Measure insight service calls and reproduce backtest date-boundary behavior."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from contextlib import ExitStack
from pathlib import Path
from time import perf_counter
from typing import Any
from unittest.mock import patch

import yaml
from loguru import logger

from src.core.config import get_settings
from src.engine.backtest.engines import _filter_events
from src.engine.market import NewsAggregator, QuoteService
from src.frontend.service.foundation import switch_ui_market
from src.frontend.services import FrontendService


def tracked_call(original: Callable, name: str, calls: list[dict[str, Any]], phase: list[str]) -> Callable:
    def measured(*args: Any, **kwargs: Any) -> Any:
        started = perf_counter()
        record: dict[str, Any] = {"method": name, "phase": phase[0]}
        try:
            return original(*args, **kwargs)
        except Exception as exc:
            record["error"] = str(exc)[:300]
            raise
        finally:
            record["duration_ms"] = round((perf_counter() - started) * 1000)
            calls.append(record)

    return measured


def profile() -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    phase = [""]
    results = []
    switch_ui_market("CN")
    service = FrontendService()
    with ExitStack() as stack:
        for owner, method in (
            (QuoteService, "indices"),
            (QuoteService, "sectors"),
            (QuoteService, "watchlist_quotes"),
            (NewsAggregator, "list_news"),
        ):
            original = getattr(owner, method)
            stack.enter_context(patch.object(owner, method, tracked_call(original, method, calls, phase)))
        for phase_name, force in (("cold", False), ("warm", False), ("refresh", True)):
            phase[0] = phase_name
            for name in ("dashboard_market_brief", "dashboard_market"):
                started = perf_counter()
                record: dict[str, Any] = {"method": name, "phase": phase_name}
                try:
                    result = getattr(service, name)("paper", force_refresh=force)
                    record["outputs"] = len(result)
                except Exception as exc:
                    record["error"] = str(exc)[:1000]
                record["duration_ms"] = round((perf_counter() - started) * 1000)
                results.append(record)
                logger.info("Insight measurement | {}", record)
    return {"mode": get_settings().data_mode, "services": results, "dependencies": calls}


def date_probe(fixture: Path) -> dict[str, Any]:
    config = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    events = _filter_events(config["symbols"][0], config["out_of_range_rows"], config["start_date"], config["end_date"])
    return {
        "requested_range": [config["start_date"], config["end_date"]],
        "actual_dates": [event.timestamp for event in events],
        "expected_event_count": 0,
        "date_filter_correct": not events,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, default=Path("tests/fixtures/platform_functional_audit.yaml"))
    args = parser.parse_args()
    result = profile()
    result["date_probe"] = date_probe(args.fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Runtime diagnosis saved | {}", args.output)


if __name__ == "__main__":
    main()
