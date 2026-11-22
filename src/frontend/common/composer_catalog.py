"""Per-browser catalogue revisions prevent delayed backend responses overwriting controls."""

from html import escape
from typing import Any

import gradio as gr

from src.agent.cli_catalog import catalog_config, discover
from src.agent.composer_config import composer_config, normalize_backend

from .callbacks import safe


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
        key = "workbuddy_setup" if catalog.get("status") == "missing" else "workbuddy"
        text += "\n\n" + cfg["messages"][key]
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


def model_options(catalog, backend, default_label):
    choices = [] if backend == "workbuddy" else [(default_label, "")]
    for row in catalog["rows"]:
        label = f"{row['name']} · {row['billing']}" if row.get("billing") else row["name"]
        choices.append((label, row["id"]))
    return choices


def bind_cli_catalog(backend, model, refresh, note, default_backend):
    """Reuse daily discovery in specialised research selectors."""
    selector = CatalogSelection([])
    state = gr.State({"backend": default_backend, "revision": 0})

    def begin(provider, current):
        current.update(backend=provider, revision=current["revision"] + 1)
        return current, gr.update(choices=[], value=None, interactive=False), catalog_config()["messages"]["loading"]

    def load(current, force=False, selected=None):
        provider, revision = current["backend"], current["revision"]
        if provider == "api":
            return gr.update(choices=[], value=None, interactive=False), ""
        result = selector.load_data(provider, force)
        if revision != current["revision"] or provider != current["backend"]:
            return gr.skip(), gr.skip()
        cfg = catalog_config()
        choices = model_options(result, provider, cfg["labels"]["default"])
        manual = provider in cfg["manual_backends"]
        if selected not in {value for _, value in choices}:
            selected = None if provider == "workbuddy" else ""
        return gr.update(
            choices=choices,
            value=selected,
            allow_custom_value=manual,
            interactive=bool(choices) or manual,
        ), details(result, selected)

    def load_fresh(current, selected):
        current["revision"] += 1
        return load(current, True, selected)

    backend.input(
        safe(begin, cancel_outputs=3),
        inputs=[backend, state],
        outputs=[state, model, note],
        queue=False,
        trigger_mode="multiple",
    ).then(
        safe(load, cancel_outputs=2),
        inputs=state,
        outputs=[model, note],
        queue=True,
        show_progress="hidden",
        trigger_mode="multiple",
        concurrency_limit=None,
    )
    refresh.click(
        safe(load_fresh, cancel_outputs=2),
        inputs=[state, model],
        outputs=[model, note],
        queue=True,
        show_progress="hidden",
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
        result = discover(backend, refresh)
        if backend == "workbuddy":
            from src.engine.market.model_graph.generation import workbuddy_paths

            try:
                workbuddy_paths()
            except (OSError, ValueError):
                return {**result, "backend": backend, "status": "missing", "rows": []}
        return result

    def load(self, state, refresh=False):
        backend, revision = state["backend"], state["revision"]
        catalog = self.load_data(backend, refresh)
        if state["revision"] != revision or state["backend"] != backend:
            return tuple(gr.skip() for _ in range(5))
        state["catalog"] = catalog
        cfg, profile = catalog_config(), composer_config()["backends"][backend]
        choices = model_options(catalog, backend, cfg["labels"]["default"] + " · " + cfg["labels"]["unknown"])
        selected = state.get("selected", "")
        selected = selected if selected in {value for _, value in choices} else None if backend == "workbuddy" else ""
        return (
            gr.update(choices=choices, value=selected, allow_custom_value=backend in cfg["manual_backends"]),
            effort_update(backend, catalog, selected),
            gr.update(
                choices=[(composer_config()["permissions"][item], item) for item in profile["permissions"]],
                value="read-only",
                interactive=len(profile["permissions"]) > 1,
            ),
            details(catalog, selected),
            gr.update(interactive=backend != "workbuddy" or bool(catalog["rows"])),
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
