"""Scoped, immutable lexical caches over current source chunks; no vector storage."""

import hashlib
import json
import math
import re
import sqlite3
from collections import Counter

from filelock import FileLock

from .config import knowledge_config
from .files import KnowledgeFiles


def tokens(text):
    """Use Latin words and overlapping CJK bigrams for portable FTS5 input."""
    result: list[str] = []
    for word in re.findall(r"[a-z0-9_]+|[\u3400-\u9fff]+", text.casefold()):
        if re.fullmatch(r"[\u3400-\u9fff]+", word):
            result.extend(word[i : i + 2] for i in range(max(1, len(word) - 1)))
        else:
            result.append(word)
    return result


class SAG2Index:
    def __init__(self, repo, documents):
        self.policy = knowledge_config()["sag2"]
        self.rows = {}
        for document in documents:
            chunks = repo.db.query(
                "SELECT * FROM kb_document_chunks WHERE doc_id=? ORDER BY chunk_index", (document["id"],)
            )
            for chunk in chunks:
                self.rows[chunk["id"]] = {
                    **document,
                    "chunk_id": chunk["id"],
                    "chunk_index": chunk["chunk_index"],
                    "chunk_heading": chunk["heading"],
                    "chunk_content": chunk["content"],
                    "snippet": chunk["content"],
                    "line_number": str(document.get("content") or "")[
                        : max(0, str(document.get("content") or "").find(chunk["content"]))
                    ].count("\n")
                    + 1,
                }
                if len(self.rows) > self.policy["max_index_chunks"]:
                    raise ValueError("SAG2 scope exceeds max_index_chunks; select a smaller scope")
        material = [
            (key, row["id"], row["title"], row["chunk_heading"], row["chunk_content"])
            for key, row in sorted(self.rows.items())
        ]
        self.fingerprint = hashlib.sha256(
            json.dumps([self.policy["index_version"], material], ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        root = KnowledgeFiles(repo).root
        directory = (root / self.policy["index_directory"]).resolve()
        if not directory.is_relative_to(root):
            raise ValueError("SAG2 index directory must stay inside knowledge storage")
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / (self.fingerprint + ".sqlite3")
        self.db = sqlite3.connect(self.path)
        try:
            with FileLock(str(self.path) + ".lock", timeout=self.policy["index_lock_seconds"]):
                self._prepare()
        except Exception:
            self.db.close()
            raise

    def _prepare(self):
        with self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS ready (fingerprint TEXT PRIMARY KEY)")
            self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(title, heading, body)")
            self.reused = bool(
                self.db.execute("SELECT 1 FROM ready WHERE fingerprint=?", (self.fingerprint,)).fetchone()
            )
            if not self.reused:
                self.db.execute("DELETE FROM passages")
                self.db.executemany(
                    "INSERT INTO passages(rowid,title,heading,body) VALUES(?,?,?,?)",
                    [
                        (
                            key,
                            " ".join(tokens(row["title"])),
                            " ".join(tokens(row["chunk_heading"])),
                            " ".join(tokens(row["chunk_content"])),
                        )
                        for key, row in self.rows.items()
                    ],
                )
                self.db.execute("INSERT INTO ready VALUES(?)", (self.fingerprint,))
        self.frequencies: Counter[str] = Counter()
        for row in self.rows.values():
            self.frequencies.update(set(tokens(row["chunk_content"])))

    def close(self):
        self.db.close()

    def recall(self, terms, limit, excluded=()):
        words = list(dict.fromkeys(terms))[: self.policy["query_terms"]]
        if not words:
            return []
        expression = " OR ".join('"' + word.replace('"', '""') + '"' for word in words)
        # Rank only this authorized corpus; filter seen chunks before truncating.
        results = self.db.execute(
            "SELECT rowid,bm25(passages) AS relevance FROM passages WHERE passages MATCH ? "
            "ORDER BY relevance,rowid LIMIT ?",
            (expression, limit + len(excluded)),
        )
        return [
            {**self.rows[key], "bm25_score": -score, "score": -score} for key, score in results if key not in excluded
        ][:limit]

    def expansion_terms(self, evidence, used):
        scores: dict[str, float] = {}
        stopwords = set(self.policy["stopwords"])
        for rank, row in enumerate(evidence[: self.policy["seed_count"]]):
            for term, count in Counter(tokens(row["chunk_content"])).items():
                if term in used or term in stopwords:
                    continue
                rarity = math.log1p(len(self.rows) / self.frequencies[term])
                scores[term] = scores.get(term, 0.0) + (1 + math.log(count)) * rarity / (rank + 1)
        return [
            term
            for term, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[
                : self.policy["expansion_terms"]
            ]
        ]
