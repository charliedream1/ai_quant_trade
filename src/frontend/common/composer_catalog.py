"""Per-browser catalogue revisions prevent delayed backend responses overwriting controls."""

from html import escape
from typing import Any

import gradio as gr

from src.agent.cli_catalog import catalog_config, discover
from src.agent.composer_config import composer_config, normalize_backend


def details(catalog, identifier):
    cfg = catalog_config()
    row = next((item for item in catalog.get("rows", []) if item["id"] == identifier), None)
    text = cfg["messages"]["detail"].format(
        billing=row["billing"] if row else cfg["labels"]["unknown"],
        source=catalog.get("source", cfg["sources"]["generic_agent"]),
        updated=catalog.get("updated", cfg["messages"]["not_refreshed"]),
    )
    text += "\n\n" + cfg["messages"].get(catalog.get("status", "unknown"), cfg["messages"]["unknown"])
    if catalog.get("cache_reused"):
        text += "\n\n" + cfg["messages"]["reused"]
    if catalog.get("stale"):
        text += "\n\n" + cfg["messages"]["stale"]
    if catalog.get("backend") == "workbuddy":
        text += "\n\n" + cfg["messages"]["workbuddy"]
    backend = catalog.get("backend", "generic_agent")
    return escape(composer_config()["backends"][backend]["label"] + " · " + text)


def effort_update(backend, catalog, identifier):
    cfg = composer_config()
    supported = cfg["backends"][backend]["efforts"]
    row: dict[str, Any] = next((item for item in catalog.get("rows", []) if item["id"] == identifier), {})
    if row.get("efforts") is not None:
        supported = [item for item in supported if not item or item in row["efforts"]]
    labels = {value: label for label, value in cfg["efforts"]}
    return gr.update(
        choices=[(labels.get(item, item), item) for item in supported], value="", interactive=len(supported) > 1
    )


class CatalogSelection:
    def __init__(self, models, loader=None):
        self.initial_choices, self.loader = models, loader

    def begin(self, selected, state):
        selected = normalize_backend(selected)
        state.update(backend=selected, revision=state.get("revision", 0) + 1, catalog={}, selected="")
        return (
            state,
            gr.update(choices=[], value=None, allow_custom_value=False),
            effort_update(selected, {}, ""),
            gr.update(value="read-only", interactive=False),
            catalog_config()["messages"]["loading"],
            gr.update(interactive=False),
        )

    def load_data(self, backend, refresh=False):
        if backend == "generic_agent":
            choices = self.loader() if self.loader else self.initial_choices
            catalog = {
                "backend": backend,
                "rows": [
                    {"id": value, "name": name, "billing": catalog_config()["labels"]["unknown"]}
                    for name, value in choices
                ],
                "status": "unknown",
            }
            return catalog
        return discover(backend, refresh)

    def load(self, state, refresh=False):
        backend, revision = state["backend"], state["revision"]
        catalog = self.load_data(backend, refresh)
        if state["revision"] != revision or state["backend"] != backend:
            return tuple(gr.skip() for _ in range(5))
        state["catalog"] = catalog
        cfg, profile = catalog_config(), composer_config()["backends"][backend]
        choices = [(cfg["labels"]["default"] + " · " + cfg["labels"]["unknown"], "")]
        choices.extend((row["name"] + " · " + row["billing"], row["id"]) for row in catalog["rows"])
        selected = state.get("selected", "")
        selected = selected if selected in {value for _, value in choices} else ""
        return (
            gr.update(choices=choices, value=selected, allow_custom_value=backend in cfg["manual_backends"]),
            effort_update(backend, catalog, selected),
            gr.update(
                choices=[(composer_config()["permissions"][item], item) for item in profile["permissions"]],
                value="read-only",
                interactive=len(profile["permissions"]) > 1,
            ),
            details(catalog, selected),
            gr.update(interactive=backend != "workbuddy"),
        )

    def refresh(self, state):
        state["revision"] = state.get("revision", 0) + 1
        return self.load(state, True)

    def select(self, identifier, backend, state):
        backend = normalize_backend(backend)
        if backend != state.get("backend"):
            return gr.skip(), gr.skip()
        state["selected"] = identifier
        return details(state.get("catalog", {}), identifier), effort_update(
            backend, state.get("catalog", {}), identifier
        )
