"""Traditional ReAct acquisition, extraction and review under one shared call budget."""

import json
from typing import Any
from uuid import uuid4

from src.core.page_work import PageCancelled, PageWork, context

from .config import config
from .validation import apply_review, validate_graph


class ResearchWorkflow:
    def __init__(self, request, skill_text, corpus, generation, cancelled, emit, *, isolate_sources=False):
        self.request, self.skill = request, skill_text
        self.corpus, self.generation = corpus, generation
        self.cancelled, self.emit = cancelled, emit
        self.graph: dict[str, Any] = {"nodes": [], "edges": []}
        self.calls = 0
        self.isolate_sources = isolate_sources

    def source(self, method, value=None):
        if not self.isolate_sources:
            return getattr(self.corpus, method)(*(() if value is None else (value,)))
        from src.frontend.page_reads import read

        operation = {"load_local": "graph_local", "read": "graph_read", "search": "graph_search"}[method]
        lifetime = PageWork(uuid4().hex, 1, cancelled=self.cancelled)
        try:
            with context(lifetime):
                result = read(operation, (self.request, value), {})
        except PageCancelled:
            raise InterruptedError("Graph source acquisition cancelled") from None
        if method == "search":
            self.corpus.candidates.extend(result)
            return result
        rows = result if method == "load_local" else [result]
        added = []
        for row in rows:
            added.append(
                self.corpus.add(
                    row["title"],
                    row["text"],
                    url=row["url"],
                    published_at=row["published_at"],
                    provenance=row["provenance"],
                    document_id=row["document_id"],
                )
            )
        return added[0] if method == "read" else None

    def generate(self, stage, proposed=None):
        if self.cancelled():
            raise InterruptedError("Graph research cancelled or timed out")
        if self.calls >= config()["limits"]["calls"]:
            raise ValueError("Graph model-call budget exhausted")
        self.calls += 1
        prompt = config()["prompts"][stage].format(
            skill=self.skill,
            target=json.dumps({"id": self.request["symbol"], "name": self.request["company_name"]}, ensure_ascii=False),
            as_of=self.request["as_of"],
            relations=json.dumps(config()["relations"], ensure_ascii=False),
            sources=json.dumps(
                {"originals": self.corpus.prompt_sources(), "discovery_only": self.corpus.candidates},
                ensure_ascii=False,
            ),
            graph=json.dumps(proposed if proposed is not None else self.graph, ensure_ascii=False),
        )
        self.emit("model_call", {"stage": stage, "call": self.calls, "sources": len(self.corpus.sources)})
        return self.generation.complete(prompt)

    def load_sources(self):
        self.source("load_local")
        for url in self.request["urls"]:
            if self.cancelled():
                raise InterruptedError("Graph research cancelled")
            row = self.source("read", url)
            self.emit("source_read", {"source_id": row["id"]})

    def expand(self):
        action = self.generate("planner")
        if action.get("action") == "finish":
            return False
        if action.get("action") == "search":
            candidates = self.source("search", str(action.get("query") or ""))
            self.emit("search_candidates", candidates)
            if not candidates:
                return False
            action = self.generate("planner")
            if action.get("action") != "read" or action.get("url") not in {item["url"] for item in candidates}:
                raise ValueError("Choose a discovered original URL to read")
        if action.get("action") != "read":
            raise ValueError("Unsupported graph ReAct action")
        row = self.source("read", str(action.get("url") or ""))
        self.emit("source_read", {"source_id": row["id"]})
        return True

    def review(self):
        extracted = self.generate("extract")
        for attempt in range(config()["limits"]["validation_retries"] + 1):
            try:
                proposed = validate_graph(extracted, self.corpus, self.request)
                break
            except ValueError as exc:
                if attempt == config()["limits"]["validation_retries"] or self.calls + 2 > config()["limits"]["calls"]:
                    raise
                self.emit("validation_repair", {"attempt": attempt + 1, "reason": str(exc)})
                extracted = self.generate("repair", {"extraction": extracted, "validation_reason": str(exc)})
        # Never publish extraction until the entire proposed set passes review.
        self.graph = apply_review(proposed, self.generate("review", proposed))

    def run(self):
        self.load_sources()
        for index in range(self.request["depth"]):
            if self.corpus.sources:
                self.review()
                self.emit("graph_reviewed", {"round": index + 1, "edges": len(self.graph["edges"])})
                if index + 1 == self.request["depth"]:
                    break
            if not self.expand():
                break
        if self.corpus.sources and not self.graph["nodes"] and self.calls + 2 <= config()["limits"]["calls"]:
            self.review()
        if not self.graph["nodes"]:
            self.graph = {
                "nodes": [{"id": self.request["symbol"], "name": self.request["company_name"], "type": "stock"}],
                "edges": [],
            }
        if self.cancelled():
            raise InterruptedError("Graph research cancelled or timed out")
        return "completed" if self.graph["edges"] else "partial"
