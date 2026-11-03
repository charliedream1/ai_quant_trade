"""Fetch real public bars and audit the numerical/ledger path without inventing an LLM."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter

import yaml
from loguru import logger

import src.core.config as config_module
from src.alpha_mining.config import contained
from src.alpha_mining.evaluation import numerical_evidence, summarize
from src.alpha_mining.service import AlphaService
from src.core.config import PROJECT_ROOT
from src.core.database import Database
from src.data.eastmoney import EastmoneyDataSource


def main():
    cfg = yaml.safe_load(
        Path(__file__).with_name("fixtures").joinpath("real_validation.yaml").read_text(encoding="utf-8")
    )
    output = contained(PROJECT_ROOT / cfg["output"])
    output.mkdir(parents=True, exist_ok=True)
    os.environ["ALL_IN_ONE_DATA_DIR"] = str(output / "data")
    os.environ["ALL_IN_ONE_DB_PATH"] = str(output / "platform.db")
    os.environ["ALL_IN_ONE_DATA_MODE"] = "real"
    os.environ["ALL_IN_ONE_HELP_DOCS_AUTO_BUILD"] = "false"
    Database.reset_instance()
    config_module._SETTINGS = None
    assert config_module.get_settings().db_path.resolve() == (output / "platform.db").resolve()
    provider = EastmoneyDataSource(timeout_seconds=cfg["timeout_seconds"])

    def fetch(symbol):
        errors = []
        for loader in (provider._load_kline_tencent, provider._load_kline_eastmoney, provider._load_kline_baostock):
            try:
                values = loader(symbol, "daily", cfg["count"], "none", end_date=cfg["cutoff"])
                values = [row for row in values if row["date"] <= cfg["cutoff"]]
                assert len(values) >= cfg["count"] // 2
                return symbol, values
            except Exception as exc:
                errors.append(str(exc))
        raise RuntimeError(f"Real data unavailable for {symbol}: {errors}")

    started = perf_counter()
    with ThreadPoolExecutor(max_workers=len(cfg["symbols"])) as executor:
        history = dict(executor.map(fetch, cfg["symbols"]))
    payload = {
        "history": history,
        "is_mock": False,
        "market": cfg["market"],
        "source": "direct_public_provider",
        "price_adjustment": "none",
        "limitations": [
            "fixed_universe_survivorship_not_corrected",
            "corporate_actions_not_included",
            "historical_status_unavailable",
        ],
    }
    (output / "market.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    service = AlphaService()
    dataset = service.register_dataset(
        "真实公开价量母池",
        "market",
        payload,
        {
            "verified": True,
            "method": "actual_http_provider_response",
            "sources": sorted({row["data_source"] for rows in history.values() for row in rows}),
        },
    )
    study = service.create(
        {
            "name": "真实行情数值与成交验收",
            "dataset_id": dataset["id"],
            "batch_size": 1,
            "execution_costs": {"profile": "cn_a"},
        }
    )
    proposal = yaml.safe_load((PROJECT_ROOT / cfg["candidate"]).read_text(encoding="utf-8"))
    candidate = service.candidate(study["id"], proposal["hypothesis"], proposal["implementation"])
    assert candidate["status"] == "implemented", candidate
    service.seal(study["id"])
    evidence = numerical_evidence(service.store, study, candidate, "validation", lambda *args: None)
    summary = summarize(evidence)
    actual, reference = evidence["backtest"]["strategy"], evidence["backtest"]["baseline"]
    assert actual["curve"]["dates"] == reference["curve"]["dates"]
    assert actual["metrics"]["trade_count"] > 0
    assert actual["metrics"]["execution_costs"]["sha256"] == reference["metrics"]["execution_costs"]["sha256"]
    assert evidence["technical"]["passed"]
    summary.update(
        duration_seconds=round(perf_counter() - started, 3),
        llm_status="not_executed_no_real_model_configured",
        market_bars={symbol: len(rows) for symbol, rows in history.items()},
        study_id=study["id"],
        verification_scope="real_public_market_numeric_and_physical_ledger_only_not_alpha_approval",
    )
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Real alpha numerical/ledger evidence: {}", summary)


if __name__ == "__main__":
    main()
