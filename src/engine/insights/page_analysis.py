"""Explicit page-owned reports reuse insight Skill loading, validation and HTML rendering."""

from contextvars import ContextVar, copy_context
from datetime import date
from threading import Event, RLock, Thread
from time import monotonic
from uuid import uuid4

from src.core.config import get_settings
from src.core.page_analysis_snapshot import analysis_config, evidence
from src.core.page_work import CURRENT_PAGE, finish_run, own_run
from src.core.task_control import TaskEvent, cancel_lease
from src.core.timeutil import utc_now_iso
from src.data import current_market

from .config import insight_config
from .execution import execute
from .store import InsightStore

PAGE_EVIDENCE: ContextVar[dict | None] = ContextVar("page_analysis_evidence", default=None)
LOCK = RLock()
ACTIVE: dict = {}
STOPS: dict = {}


def cancel(identifier):
    store = InsightStore()
    row = store.detail(identifier)
    cfg = analysis_config()["ui"]
    if row["request"].get("kind") != "page_analysis":
        raise ValueError(cfg["invalid"])
    with LOCK:
        event = STOPS.get((str(get_settings().db_path), identifier))
        if event is not None:
            event.set()
    if row["status"] != "running":
        return row["status"]
    cancel_lease("insight", identifier)
    if not event or not any(item["kind"] == "cancellation" for item in store.events(identifier)):
        store.append(identifier, "cancellation", cfg["stopping"])
    return cfg["stopping"]


def settings(preset, language="en"):
    cfg = insight_config()
    page_cfg = analysis_config()
    cfg["defaults"]["deadline_seconds"] = page_cfg["limits"]["deadline_seconds"]
    cfg["tasks"]["page_analysis"] = {
        "label": preset["label"],
        "skill_dir": "page_analysis",
        "resources": ["SKILL.md"],
        "sections": page_cfg["sections_zh" if language == "zh" else "sections"],
        "instruction": page_cfg["methods"][preset["method"]]
        + "\n"
        + page_cfg["ui"]["chinese_report" if language == "zh" else "english_report"],
        "method_resources": page_cfg["resources"][preset["method"]],
        "shared_model_client": True,
    }
    cfg["ui"]["verification"] = page_cfg["ui"]["verification"]
    cfg["ui"].update(page_cfg["report_copy"][language])
    return cfg


def start(task, provider, inputs):
    with LOCK:
        return _start(task, provider, inputs)


def _start(task, provider, inputs):
    cfg = analysis_config()
    if task not in cfg["presets"]:
        raise ValueError(cfg["ui"]["invalid"])
    preset, market = cfg["presets"][task], current_market()
    language = "zh" if provider.get("language") == "zh" else "en"
    report_copy = {**cfg["ui"], **cfg["report_copy"][language]}
    if market == "US" and get_settings().data_mode != "mock":
        raise ValueError(cfg["ui"]["no_real_us"])
    sources = evidence(preset, inputs)
    page = CURRENT_PAGE.get()
    if page is None:
        raise ValueError(cfg["ui"]["missing"])
    key = str(get_settings().db_path), page.owner, page.revision
    if key in ACTIVE:
        raise ValueError(cfg["ui"]["busy"])
    identifier = uuid4().hex
    store = InsightStore()
    request = {
        **provider,
        "kind": "page_analysis",
        "page_task": task,
        "page_run_id": identifier,
        "market": market,
        "end_date": date.today().isoformat(),
        "page_inputs": inputs,
        "timeframe": "daily",
    }
    run = {"run_id": identifier, "request": request, "status": "running", "created_at": utc_now_iso()}
    stop = TaskEvent("insight", identifier, limit=insight_config()["defaults"]["max_concurrent_jobs"])
    cancelled = Event()
    deadline = monotonic() + cfg["limits"]["deadline_seconds"]
    context = {
        "market": market,
        "data_source": report_copy["source"],
        "is_mock": get_settings().data_mode == "mock",
        "sources": sources,
        "gaps": [report_copy["bounded"].format(**cfg["limits"])]
        + ([report_copy["mock"]] if get_settings().data_mode == "mock" else []),
    }
    try:
        store.save(run)
        ACTIVE[key] = identifier
        STOPS[(str(get_settings().db_path), identifier)] = cancelled
        own_run("page_analysis", identifier, cancelled.set)

        def work():
            token = PAGE_EVIDENCE.set(context)
            try:
                execute(
                    run,
                    store,
                    settings(preset, language),
                    cancelled=lambda: cancelled.is_set() or stop.is_set() or monotonic() >= deadline,
                )
                if cancelled.is_set() or stop.is_set() or monotonic() >= deadline:
                    run["status"] = "cancelled"
                    store.save(run)
            finally:
                PAGE_EVIDENCE.reset(token)
                finish_run("page_analysis", identifier)
                stop.close()
                with LOCK:
                    ACTIVE.pop(key, None)
                    STOPS.pop((str(get_settings().db_path), identifier), None)

        Thread(target=copy_context().run, args=(work,), daemon=True, name="page-skill-analysis").start()
    except Exception:
        ACTIVE.pop(key, None)
        STOPS.pop((str(get_settings().db_path), identifier), None)
        stop.close()
        raise
    return run
