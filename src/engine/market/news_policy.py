"""Versioned, inspectable inclusion rules separate geography from topic and effect."""

import hashlib
import json
import re
from datetime import datetime
from functools import lru_cache

import yaml

from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def news_policy() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/data/market_news.yaml").read_text(encoding="utf-8"))


def matches(text: str, term: str) -> bool:
    if term.isascii():
        return bool(re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])", text.lower()))
    return term in text


def classify(item: dict) -> dict:
    cfg = news_policy()
    text = str(item.get("title") or "") + " " + str(item.get("summary") or "")
    scopes = [region for region, words in cfg["regions"].items() if any(matches(text, word) for word in words)]
    region = "cross_border" if len(scopes) > 1 else scopes[0] if scopes else "unknown"
    reasons = [name for name, words in cfg["transmission"].items() if any(matches(text, word) for word in words)]
    excluded = any(matches(text, word) for word in cfg["exclude"])
    policy = any(matches(text, word) for word in cfg["policy_terms"])
    political = any(matches(text, word) for word in cfg["political_terms"])
    # Political events require an explicit transmission channel; politics alone is not a market signal.
    relevant = bool(reasons) and not excluded
    topics = ["policy"] if policy or political else ["finance"]
    if (policy or political) and any(
        key in reasons for key in ("markets_companies", "supply_energy", "monetary_policy")
    ):
        topics.append("finance")
    impacts = [tag for tag, words in cfg["impact_terms"].items() if any(matches(text, word) for word in words)]
    published = item.get("published_at")
    try:
        if not published or datetime.fromisoformat(str(published).replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("Unverified source time")
        time_status = "source_time"
    except ValueError:
        time_status = "unknown"
    return {
        "region": region,
        "topics": topics,
        "market_relevant": relevant,
        "relevance_reasons": reasons,
        "affected_markets": impacts,
        "time_status": time_status,
    }


def initialize(db) -> None:
    db.executescript("""CREATE TABLE IF NOT EXISTS news_classification(
        news_id INTEGER PRIMARY KEY, policy_hash TEXT NOT NULL, region TEXT NOT NULL, topics TEXT NOT NULL,
        market_relevant INTEGER NOT NULL, metadata TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS news_classification_filter ON news_classification(market_relevant,region);""")
    cfg = news_policy()
    version = hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    rows = db.query(
        "SELECT n.* FROM news_items n LEFT JOIN news_classification c ON c.news_id=n.id "
        "WHERE c.news_id IS NULL OR c.policy_hash!=? ORDER BY n.id DESC LIMIT ?",
        (version, cfg["classification_batch"]),
    )
    with db.transaction():
        for row in rows:
            metadata = classify(row)
            db.execute(
                "INSERT INTO news_classification VALUES(?,?,?,?,?,?) ON CONFLICT(news_id) DO UPDATE SET "
                "policy_hash=excluded.policy_hash,region=excluded.region,topics=excluded.topics,"
                "market_relevant=excluded.market_relevant,metadata=excluded.metadata",
                (
                    row["id"],
                    version,
                    metadata["region"],
                    json.dumps(metadata["topics"]),
                    int(metadata["market_relevant"]),
                    json.dumps(metadata, ensure_ascii=False),
                ),
            )
