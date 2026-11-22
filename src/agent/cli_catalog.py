"""Provider-scoped model metadata and explicitly sourced billing classifications."""

import math
import re

# Only the metadata failure type is used here.
import subprocess  # nosec B404
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import yaml
from json_repair import loads

from src.core.config import PROJECT_ROOT
from src.core.env_file import resolve_env_value
from src.core.logger import get_logger
from src.core.page_work import check
from src.core.process_env import process_environment

from .cli_catalog_cache import reuse
from .cli_catalog_transport import metadata
from .composer_config import normalize_backend
from .providers.native import executable
from .qoder_cli import QoderCliRunner


@lru_cache(maxsize=1)
def catalog_config():
    return yaml.safe_load((PROJECT_ROOT / "egs/config/ui/cli_catalog.yaml").read_text(encoding="utf-8"))


def billing(row):
    cfg = catalog_config()
    if row.get("is_free") is True or row.get("free") is True:
        return cfg["labels"]["free"]
    factor = row.get("price_factor")
    if isinstance(factor, (int, float)) and not isinstance(factor, bool) and math.isfinite(factor) and factor >= 0:
        return cfg["labels"]["credits"].format(factor=factor)
    kind = row.get("billing_type")
    pricing = row.get("pricing")
    if kind == "tokens" and isinstance(pricing, dict):
        rates = [pricing.get(key) for key in ("input", "output")]
        if (
            all(
                isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0
                for value in rates
            )
            and pricing.get("currency") in {"USD", "CNY", "EUR"}
            and pricing.get("unit") in {"per_million_tokens", "per_thousand_tokens"}
        ):
            return f"{cfg['labels']['tokens']} · {rates[0]}/{rates[1]} {pricing['currency']} {pricing['unit']} (input/output)"
    return (
        cfg["labels"].get(kind, cfg["labels"]["unknown"])
        if kind in {"subscription", "tokens"}
        else cfg["labels"]["unknown"]
    )


def normalize_catalog(value, backend, source):
    cfg = catalog_config()
    rows = value.get("models", value.get("data", [])) if isinstance(value, dict) else value
    if not isinstance(rows, list):
        raise ValueError("Invalid model catalogue")
    result, identifiers = [], set()
    for row in rows[: cfg["max_models"]]:
        if not isinstance(row, dict) or row.get("hidden") or row.get("enabled") is False:
            continue
        identifier = str(
            (row.get("id") if backend == "workbuddy" else None)
            or row.get("model")
            or row.get("id")
            or row.get("slug")
            or ""
        )[: cfg["max_identifier_chars"]]
        if not identifier or identifier in identifiers:
            continue
        identifiers.add(identifier)
        efforts = row.get("supportedReasoningEfforts", row.get("reasoning_efforts"))
        efforts = (
            [item.get("reasoningEffort") if isinstance(item, dict) else item for item in efforts]
            if isinstance(efforts, list)
            else None
        )
        if backend == "workbuddy":
            credits = re.fullmatch(r"x(\d+(?:\.\d+)?)(?:\s+credits)?", str(row.get("credits", "")).strip())
            if credits:
                factor = float(credits[1])
                row = {**row, "is_free": factor == 0, "price_factor": factor}
        result.append(
            {
                "id": identifier,
                "name": str(row.get("displayName") or row.get("name") or identifier)[: cfg["max_name_chars"]],
                "billing": billing(row),
                "source": source,
                "efforts": efforts,
            }
        )
    return result


def discover(backend, refresh=False):
    backend = normalize_backend(backend)
    cfg = catalog_config()
    configured = resolve_env_value(cfg["catalog_env"][backend])
    path = Path(configured) if configured else None
    runner = QoderCliRunner() if backend == "qoder" else None
    command = runner.executable() if runner else executable(backend) if backend != "workbuddy" else None
    environment = runner.environment() if runner else process_environment(backend)
    scope = (backend, configured, command, sorted(environment.items()))
    policy = {**cfg["cache"], "max_bytes": cfg["max_bytes"], "max_models": cfg["max_models"]}
    return reuse(scope, backend, refresh, policy, lambda: _discover(backend, path, command, environment, cfg))


def _discover(backend, path, command, environment, cfg):
    source = cfg["sources"][backend]
    status, rows = "ready", []
    try:
        if path:
            if not path.is_file() or path.stat().st_size > cfg["max_bytes"]:
                raise ValueError("Invalid metadata file")
            value = loads(path.read_text(encoding="utf-8-sig"))
            source = cfg["messages"]["configured"] + source
        elif not command:
            value, status = [], "missing"
        elif backend in {"codex", "qoder"}:
            value = metadata(
                [command, *cfg[backend + "_arguments"]], environment, PROJECT_ROOT, cfg, rpc=backend == "codex"
            )
        else:
            value, status = [], "unsupported"
        rows = normalize_catalog(value, backend, source)
        if status == "ready" and not rows:
            status = "empty"
    except InterruptedError:
        check()
        raise
    except (OSError, ValueError, TimeoutError, subprocess.SubprocessError):
        status = "failed"
    result = {
        "backend": backend,
        "rows": rows,
        "status": status,
        "source": source,
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "available": backend != "workbuddy",
    }
    get_logger("ui.catalog").info("CLI catalogue ready | backend={} status={} models={}", backend, status, len(rows))
    return result
