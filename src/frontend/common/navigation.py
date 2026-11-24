"""Canonical workspace links and compatible routes, without constructing Gradio pages."""

from functools import lru_cache
from html import escape
from urllib.parse import urlencode

import yaml

from src.core.config import PROJECT_ROOT
from src.core.page_analysis_snapshot import analysis_config
from src.engine.economics.config import economics_config
from src.frontend.registry import MODULES


@lru_cache(maxsize=1)
def navigation_config():
    config = yaml.safe_load((PROJECT_ROOT / "egs/config/ui/navigation.yaml").read_text(encoding="utf-8"))
    config["modules"] = {module.key: dict(module.views) for module in MODULES}
    config["stock_defaults"] = economics_config()["defaults"]["company_symbols"]
    config["report_views"] = sorted(
        {
            f"{preset['module']}/{view}"
            for preset in analysis_config()["presets"].values()
            if preset.get("show_panel", True)
            for view in preset["views"]
        }
    )
    return config


def resolve_destination(module, view=""):
    for row in navigation_config()["aliases"]:
        if row["module"] == module and row["view"] == (view or ""):
            return {"module": row["target"], "view": row["target_view"], "tab": row.get("tab", "")}
    return {"module": module, "view": view or "", "tab": ""}


def workspace_link(label, module, view="", **context):
    target = resolve_destination(module, view)
    values = {key: value for key, value in {**target, **context}.items() if value not in ("", None)}
    return f'<a class="workspace-shortcut" href="/app/?{escape(urlencode(values), quote=True)}">{escape(label)}</a>'
