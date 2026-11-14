"""Bounded Skill workflow with background runs, cancellation and immutable result reuse."""

import hashlib
import json
import os
from datetime import date
from pathlib import Path
from threading import RLock, Thread
from time import monotonic, sleep
from uuid import uuid4

from loguru import logger

from src.core.network_policy import validate_url
from src.core.page_work import CURRENT_PAGE, check, finish_run, own_run
from src.core.redaction import redact_text
from src.core.task_control import TaskEvent, lease_alive
from src.core.timeutil import utc_now_iso
from src.data import SecurityMasterService, current_market, normalize_market
from src.observability.instrumentation import traced

from .config import config, skill
from .evidence import EvidenceCorpus
from .generation import GraphGeneration
from .store import GraphStore
from .validation import connected_view
from .workflow import ResearchWorkflow

LOCK = RLock()
ACTIVE: set[tuple[str, str]] = set()


def shutdown():
    """Request cancellation of owned runs before application resources close."""
    with LOCK:
        owned = set(ACTIVE)
        for root, identifier in owned:
            (Path(root) / identifier / "cancel").touch()
    deadline = monotonic() + config()["limits"]["shutdown_seconds"]
    while monotonic() < deadline:
        with LOCK:
            if not ACTIVE.intersection(owned):
                return
        sleep(config()["limits"]["shutdown_poll_seconds"])


