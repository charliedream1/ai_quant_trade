"""One real run per recipe; data preparation can run without any paid model request."""

import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests
import yaml
from loguru import logger
from real_agent import VisibleText, prepare_model

import src.core.config as config_module
from src.agent_strategies.service import AgentStrategyService
from src.alpha_mining.config import contained, digest
from src.alpha_mining.service import AlphaService
from src.core.config import PROJECT_ROOT
from src.core.database import Database
from src.core.timeutil import utc_now_iso
from src.data.eastmoney import EastmoneyDataSource
from src.strategy.composition.contracts import Frame


def main(prepare_only: bool, recipe=None):
    cfg = yaml.safe_load(
        Path(__file__).with_name("fixtures").joinpath("real_validation.yaml").read_text(encoding="utf-8")
    )
    if recipe:
        if recipe not in cfg["recipes"]:
            raise ValueError("Real acceptance recipe is outside the configured two-workflow scope")
        cfg["recipes"] = [recipe]
    output = contained(PROJECT_ROOT / cfg["output"])
    output.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        ALL_IN_ONE_DATA_DIR=str(output / "data"),
        ALL_IN_ONE_DB_PATH=str(output / "platform.db"),
        ALL_IN_ONE_DATA_MODE="real",
        ALL_IN_ONE_HELP_DOCS_AUTO_BUILD="false",
    )
    Database.reset_instance()
    config_module._SETTINGS = None
    assert config_module.get_settings().db_path.resolve() == output / "platform.db"
    alpha = AlphaService()
    today = datetime.now().date()
    last_close = (today - timedelta(days=1)).isoformat()
    archive = output / "market.json"
    if not archive.exists():
        provider = EastmoneyDataSource(timeout_seconds=cfg["timeout_seconds"])
        history = {
            symbol: provider._load_kline_tencent(symbol, "daily", cfg["count"], "none", end_date=last_close)
            for symbol in cfg["symbols"]
        }
        market = {
            "history": history,
            "market": "CN",
            "is_mock": False,
            "source": "actual_tencent_daily_ohlcv",
            "price_adjustment": "none",
            "limitations": [
                "fixed_small_universe",
                "corporate_actions_not_included",
                "historical_trading_status_unavailable",
            ],
        }
        archive.write_text(json.dumps(market, ensure_ascii=False), encoding="utf-8")
    else:
        market = json.loads(archive.read_text(encoding="utf-8"))
    documents_path = output / cfg["documents_archive"]
    if not documents_path.exists():
        response = requests.get(cfg["news_article_url"], timeout=cfg["timeout_seconds"])
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        parser = VisibleText()
        parser.feed(response.text)
        text = " ".join(" ".join(parser.parts).split())
        begin = text.find(cfg["news_article_marker"])
        if begin < 0 or cfg["company_name"] not in text:
            raise RuntimeError("Actual cited company news could not be verified; no paid calls made")
        excerpt = text[begin : begin + cfg["news_article_excerpt_chars"]]
        documents = {
            "source": "actual_public_news_excerpt",
            "is_mock": False,
            "documents": [
                {
                    "id": digest([response.url, excerpt]),
                    "symbols": [cfg["company_symbol"]],
                    "text": excerpt,
                    "category": "news",
                    "published_at": cfg["news_article_published_at"],
                    "available_at": utc_now_iso(),
                    "source": response.url,
                    "timestamp_basis": "publication_from_original_page_first_collection_today_not_historical_PIT_archive",
                }
            ],
        }
        documents_path.write_text(json.dumps(documents, ensure_ascii=False), encoding="utf-8")
    else:
        documents = json.loads(documents_path.read_text(encoding="utf-8"))
    dataset = alpha.register_dataset(
        "真实小样本价量", "market", market, {"verified": True, "method": "actual_public_http"}
    )
    docs = alpha.register_dataset(
        "真实采集公司资料", "documents", documents, {"verified": True, "method": documents["source"]}
    )
    (output / "preparation.json").write_text(
        json.dumps(
            {
                "market_id": dataset["id"],
                "documents_id": docs["id"],
                "bars": {s: len(rows) for s, rows in market["history"].items()},
                "last_dates": {s: rows[-1]["date"] for s, rows in market["history"].items()},
                "document_source": documents["source"],
                "categories": sorted({row["category"] for row in documents["documents"]}),
                "research_symbols": cfg["research_symbols"],
                "historical_backtest_claim": False,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info(
        "Real data prepared: bars={} documents={} source={}",
        {s: len(rows) for s, rows in market["history"].items()},
        len(documents["documents"]),
        documents["source"],
    )
    if prepare_only:
        return
    model_id, model_name = prepare_model(alpha, cfg)
    service = AgentStrategyService()
    results = []
    for recipe in cfg["recipes"]:
        run = service.prepare(
            {
                "recipe": recipe,
                "backend": "api",
                "model_id": model_id,
                "market": "CN",
                "symbols": cfg["research_symbols"],
                "as_of": today.isoformat(),
                "validation_mode": "current_research",
                "market_dataset_id": dataset["id"],
                "documents_dataset_id": docs["id"],
                "scope": "real-small-sample-no-search",
                "options": {
                    "calls": cfg["model_calls"],
                    "output_tokens": cfg["max_output_tokens"],
                    "enable_thinking": cfg["enable_thinking"],
                },
            },
            Frame.create(today.isoformat(), market["history"]),
        )
        try:
            service.phase(run["id"], False, Frame.create(today.isoformat(), market["history"]))
            service.phase(run["id"], True, Frame.create(today.isoformat(), market["history"]))
        except Exception as exc:
            logger.warning("Real recipe {} rejected: {}", recipe, type(exc).__name__)
        final = service.store.get(run["id"])
        events = service.all_events(run["id"])
        usage = {}
        for event in events:
            if event["kind"] == "llm_response":
                for key, value in event["payload"].get("usage", {}).items():
                    if type(value) is int:
                        usage[key] = usage.get(key, 0) + value
        results.append(
            {
                "id": run["id"],
                "recipe": recipe,
                "status": final["status"],
                "result": final["result"],
                "missing": final["evidence"]["missing"],
                "usage": usage,
                "requests": sum(event["kind"] == "llm_request" for event in events),
            }
        )
    summary_path = output / ("summary-" + recipe + "-" + str(results[-1]["id"]) + ".json" if recipe else "summary.json")
    summary_path.write_text(
        json.dumps(
            {
                "actual_model": model_name,
                "results": results,
                "scope": "current_research_not_historical_performance",
                "unknown_failed_request_usage": "not_zero_not_estimated",
                "mass_parameter_search": False,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info(
        "Real small-sample finished: model={} results={}",
        model_name,
        [(r["recipe"], r["status"], r["usage"]) for r in results],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--recipe")
    args = parser.parse_args()
    main(args.prepare_only, args.recipe)
