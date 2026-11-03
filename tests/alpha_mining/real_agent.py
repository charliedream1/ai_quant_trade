"""Small real-model verification; secrets remain solely in process environment."""

import argparse
import io
import json
import os
from html.parser import HTMLParser
from pathlib import Path
from threading import Event
from time import monotonic

import pandas as pd
import requests
import yaml
from dotenv import dotenv_values
from loguru import logger

import src.core.config as config_module
from src.alpha_mining.config import contained, digest
from src.alpha_mining.service import AlphaService
from src.core.config import PROJECT_ROOT
from src.core.database import Database
from src.core.timeutil import utc_now_iso
from src.data.eastmoney import EastmoneyDataSource
from src.data.relation_evidence import news_evidence


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.ignored = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignored = max(self.ignored - 1, 0)

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def prepare_model(service, cfg):
    environment = dotenv_values(cfg["environment_file"])
    key = environment.get("LLM_API_KEY") or environment.get("OPENAI_API_KEY")
    base = environment.get("LLM_BASE_URL") or environment.get("OPENAI_BASE_URL")
    model = environment.get("LLM_MODEL_NAME")
    if not key or not base or not model:
        raise RuntimeError("User-supplied environment has no usable LLM settings")
    os.environ["ALPHA_VERIFICATION_API_KEY"] = key
    existing = service.store.repo.list("llm_models", "name=?", ("真实小样本验收",))
    if existing:
        return existing[0]["id"], model
    row = service.store.repo.insert(
        "llm_models",
        {
            "name": "真实小样本验收",
            "base_url": base,
            "model_name": model,
            "api_key": "",
            "api_key_env": "ALPHA_VERIFICATION_API_KEY",
            "purpose": "用户授权的少调用流程验证",
            "max_tokens": cfg["max_output_tokens"],
            "timeout_seconds": cfg["model_timeout_seconds"],
            "temperature": cfg["model_temperature"],
            "enabled": 1,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        },
    )
    return row["id"], model


def macro_data(cfg, output):
    observations = []
    spec = cfg["macro"]
    bound = spec["vintage"] + "T23:59:59+00:00"
    for key, series in (("growth", spec["growth_series"]), ("inflation", spec["inflation_series"])):
        response = requests.get(
            spec["endpoint"],
            params={"id": series, "vintage_date": spec["vintage"], "cosd": spec["start"]},
            timeout=spec["timeout_seconds"],
        )
        response.raise_for_status()
        (output / (key + "-vintage.csv")).write_bytes(response.content)
        frame = pd.read_csv(io.StringIO(response.text))
        expected = series + "_" + spec["vintage"].replace("-", "")
        if list(frame.columns) != ["observation_date", expected]:
            raise RuntimeError("ALFRED did not return the requested vintage identity")
        frame[expected] = pd.to_numeric(frame[expected], errors="coerce")
        if key == "inflation":
            frame[expected] = frame[expected] / frame[expected].shift(12) * 100 - 100
        for _, row in frame.dropna().tail(spec["last_observations"]).iterrows():
            observations.append(
                {
                    "id": key + "-" + row["observation_date"],
                    "series": key,
                    "observation_date": row["observation_date"],
                    "value": float(row[expected]),
                    "published_at": bound,
                    "vintage_at": bound,
                    "available_at": bound,
                    "source": response.url,
                    "timestamp_basis": "conservative_vintage_end_bound_not_original_release_time",
                    "definition": "real_GDP_quarterly_growth_saar" if key == "growth" else "CPI_yoy_from_same_vintage",
                }
            )
    return {"observations": observations, "source": "ALFRED_requested_vintage", "is_mock": False}


