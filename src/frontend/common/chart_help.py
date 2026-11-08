"""One YAML catalog supplies lazy, accessible chart explanations."""

from __future__ import annotations

import json
from functools import lru_cache
from hashlib import sha256
from typing import Any

import yaml

from src.core.config import PROJECT_ROOT, get_settings


@lru_cache(maxsize=1)
def catalog() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/ui/chart_explanations.yaml").read_text(encoding="utf-8"))


def help_key(label: str) -> str:
    for key, item in catalog()["charts"].items():
        if label in item["labels"]:
            return key
    return "default"


def chart_help_js() -> str:
    assets = PROJECT_ROOT / "src/frontend/assets"
    revision = sha256(
        json.dumps(catalog(), sort_keys=True).encode()
        + (assets / "chart_help.js").read_bytes()
        + (assets / "styles/chart_help.css").read_bytes()
    ).hexdigest()[:16]
    endpoint = json.dumps(get_settings().api_prefix + "/ui/chart-explanations")
    return (
        """(() => { if (document.querySelector('script[data-chart-help]')) return;
const script = document.createElement('script'); script.dataset.chartHelp = '1';
script.src = '/static/chart_help.js?v="""
        + revision
        + "'; script.dataset.catalogUrl="
        + endpoint
        + "; document.head.append(script); const css=document.createElement('link'); css.rel='stylesheet'; css.href='/static/styles/chart_help.css?v="
        + revision
        + "'; document.head.append(css); })();"
    )
