"""Bounded per-turn page evidence, reused by model, CLI and knowledge conversations."""

import hashlib
import json
from contextvars import ContextVar
from functools import lru_cache

import yaml

from src.core.config import PROJECT_ROOT
from src.core.page_analysis_snapshot import analysis_config, evidence, portable, preset_matches_view
from src.core.page_work import CURRENT_PAGE, check
from src.core.redaction import redact
from src.data import current_market

TURN_PAGE_CONTEXT: ContextVar[dict | None] = ContextVar("assistant_turn_page_context", default=None)


@lru_cache(maxsize=1)
def context_config():
    return yaml.safe_load((PROJECT_ROOT / "egs/config/ui/assistant_context.yaml").read_text(encoding="utf-8"))


def compact(value):
    cfg = context_config()
    if isinstance(value, dict):
        return {key: compact(item) for key, item in list(value.items())[: cfg["compact_rows"]]}
    if isinstance(value, list):
        return [compact(item) for item in value[: cfg["compact_rows"]]]
    if isinstance(value, str):
        return value[: cfg["compact_text_chars"]]
    return value


def page_context(enabled=True, selections=None):
    check()
    cfg = context_config()
    if not enabled:
        return {"enabled": False, "status": cfg["ui"]["disabled"], "sources": []}
    page = CURRENT_PAGE.get()
    module, view = page.view_label if page and page.view_label else ("unknown", "unknown")
    result = {
        "enabled": True,
        "module": module,
        "view": view,
        "market": current_market(),
        "selections": {},
        "sources": [],
    }
    presets = {
        key: value
        for key, value in analysis_config()["presets"].items()
        if value["module"] == module and preset_matches_view(value, view)
    }
    stale, bounded = False, False
    methods = set()
    for key, preset in presets.items():
        selected = redact(portable((selections or {}).get(key, {})))
        selected = {name: value for name, value in selected.items() if name in preset.get("bindings", {})}
        if len(json.dumps(selected, ensure_ascii=False)) > cfg["selection_chars"]:
            result["selections"][key] = {"status": cfg["ui"]["truncated"]}
            bounded = True
            continue
        result["selections"][key] = selected
        try:
            sources = evidence(preset, selected)
        except ValueError as exc:
            stale = stale or "changed" in str(exc)
            continue
        for source in sources:
            if source["kind"] in methods:
                continue
            source = {**source, "id": f"P{len(result['sources']) + 1}"}
            if len(json.dumps(source, ensure_ascii=False)) > cfg["source_chars"]:
                source = {**source, "data": compact(source["data"]), "limitation": cfg["ui"]["truncated"]}
                bounded = True
            candidate = {**result, "sources": [*result["sources"], source]}
            if (
                len(result["sources"]) >= cfg["max_sources"]
                or len(json.dumps(candidate, ensure_ascii=False)) > cfg["max_chars"]
            ):
                bounded = True
                continue
            result["sources"].append(source)
            methods.add(source["kind"])
    result["status"] = (
        cfg["ui"]["stale"]
        if stale
        else cfg["ui"]["ready"]
        if result["sources"]
        else cfg["ui"]["unloaded"]
        if presets
        else cfg["ui"]["unsupported"]
    )
    if bounded:
        result["limitation"] = cfg["ui"]["truncated"]
    result["scope_key"] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return result


def summary(value):
    cfg = context_config()
    if not value.get("enabled"):
        return cfg["ui"]["disabled"]
    return cfg["ui"]["scope"].format(**value, count=len(value["sources"]))


def context_prompt():
    value = TURN_PAGE_CONTEXT.get()
    if not value or not value.get("enabled"):
        return ""
    cfg = context_config()
    encoded = json.dumps(redact(portable(value)), ensure_ascii=False)
    if len(encoded) > cfg["max_chars"]:
        encoded = json.dumps({"status": cfg["ui"]["truncated"], "sources": []})
    return "\n\n" + cfg["prompt"].format(context=encoded)


def context_identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def turn_metadata():
    value = TURN_PAGE_CONTEXT.get()
    if not value:
        return None
    return {
        key: value[key] for key in ("enabled", "module", "view", "market", "selections", "status") if key in value
    } | {"digest": context_identity(value), "source_count": len(value.get("sources", []))}