def news_data(cfg, output):
    provider = EastmoneyDataSource(timeout_seconds=cfg["macro"]["timeout_seconds"])
    raw = provider._stock_news(cfg["company_symbol"])
    (output / "news-provider.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    now, documents = utc_now_iso(), []
    for item in raw:
        evidence = news_evidence(item, cfg["company_symbol"], cfg["company_name"])
        if evidence is None or evidence["method"] != "text_entity_match":
            continue
        text = str(item.get("title") or "") + "\n" + str(item.get("summary") or "")
        documents.append(
            {
                "id": digest([item.get("url"), text]),
                "symbols": [cfg["company_symbol"]],
                "text": text,
                "published_at": now,
                "available_at": now,
                "source": str(item.get("source") or "public_news"),
                "url": item.get("url"),
                "provider_published_at": item.get("published_at"),
                "timestamp_basis": "first_actual_collection_upper_bound_not_backdated_publication",
            }
        )
        if len(documents) == cfg["news_limit"]:
            break
    if not documents:
        response = requests.get(cfg["company_profile_url"], timeout=cfg["macro"]["timeout_seconds"])
        response.raise_for_status()
        (output / "corporate-profile.html").write_bytes(response.content)
        response.encoding = response.apparent_encoding
        parser = VisibleText()
        parser.feed(response.text)
        text = " ".join(" ".join(parser.parts).split())
        begin = text.find(cfg["company_profile_marker"])
        if begin < 0:
            raise RuntimeError("No authentic company profile or news available")
        excerpt = text[begin : begin + cfg["company_profile_excerpt_chars"]]
        documents = [
            {
                "id": digest(excerpt),
                "symbols": [cfg["company_symbol"]],
                "text": excerpt,
                "published_at": now,
                "available_at": now,
                "source": response.url,
                "scope": "historical_corporate_profile_retrieved_now_not_current_news",
                "timestamp_basis": "first_actual_collection_upper_bound_not_backdated_publication",
            }
        ]
        return {"documents": documents, "source": "actual_historical_official_corporate_profile", "is_mock": False}
    return {"documents": documents, "source": "actual_public_news_excerpt", "is_mock": False}


def wait(service, study_id, seconds):
    deadline = monotonic() + seconds
    while True:
        result = service.detail(study_id)
        if result["status"] not in {"discovering", "validating", "testing"}:
            return result
        if monotonic() > deadline:
            service.cancel(study_id)
            raise TimeoutError("Real-model study exceeded its bounded verification deadline")
        Event().wait(0.2)


def main(workflow="all"):
    cfg = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("real_agent.yaml").read_text(encoding="utf-8"))
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
    service = AlphaService()
    model_id, model_name = prepare_model(service, cfg)
    market = json.loads((PROJECT_ROOT / cfg["market_archive"]).read_text(encoding="utf-8"))
    dataset = service.register_dataset(
        "真实归档价量", "market", market, {"verified": True, "method": "real_http_archive", "sha256": digest(market)}
    )
    # Data preparation finishes before paid model calls.
    extras, preparation = {}, {}
    for kind, fetch in (("documents", news_data), ("macro", macro_data)):
        if workflow != "all" and kind != {"theme": "documents", "regime": "macro"}.get(workflow):
            continue
        try:
            payload = fetch(cfg, output)
            extras[kind] = service.register_dataset(
                "真实资料 " + kind, kind, payload, {"verified": True, "method": payload["source"]}
            )
        except Exception as exc:
            preparation[kind] = str(exc)
            logger.warning("Real auxiliary data preparation unavailable: {} {}", kind, type(exc).__name__)
    selection = {"model_id": model_id, "enable_thinking": cfg["enable_thinking"]}
    common = {"batch_size": 1, "models": {"default": selection}}
    studies = []
    if workflow in {"all", "alpha"}:
        run_alpha(service, cfg, common, dataset, studies)
    if "documents" in extras:
        theme = service.create(
            {
                **common,
                "name": "真实主题精炼小样本",
                "mode": "theme",
                "dataset_id": extras["documents"]["id"],
                "cutoff": utc_now_iso(),
                "theme": cfg["theme"],
                "model_call_budget": cfg["auxiliary_call_budget"],
            }
        )
        service.start(theme["id"], "run")
        studies.append(wait(service, theme["id"], cfg["max_wait_seconds"]))
    if "macro" in extras:
        regime = service.create(
            {
                **common,
                "name": "真实PIT体制单配置验收",
                "mode": "regime",
                "dataset_id": extras["macro"]["id"],
                "cutoff": cfg["macro"]["cutoff"],
                "asset_mapping": cfg["asset_mapping"],
                "market": "US",
                "configurations": [selection],
                "model_call_budget": cfg["auxiliary_call_budget"],
            }
        )
        service.start(regime["id"], "run")
        studies.append(wait(service, regime["id"], cfg["max_wait_seconds"]))
    finish_summary(service, studies, preparation, model_name, output, workflow)


def run_alpha(service, cfg, common, dataset, studies):
    first = service.create(
        {
            **common,
            "name": "真实单候选Alpha验收",
            "dataset_id": dataset["id"],
            "model_call_budget": cfg["alpha_call_budget"],
            "purpose": cfg["alpha_purpose"],
            "execution_costs": {"profile": "cn_a"},
        }
    )
    service.start(first["id"], "discover")
    discovered = wait(service, first["id"], cfg["max_wait_seconds"])
    if discovered["status"] == "discovered":
        service.seal(first["id"])
        service.start(first["id"], "validate")
        discovered = wait(service, first["id"], cfg["max_wait_seconds"])
    studies.append(discovered)


def finish_summary(service, studies, preparation, model_name, output, workflow):
    usage, calls = {}, 0
    summary = {
        "actual_model": model_name,
        "preparation_errors": preparation,
        "studies": [],
        "mass_parameter_search": False,
    }
    for study in studies:
        events = service.store.repo.db.query(
            "SELECT payload FROM alpha_events WHERE study_id=? AND kind='llm_response' ORDER BY id", (study["id"],)
        )
        for event in events:
            calls += 1
            for key, value in json.loads(event["payload"]).get("usage", {}).items():
                if type(value) is int:
                    usage[key] = usage.get(key, 0) + value
        summary["studies"].append({key: study[key] for key in ("id", "name", "mode", "status", "result")})
    summary.update(observed_model_responses=calls, provider_usage=usage)
    filename = "summary.json" if workflow == "all" else "summary-" + workflow + ".json"
    (output / filename).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        "Real-agent audit completed: model={} statuses={} observed_responses={} usage={}",
        model_name,
        [(study["mode"], study["status"]) for study in studies],
        calls,
        usage,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", choices=["all", "alpha", "theme", "regime"], default="all")
    main(parser.parse_args().workflow)
