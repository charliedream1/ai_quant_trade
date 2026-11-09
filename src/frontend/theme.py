"""Shared theme, CSS and browser runtime for every Gradio module."""

from __future__ import annotations

import json
from functools import lru_cache
from inspect import signature
from pathlib import Path
from typing import Any

import gradio as gr

from src.core.config import get_settings

from .common.chart_help import chart_help_js
from .common.navigation import navigation_config
from .i18n import technical_texts_json, translations_json

_ASSET_ROOT = Path(__file__).with_name("assets")

CSS = _ASSET_ROOT.joinpath("styles/base_theme.css").read_text(encoding="utf-8")

CSS += _ASSET_ROOT.joinpath("styles", "ai_console.css").read_text(encoding="utf-8")
CSS += _ASSET_ROOT.joinpath("styles", "composer.css").read_text(encoding="utf-8")
CSS += _ASSET_ROOT.joinpath("styles", "notifications.css").read_text(encoding="utf-8")
CSS += _ASSET_ROOT.joinpath("styles", "usability.css").read_text(encoding="utf-8")
HOME_CSS = _ASSET_ROOT.joinpath("styles", "home_dashboard.css").read_text(encoding="utf-8")
_AI_CONSOLE_JS = _ASSET_ROOT.joinpath("ai_console.js").read_text(encoding="utf-8")
_AI_CONSOLE_JS += _ASSET_ROOT.joinpath("home_dashboard.js").read_text(encoding="utf-8")
_AI_CONSOLE_JS += _ASSET_ROOT.joinpath("composer.js").read_text(encoding="utf-8")
_AI_CONSOLE_JS += (
    _ASSET_ROOT.joinpath("assistant_avatar.js")
    .read_text(encoding="utf-8")
    .replace("__NOTICE_CONFIG__", get_settings().api_prefix + "/notifications/config")
)
_AI_CONSOLE_JS += _ASSET_ROOT.joinpath("preview_panel.js").read_text(encoding="utf-8")
_AI_CONSOLE_JS += chart_help_js()

_APP_JS_TEMPLATE = _ASSET_ROOT.joinpath("workspace_runtime.js").read_text(encoding="utf-8")
APP_JS = (
    _APP_JS_TEMPLATE.replace("__UI_THEME__", "light")
    .replace("__AI_CONSOLE_RUNTIME__", _AI_CONSOLE_JS)
    .replace("__I18N_DICT__", translations_json())
    .replace("__I18N_TECHNICAL_TEXTS__", technical_texts_json())
    .replace("__WORKSPACE_ROUTING__", json.dumps(navigation_config(), ensure_ascii=False))
    .replace("__WORKSPACE_ROUTES__", _ASSET_ROOT.joinpath("workspace_routes.js").read_text(encoding="utf-8"))
)


def _supports_parameter(callable_object: Any, name: str) -> bool:
    return name in signature(callable_object).parameters


@lru_cache(maxsize=1)
def theme() -> gr.Theme:
    return gr.themes.Base(
        primary_hue=gr.themes.colors.emerald,
        secondary_hue=gr.themes.colors.slate,
        neutral_hue=gr.themes.colors.slate,
        radius_size=gr.themes.sizes.radius_sm,
        font=["Microsoft YaHei", "Arial", "sans-serif"],
    )


def theme_runtime_js(theme_mode: str | None = None) -> str:
    """Wrap the shared browser runtime with the server-configured theme."""
    if theme_mode is None:
        return APP_JS
    normalized = theme_mode if theme_mode in {"light", "dark", "system"} else "light"
    return (
        _APP_JS_TEMPLATE.replace("__UI_THEME__", normalized)
        .replace("__AI_CONSOLE_RUNTIME__", _AI_CONSOLE_JS)
        .replace("__I18N_DICT__", translations_json())
        .replace("__I18N_TECHNICAL_TEXTS__", technical_texts_json())
        .replace("__WORKSPACE_ROUTING__", json.dumps(navigation_config(), ensure_ascii=False))
        .replace("__WORKSPACE_ROUTES__", _ASSET_ROOT.joinpath("workspace_routes.js").read_text(encoding="utf-8"))
    )


def gradio_mount_options(theme_mode: str | None = None) -> dict[str, Any]:
    """Return UI options moved from Blocks to mount_gradio_app in Gradio 6."""
    if not _supports_parameter(gr.mount_gradio_app, "theme"):
        return {}
    options: dict[str, Any] = {"theme": theme(), "css": CSS}
    if _supports_parameter(gr.mount_gradio_app, "js"):
        options["js"] = theme_runtime_js(theme_mode)
    return options