class GraphResearchService:
    def __init__(self, store=None, generator=None):
        self.store = store or GraphStore()
        self.generator = generator or GraphGeneration

    def normalize(self, payload):
        allowed = {
            "symbol",
            "market",
            "backend",
            "model_name",
            "reasoning_effort",
            "as_of",
            "lookback_days",
            "depth",
            "urls",
            "library_name",
            "document_ids",
            "session_id",
        }
        if not isinstance(payload, dict) or set(payload) - allowed:
            raise ValueError("Unknown graph request fields")
        request = dict(payload)
        request["market"] = normalize_market(request.get("market") or current_market())
        if request["market"] not in {"CN", "HK"}:
            raise ValueError("Model relationship research currently supports CN/HK target identities")
        if CURRENT_PAGE.get() is not None:
            from src.frontend.page_reads import read

            company = read("graph_resolve", (request.get("symbol"), request["market"]), {})
        else:
            company = SecurityMasterService().resolve(request.get("symbol"), request["market"])
        if not company:
            raise ValueError("Cannot resolve the selected company")
        request.update(symbol=company["symbol"], company_name=company["name"])
        request["backend"] = request.get("backend") or config()["default_backend"]
        if request["backend"] not in config()["providers"]:
            raise ValueError("This CLI lacks a verified graph text-only profile; select Qoder or configured WorkBuddy")
        name = request.get("model_name") or ""
        effort = request.get("reasoning_effort") or ""
        if not isinstance(name, str) or name.startswith("-") or any(ord(char) < 32 for char in name):
            raise ValueError("Invalid CLI model identifier")
        if effort not in {"", "low", "medium", "high", "xhigh"}:
            raise ValueError("Unsupported reasoning effort")
        if request["backend"] == "workbuddy" and effort:
            raise ValueError("WorkBuddy graph profile does not support a verified reasoning-effort flag")
        request["as_of"] = str(request.get("as_of") or date.today().isoformat())
        if date.fromisoformat(request["as_of"]) > date.today():
            raise ValueError("Graph as-of date cannot be in the future")
        request["lookback_days"] = int(request.get("lookback_days") or config()["limits"]["lookback_days"])
        if not 1 <= request["lookback_days"] <= config()["limits"]["max_lookback_days"]:
            raise ValueError("Graph lookback is outside the configured range")
        request["depth"] = int(request.get("depth") or 1)
        if not 1 <= request["depth"] <= config()["limits"]["rounds"]:
            raise ValueError("Graph depth exceeds configured expansion budget")
        urls = request.get("urls") or []
        if not isinstance(urls, list) or any(not isinstance(url, str) for url in urls):
            raise ValueError("Graph source URLs must be a list")
        if len(urls) > config()["limits"]["sources"]:
            raise ValueError("Too many graph source URLs")
        request["urls"] = urls
        for url in urls:
            validate_url(url)
        if not isinstance(request.get("document_ids", []), list):
            raise ValueError("document_ids must be a list")
        if len(json.dumps(request, ensure_ascii=False)) > config()["limits"]["input_chars"]:
            raise ValueError("Graph request exceeds input budget")
        return request

    def start(self, payload):
        if int(os.environ.get("ALL_IN_ONE_PROVIDER_DEPTH", "0")) > 0:
            raise ValueError("A model-provider subprocess cannot launch a graph Skill")
        request = self.normalize(payload)
        check()
        text, digest = skill()
        with LOCK:
            identifier = uuid4().hex
            lease = TaskEvent("relation_graph", identifier, limit=config()["limits"]["active_runs"])
            row = {
                "run_id": identifier,
                "status": "queued",
                "request": request,
                "created_at": utc_now_iso(),
                "skill": config()["skill"],
                "skill_sha256": digest,
                "config_sha256": hashlib.sha256(json.dumps(config(), sort_keys=True).encode()).hexdigest(),
                "research_scope": "current exploratory research; no historical PIT qualification",
                "page_owned": CURRENT_PAGE.get() is not None,
            }
            try:
                self.store.save(row)
                ACTIVE.add((str(self.store.root), identifier))
                Thread(
                    target=self._execute, args=(row, text, lease), daemon=True, name=f"relation-{identifier}"
                ).start()
                own_run("model_graph", identifier, lambda: self.store.cancel(identifier))
            except Exception:
                ACTIVE.discard((str(self.store.root), identifier))
                lease.close()
                row.update(status="failed", error="Could not start graph worker")
                self.store.save(row)
                raise
        return row

    @traced("agent.stock_relation_skill", "agent")
    def _execute(self, row, skill_text, lease):
        started = monotonic()
        identifier = row["run_id"]
        corpus = EvidenceCorpus(row["request"])
        workflow = None
        generation = None
        limits = config()["limits"]

        def cancelled():
            return lease.is_set() or self.store.cancelled(identifier) or monotonic() - started > limits["seconds"]

        try:
            row.update(status="running", started_at=utc_now_iso())
            self.store.save(row)
            generation = self.generator(row["request"], self.store.directory(identifier), cancelled)
            workflow = ResearchWorkflow(
                row["request"],
                skill_text,
                corpus,
                generation,
                cancelled,
                lambda kind, data: self.store.event(identifier, kind, data),
                isolate_sources=bool(row.get("page_owned")),
            )
            row["status"] = workflow.run()
        except Exception as exc:
            row["status"] = (
                "cancelled" if cancelled() else "partial" if workflow and workflow.graph.get("edges") else "failed"
            )
            row["error"] = type(exc).__name__
            row["error_message"] = redact_text(str(exc))[:500]
            logger.log(
                "DEBUG" if row["status"] == "cancelled" else "WARNING",
                "Graph Skill stopped | run={} error_type={}",
                identifier,
                type(exc).__name__,
            )
            self.store.event(identifier, "error", {"error_type": type(exc).__name__})
        finally:
            with LOCK:
                try:
                    self._persist(row, workflow, generation, corpus, started)
                finally:
                    finish_run("model_graph", identifier)
                    lease.close()
                    ACTIVE.discard((str(self.store.root), identifier))

    def _persist(self, row, workflow, generation, corpus, started):
        identifier = row["run_id"]
        graph = workflow.graph if workflow else {"nodes": [], "edges": []}
        calls = workflow.calls if workflow else 0
        (self.store.directory(identifier) / "evidence.json").write_text(
            json.dumps(corpus.sources, ensure_ascii=False), encoding="utf-8"
        )
        if row["status"] in {"completed", "partial"}:
            graph.update(
                run_id=identifier,
                market=row["request"]["market"],
                mode="model",
                as_of=row["request"]["as_of"],
                skill=row["skill"],
                skill_sha256=row["skill_sha256"],
                evidence=corpus.sources,
                sources_first_seen_now=True,
                calls=generation.calls if generation else [],
                model_calls_attempted=calls,
            )
            (self.store.directory(identifier) / "graph.json").write_text(
                json.dumps(graph, ensure_ascii=False, allow_nan=False), encoding="utf-8"
            )
        row.update(finished_at=utc_now_iso(), duration_ms=round((monotonic() - started) * 1000), model_calls=calls)
        self.store.save(row)
        self.store.event(identifier, "finished", {"status": row["status"]})

    def detail(self, identifier):
        with LOCK:
            row = self.store.get(identifier)
            if (
                row["status"] in {"queued", "running"}
                and (str(self.store.root), identifier) not in ACTIVE
                and not lease_alive("relation_graph", identifier)
            ):
                row.update(status="interrupted", error="Owning process stopped; restart explicitly")
                self.store.save(row)
        return row

    def result(self, identifier, include_inferences=False):
        result = self.store.result(identifier)
        if include_inferences:
            return result
        selected = [edge for edge in result["edges"] if edge["classification"] == "stated" and not edge["expired"]]
        return connected_view({**result, "edges": selected})
