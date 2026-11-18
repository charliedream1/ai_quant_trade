"""Bounded server-owned observations for explicit page analysis; no browser-supplied facts."""

import inspect
import json
import math
import re
from collections import OrderedDict
from functools import lru_cache
from threading import RLock
from time import monotonic

import yaml

from src.core.config import PROJECT_ROOT, get_settings
from src.core.page_work import CURRENT_PAGE
from src.core.redaction import redact
from src.core.timeutil import utc_now_iso
from src.data import current_market

LOCK = RLock()
SNAPSHOTS: OrderedDict = OrderedDict()


@lru_cache(maxsize=1)
def analysis_config():
    return yaml.safe_load((PROJECT_ROOT / "egs/config/ui/page_analysis.yaml").read_text(encoding="utf-8"))


def portable(value):
    cfg = analysis_config()["limits"]
    if hasattr(value, "to_plotly_json"):
        return {
            "plot_data": portable([trace.to_plotly_json() for trace in value.data]),
            "title": str(value.layout.title.text or ""),
        }
    if hasattr(value, "tolist"):
        return portable(value.tolist())
    if hasattr(value, "data") and hasattr(value.data, "to_dict"):
        value = value.data
    if hasattr(value, "to_dict"):
        value = value.head(cfg["rows"]).to_dict(orient="records")
    if isinstance(value, dict):
        if "headers" in value and "data" in value:
            return {"headers": portable(value["headers"]), "data": portable(value["data"])}
        return {
            str(key): portable(item)
            for key, item in value.items()
            if str(key) not in {"api_key", "accessToken", "token", "base_url", "executable"}
        }
    if isinstance(value, (list, tuple)):
        return [portable(item) for item in value[: cfg["rows"]]]
    if isinstance(value, str):
        if re.match(r"^(?:[A-Za-z]:[\\/]|/(?:home|Users|tmp|var)/)", value):
            return analysis_config()["ui"]["local_artifact"]
        return re.sub("<[^>]+>", " ", value)[: cfg["text_chars"]]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (bool, float, int)):
        return value
    return str(value)[: cfg["text_chars"]]


def capture(name, function, args, kwargs, value):
    page = CURRENT_PAGE.get()
    if page is None or page.is_set():
        return
    cfg = analysis_config()
    if not any(name in preset["reads"] for preset in cfg["presets"].values()):
        return
    if name == "factor_job" and value.get("status") != "completed":
        return
    signature = inspect.signature(function)
    if "self" in signature.parameters:
        signature = signature.replace(
            parameters=[value for key, value in signature.parameters.items() if key != "self"]
        )
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    scope = redact(portable(dict(bound.arguments)))
    if name == "kb_document_detail" and scope.get("doc_id"):
        from src.core.repository import Repository

        document = Repository().get("kb_documents", int(scope["doc_id"]))
        scope["library"] = document.get("library_name")
    if name == "rag_chat":
        value = value[2]
    data = redact(portable(value.get("result") if name == "factor_job" else value))
    if len(json.dumps(data, ensure_ascii=False, default=str)) > cfg["limits"]["evidence_chars"]:
        return
    key = str(get_settings().db_path), page.owner, page.revision, name
    with LOCK:
        SNAPSHOTS[key] = {
            "method": name,
            "scope": scope,
            "data": data,
            "captured": monotonic(),
            "captured_at": utc_now_iso(),
            "market": current_market(),
        }
        SNAPSHOTS.move_to_end(key)
        while len(SNAPSHOTS) > cfg["limits"]["snapshots"]:
            SNAPSHOTS.popitem(last=False)


def evidence(preset, inputs):
    page = CURRENT_PAGE.get()
    if page is None:
        raise ValueError(analysis_config()["ui"]["missing"])
    cfg = analysis_config()
    prefix = str(get_settings().db_path), page.owner, page.revision
    with LOCK:
        candidates = [
            value
            for key, value in SNAPSHOTS.items()
            if key[:3] == prefix
            and key[3] in preset["reads"]
            and value.get("market") == current_market()
            and monotonic() - value["captured"] < cfg["limits"]["ttl_seconds"]
        ]
    selected = []
    for row in candidates:
        if any(row["scope"].get(key) != value for key, value in preset.get("match", {}).items()):
            continue
        if any(
            key in row["scope"] and str(row["scope"][key] or "") != str(value or "") for key, value in inputs.items()
        ):
            continue
        selected.append(row)
    if not selected:
        raise ValueError(cfg["ui"]["stale"] if candidates else cfg["ui"]["missing"])
    if len(json.dumps(selected, ensure_ascii=False)) > cfg["limits"]["evidence_chars"]:
        raise ValueError("Selected evidence exceeds the report budget; narrow the rule-data scope first")
    return [
        {
            "id": f"E{index}",
            "kind": row["method"],
            "data": {"request": row["scope"], "observations": row["data"], "captured_at": row["captured_at"]},
            "data_source": "Completed platform rule callback",
            "is_mock": get_settings().data_mode == "mock",
        }
        for index, row in enumerate(selected, 1)
    ]
