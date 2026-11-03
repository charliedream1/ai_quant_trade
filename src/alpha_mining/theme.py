"""LLM refines associations; frozen literal rules create the actual theme universe."""

import re
from typing import Any

import pandas as pd

from .agents import AgentSession
from .backtest import paired_results, plan_definition, simulate
from .config import digest, invalid
from .pit import known_documents
from .store import AlphaStore


def _words(values: Any) -> list[str]:
    if (
        not isinstance(values, list)
        or len(values) > 100
        or any(not isinstance(value, str) or not 1 <= len(value.strip()) <= 80 for value in values)
    ):
        raise invalid("主题词表必须是有界非空短语列表")
    return sorted({value.strip() for value in values})


def _matches(text: str, words: list[str]) -> list[str]:
    return [
        word
        for word in words
        if (
            re.search(r"(?<![A-Za-z0-9])" + re.escape(word) + r"(?![A-Za-z0-9])", text, re.IGNORECASE)
            if word.isascii()
            else word in text
        )
    ]


def theme_scores(documents: list[dict], words: list[str], exclusions: list[str]) -> dict:
    scores: dict[str, int] = {}
    evidence = []
    for document in documents:
        matched = _matches(document["text"], words)
        if not matched or _matches(document["text"], exclusions):
            continue
        for symbol in document["symbols"]:
            scores[symbol] = scores.get(symbol, 0) + len(matched)
            evidence.append(
                {
                    "document_id": document["id"],
                    "symbol": symbol,
                    "terms": matched,
                    "available_at": document["available_at"],
                    "scope": "provided_text_only",
                }
            )
    return {"scores": scores, "evidence": evidence, "semantics": "theme_relevance_not_expected_return"}


def run_theme(store: AlphaStore, study: dict, session: AgentSession, emit) -> dict:
    dataset = store.get("alpha_datasets", study["dataset_id"])
    cfg = study["config"]
    documents = known_documents(dataset["payload"]["documents"], cfg["cutoff"])
    if not documents:
        raise invalid("截止时点没有可用资料，不能用当前新闻补历史")
    output = session.run("theme", {"theme": cfg["theme"], "documents": documents}, cfg["theme"])
    words, exclusions = _words(output.get("keywords")), _words(output.get("exclusions", []))
    if not words:
        raise invalid("LLM没有给出可冻结的主题词表")
    lookup = {row["id"]: row for row in documents}
    associations = output.get("associations")
    if not isinstance(associations, list):
        raise invalid("主题关联必须为列表")
    for row in associations:
        original = lookup.get(str(row.get("document_id"))) if isinstance(row, dict) else None
        if (
            original is None
            or row.get("symbol") not in original["symbols"]
            or not row.get("quote")
            or row["quote"] not in original["text"]
            or not row.get("relation")
        ):
            raise invalid("主题引用不存在、公司不符或摘录不是实际原文")
    seed_words = [cfg["theme"]]
    manual = cfg.get("manual_keywords") or seed_words
    comparisons = {
        "no_llm": theme_scores(documents, seed_words, []),
        "human_dictionary": theme_scores(documents, manual, []),
        "llm_refined": theme_scores(documents, words, exclusions),
    }
    approved_symbols = {row["symbol"] for row in associations}
    frozen_symbols = sorted(set(comparisons["llm_refined"]["scores"]) & approved_symbols)
    result = {
        "keywords": words,
        "exclusions": exclusions,
        "associations": associations,
        "frozen_symbols": frozen_symbols,
        "cutoff": cfg["cutoff"],
        "comparisons": comparisons,
        "data_digest": dataset["digest"],
        "dictionary_digest": digest([words, exclusions]),
        "document_count": len(documents),
        "source": dataset["provenance"],
        "export_ready": bool(frozen_symbols)
        and bool(dataset["provenance"].get("verified"))
        and not dataset["payload"]["is_mock"],
        "comparison_scope": "association_and_coverage_only_until_market_history_supplied",
        "requires_human_dictionary_confirmation": True,
        "direct_trading_signal": False,
        "automatic_live_trading": False,
    }
    if cfg.get("market_dataset_id"):
        result["market_comparisons"] = theme_backtests(store, study, comparisons, documents, emit, session.cancelled)
        result["comparison_scope"] = "historically_available_documents_frozen_dictionaries_shared_ledger"
    emit(
        "theme_evidence_verified",
        {"documents": len(documents), "associations": len(associations), "symbols": frozen_symbols},
    )
    return result


def theme_backtests(store, study, comparisons, documents, emit, cancelled):
    cfg = study["config"]
    snapshot = store.get("alpha_datasets", cfg["market_dataset_id"])["payload"]
    names = sorted(snapshot["history"])
    days = sorted(
        {row["date"] for rows in snapshot["history"].values() for row in rows if row["date"] >= cfg["cutoff"][:10]}
    )
    # The vocabulary was refined after reading all supplied evidence. It cannot be
    # backdated to the publication of the first document used in that refinement.
    if len(days) < cfg["policy"]["min_test_dates"]:
        return {"status": "insufficient_market_dates_after_dictionary_freeze", "vocabulary_available_at": cfg["cutoff"]}
    results, baseline = {}, None
    for label in ("no_llm", "human_dictionary", "llm_refined"):
        scores = comparisons[label]["scores"]
        rows = [
            {symbol: float(scores[symbol]) if symbol in scores else float("nan") for symbol in names} for day in days
        ]
        values = pd.DataFrame(rows, index=days)
        definition = plan_definition(study, 1, names)
        actual = simulate(study, snapshot, days, definition, values, 1, emit, cancelled)
        if baseline is None:
            baseline_definition = plan_definition(study, 1, names, benchmark=True)
            baseline = simulate(study, snapshot, days, baseline_definition, None, 1, emit, cancelled)
        results[label] = paired_results(actual, baseline, cfg["policy"])
    return {
        "status": "research_replay_with_vocabulary_availability_not_unseen_model_oos",
        "dictionaries": results,
        "vocabulary_available_at": cfg["cutoff"],
        "has_pre_cutoff_backfill": False,
    }
