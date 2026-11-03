"""Svelte Flow inside Gradio's supported custom HTML component lifecycle."""

from hashlib import sha256
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from packaging.version import Version
from starlette.staticfiles import StaticFiles

import gradio as gr
from src.frontend.service.graph_documents import graph_config

ROOT = Path(__file__).resolve().parent


class StrategyGraph(gr.HTML):
    def __init__(self, value: dict[str, Any] | None = None, patch: dict[str, Any] | None = None, **kwargs):
        super().__init__(
            value=value,
            html_template="<aiquant-strategy-graph></aiquant-strategy-graph>",
            js_on_load=(ROOT / "bootstrap.js").read_text(encoding="utf-8"),
            apply_default_css=False,
            patch=patch,
            assets_path=graph_config()["assets_path"],
            assets_version=sha256((ROOT / "assets/graph.js").read_bytes()).hexdigest()[:16],
            **kwargs,
        )

    def api_info(self):
        return {"type": "object", "additionalProperties": True}


def supported() -> bool:
    return Version(gr.__version__) >= Version("6.16.0")


def mount_graph_assets(app: FastAPI) -> None:
    app.mount(
        graph_config()["assets_path"],
        StaticFiles(directory=ROOT / "assets", check_dir=False),
        name="strategy-graph-assets",
    )
