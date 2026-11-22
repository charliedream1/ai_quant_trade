"""Bounded and grounded extraction for news keywords and topic groups."""

import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from html import unescape
from math import log
from zoneinfo import ZoneInfo

import jieba
import yaml
from filelock import FileLock

from src.core.config import PROJECT_ROOT, get_settings
from src.core.timeutil import utc_now


@lru_cache(maxsize=1)
def policy():
    return yaml.safe_load((PROJECT_ROOT / "egs/config/data/news_topics.yaml").read_text(encoding="utf-8"))


def key(value):
    return unicodedata.normalize("NFKC", str(value or "")).casefold().strip()


def source_time(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp if stamp.tzinfo else None
    except ValueError:
        return None


def time_range(scope, *, now=None):
    cfg = policy()
    days = cfg["window_days"].get(scope)
    if days is None:
        raise ValueError("News scope must be day, week, month or all")
    stamp = (now or utc_now()).astimezone(ZoneInfo(cfg["timezone"]))
    midnight = stamp.replace(hour=0, minute=0, second=0, microsecond=0)
    return (midnight - timedelta(days=days - 1)).isoformat(), stamp.isoformat()


@lru_cache(maxsize=1)
def segmenter():
    cache = get_settings().data_dir / "news_tokenizer"
    cache.mkdir(parents=True, exist_ok=True)
    tokenizer = jieba.Tokenizer()
    tokenizer.tmp_dir = str(cache)
    with FileLock(str(cache / "dictionary.lock")):
        tokenizer.initialize()
    for term in policy()["dictionary"]:
        tokenizer.add_word(term)
    return tokenizer


def _plain(text):
    return key(re.sub(r"<[^>]+>", " ", unescape(str(text or ""))))


def _canonical_terms():
    return {key(phrase): term for term, aliases in policy()["aliases"].items() for phrase in [term, *aliases]}


@lru_cache(maxsize=1024)
def terms(text):
    cleaned = _plain(text)
    stopwords = {key(word) for word in policy()["stopwords"]}
    aliases = _canonical_terms()
    tokens: list[str] = []
    for fragment in re.findall(r"[\u3400-\u9fff]+|[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*", cleaned):
        words = _chinese_words(fragment) if re.search(r"[\u3400-\u9fff]", fragment) else [fragment]
        tokens.extend(word for word in words if len(word) > 1 and word not in stopwords)
    for alias, canonical in aliases.items():
        if alias.isascii() and re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", cleaned):
            tokens.append(canonical)
    return tuple(aliases.get(word, word) for word in tokens)


@lru_cache(maxsize=1)
def _finance_dictionary():
    words = sorted(policy()["dictionary"], key=len, reverse=True)
    return re.compile("(" + "|".join(re.escape(word) for word in words) + ")")


def _chinese_words(fragment):
    for index, part in enumerate(_finance_dictionary().split(fragment)):
        if part:
            if index % 2:
                yield part
            else:
                yield from segmenter().lcut(part)


def _shingles(title):
    plain = _plain(title)
    normalized = re.sub(r"[\W_]+", "", plain)
    numeric_facts = tuple(re.findall(r"[+-]?\d+(?:[.,]\d+)*%?", plain))
    return normalized, numeric_facts, {normalized[i : i + 3] for i in range(len(normalized) - 2)}


def deduplicate(rows):
    seen = set()
    fingerprints: list[tuple[tuple[str, ...], set[str]]] = []
    threshold = policy()["limits"]["near_duplicate_similarity"]
    unique = []
    for row in rows:
        title, facts, grams = _shingles(row.get("title"))
        if (
            not title
            or (title, facts) in seen
            or any(
                grams and facts == other_facts and len(grams & other) / len(grams | other) >= threshold
                for other_facts, other in fingerprints
            )
        ):
            continue
        seen.add((title, facts))
        fingerprints.append((facts, grams))
        unique.append(row)
    return unique


def ranked_keywords(rows, top_n, *, now=None, tfidf=False):
    cfg = policy()
    limits, weights = cfg["limits"], cfg["weights"]
    samples = deduplicate(rows[: limits["sample"]])
    counts: Counter[str] = Counter()
    scores: dict[str, float] = defaultdict(float)
    sources: dict[str, set[str]] = {}
    evidence: dict[str, str] = {}
    now = now or utc_now()
    for row in samples:
        title = str(row.get("title") or "")[: limits["title_chars"]]
        heading = list(dict.fromkeys(terms(title)))
        summary = terms(str(row.get("summary") or "")[: limits["summary_chars"]])
        stamp = source_time(row.get("published_at"))
        hours = max(0, (now - stamp).total_seconds() / 3600) if stamp else weights["fresh_half_life_hours"]
        freshness = 0.5 ** (hours / weights["fresh_half_life_hours"])
        for word in list(dict.fromkeys([*heading, *summary]))[: limits["story_terms"]]:
            counts[word] += 1
            scores[word] += (weights["title"] if word in heading else weights["summary"]) * freshness
            sources.setdefault(word, set()).add(str(row.get("source") or ""))
            evidence.setdefault(word, title)
    for word in scores:
        scores[word] *= 1 + log(len(sources[word]))
        if tfidf:
            scores[word] *= cfg["modes"]["idf_floor"] + log((1 + len(samples)) / (1 + counts[word]))
    total = sum(scores.values()) or 1
    return [
        {
            "keyword": word,
            "count": counts[word],
            "weight": scores[word] / total,
            "sentiment": "neutral",
            "source_count": len(sources[word]),
            "headline": evidence[word],
        }
        for word in sorted(scores, key=lambda word: (-scores[word], word))[:top_n]
    ]


def grouped_topics(rows):
    cfg = policy()
    groups: dict[str, dict] = {}
    phrases = [(item["label"], {key(term) for term in item["terms"]}) for item in cfg["topics"]]
    for row in deduplicate(rows[: cfg["limits"]["sample"]]):
        title = str(row.get("title") or "")[: cfg["limits"]["title_chars"]]
        candidates = terms(title)
        hits = [(label, set(candidates) & variants) for label, variants in phrases]
        label, matched = max(hits, key=lambda item: len(item[1]))
        if not matched:
            continue
        topic = groups.setdefault(
            label,
            {"label": label, "count": 0, "headline": title, "published_at": row.get("published_at"), "terms": set()},
        )
        topic["count"] += 1
        topic["terms"].update(matched)
    return [
        dict(row, terms=sorted(row["terms"]))
        for row in sorted(groups.values(), key=lambda row: (-row["count"], row["label"]))
    ]
