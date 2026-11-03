"""Pure projections between visual documents and the existing strategy contracts."""

from copy import deepcopy
from functools import lru_cache
from typing import Any
from uuid import uuid4

import yaml

from src.core.config import PROJECT_ROOT
from src.strategy.composition.config import config, merge, template
from src.strategy.composition.validation import compile_plan, digest
from src.strategy.models.config import model_config


@lru_cache(maxsize=1)
def graph_config() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_ROOT / "egs/strategy_graph.yaml").read_text(encoding="utf-8"))


def materialize(definition: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    if depth > config()["defaults"]["max_depth"]:
        raise ValueError("Sub-strategy depth exceeded")
    value = deepcopy(definition)
    for sleeve in value.get("sleeves") or []:
        child = deepcopy(sleeve.get("definition") or template(str(sleeve.get("template") or "")))
        variant = sleeve.get("variant") or "baseline"
        child = merge(merge(child, (child.get("variants") or {"baseline": {}})[variant]), sleeve.get("overrides") or {})
        child["variants"] = {"baseline": {}}
        sleeve["definition"] = materialize(child, depth + 1)
        for key in ("template", "variant", "overrides"):
            sleeve.pop(key, None)
    return value


def schema() -> dict[str, Any]:
    cfg = config()
    components = deepcopy(cfg["components"])
    for key, profile in cfg["defaults"]["model_profiles"].items():
        components[key]["defaults"] = model_config(profile)
    return {
        "components": components,
        "portfolios": cfg["portfolios"],
        "defaults": {key: cfg["defaults"][key] for key in ("portfolio", "risk", "execution")},
        "max_nodes": cfg["defaults"]["max_nodes"],
        "max_depth": cfg["defaults"]["max_depth"],
    }


def scoped(document: dict[str, Any], path: list[str]) -> dict[str, Any]:
    value = document
    if len(path) > config()["defaults"]["max_depth"]:
        raise ValueError("Invalid graph scope")
    for key in path:
        found = next((s for s in value.get("sleeves") or [] if s["id"] == key), None)
        if found is None:
            raise ValueError("Unknown graph scope")
        value = found["definition"]
    return value


def document_payload(text: str, prior: dict[str, Any] | None = None) -> dict[str, Any]:
    value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ValueError("Strategy definition must be a mapping")
    prior = prior or {}
    document = materialize(value)
    issues = []
    try:
        compiled = compile_plan(document)
        compiled_digest = digest(compiled)
    except (ValueError, TypeError, KeyError) as exc:
        issues.append(str(exc))
        compiled_digest = ""
    return {
        "doc_id": prior.get("doc_id") or uuid4().hex,
        "edit_revision": prior.get("edit_revision", 0),
        "layout_session": prior.get("layout_session", ""),
        "layout_origin": prior.get("layout_origin", ""),
        "document": document,
        "base_digest": digest(value),
        "compiled_digest": compiled_digest,
        "schema": schema(),
        "config": graph_config(),
        "layout": prior.get("layout", {}),
        "layout_key": prior.get("layout_key", ""),
        "layout_revision": prior.get("layout_revision", 0),
        "applied_revision": prior.get("applied_revision", 0),
        "issues": issues,
        "evidence": prior.get("evidence", {}),
        "read_only": False,
    }


def validate_submission(payload: dict[str, Any], current: str) -> dict[str, Any]:
    cfg = graph_config()
    if not isinstance(payload, dict):
        raise ValueError("Graph payload must be a mapping")
    import_size = len(
        yaml.safe_dump({key: payload.get(key) for key in ("document", "layout")}, allow_unicode=True).encode("utf-8")
    )
    if import_size > cfg["limits"]["max_bytes"]:
        raise ValueError("Graph payload exceeds size limit")
    raw = yaml.safe_load(current)
    if not isinstance(payload, dict) or payload.get("base_digest") != digest(raw):
        raise ValueError("Stale draft: reload the current graph before applying")
    value = payload.get("document")
    if not isinstance(value, dict):
        raise ValueError("Missing graph document")
    compile_plan(value)
    return deepcopy(value)
