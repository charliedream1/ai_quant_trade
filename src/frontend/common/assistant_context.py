"""Bind safe current controls; context acquisition occurs only on preview or send."""

from html import escape
from typing import Any

import gradio as gr

from src.core.assistant_page_context import TURN_PAGE_CONTEXT, context_config, context_identity, page_context, summary
from src.core.page_analysis_snapshot import analysis_config

from .callbacks import safe


def controls():
    cfg = context_config()
    parent = gr.context.get_blocks_context()
    if parent is None:
        raise ValueError("Assistant controls require a mounted page")
    blocks = parent.blocks
    bindings = {}
    for key, preset in analysis_config()["presets"].items():
        for field, selector in preset.get("bindings", {}).items():
            component = next(
                (
                    item
                    for item in blocks.values()
                    if all(
                        getattr(item, "elem_id" if name == "id" else name, None) == value
                        for name, value in selector.items()
                    )
                ),
                None,
            )
            if component is not None:
                bindings[(key, field)] = component
    inputs = list(dict.fromkeys(bindings.values()))
    enabled = gr.Checkbox(value=True, label=cfg["ui"]["enabled"], elem_id="assistant-use-page")
    preview = gr.Button(cfg["ui"]["preview"], elem_id="assistant-context-preview")
    gr.HTML(
        f'<span id="assistant-context-state" data-reset="{escape(cfg["ui"]["changed"], quote=True)}" hidden></span>'
    )
    badge = gr.Markdown(cfg["ui"]["pending"], elem_id="assistant-context-scope", elem_classes=["no-i18n"])
    with gr.Accordion(cfg["ui"]["title"], open=False):
        detail = gr.JSON(elem_id="assistant-context-detail")

    def collect(use, *values):
        selections: dict[str, Any] = {}
        for (key, field), item in bindings.items():
            selections.setdefault(key, {})[field] = values[inputs.index(item)]
        return page_context(use, selections)

    preview.click(
        safe(lambda *values: ((value := collect(*values)), summary(value))),
        inputs=[enabled, *inputs],
        outputs=[detail, badge],
        queue=False,
    )
    return enabled, inputs, collect, badge


class ContextTurns:
    """Reset page-scoped conversations while keeping original visible user messages."""

    def __init__(self, collect, chat, cli):
        self.collect, self.chat, self.cli = collect, chat, cli

    def send(self, session, message, history, backend, attachments, model, effort, access, enabled, scopes, *values):
        envelope = self.collect(enabled, *values)
        identity = context_identity(envelope)
        if scopes.get("chat") != identity:
            session, history = 0, []
        scopes["chat"] = identity
        token = TURN_PAGE_CONTEXT.set(envelope)
        try:
            for result in self.chat(session, message, history, backend, attachments, model, effort, access):
                yield result[0], result[1], result[2], result[3], result[4], summary(envelope)
        finally:
            TURN_PAGE_CONTEXT.reset(token)

    def cli_send(self, message, history, backend, enabled, scopes, *values, **options):
        envelope = self.collect(enabled, *values)
        identity = context_identity(envelope)
        if scopes.get("cli") != identity:
            history = []
        scopes["cli"] = identity
        token = TURN_PAGE_CONTEXT.set(envelope)
        try:
            yield from self.cli(message, history, backend, **options)
        finally:
            TURN_PAGE_CONTEXT.reset(token)

    def cli_send_with_options(self, message, history, backend, model, effort, access, enabled, scopes, *values):
        yield from self.cli_send(
            message,
            history,
            backend,
            enabled,
            scopes,
            *values,
            model_name=model,
            reasoning_effort=effort,
            access_mode=access,
        )
