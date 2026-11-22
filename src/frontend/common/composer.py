"""One compact, accessible composer shared by workbench and floating assistant."""

from collections.abc import Callable
from dataclasses import dataclass

import gradio as gr

from src.agent.cli_catalog import catalog_config
from src.agent.composer_config import cli_choices, composer_config

from .callbacks import safe
from .composer_catalog import CatalogSelection


@dataclass
class Composer:
    text: gr.Textbox
    attachments: gr.File
    backend: gr.Dropdown
    permission: gr.Dropdown
    model: gr.Dropdown
    reasoning: gr.Dropdown
    send: gr.Button


def render_composer(
    prefix: str,
    models: list[tuple[str, str]],
    model_loader: Callable | None = None,
    *,
    default_backend="generic_agent",
    task_controls=False,
    cli_only=False,
    load_event=None,
) -> Composer:
    cfg = composer_config()
    with gr.Column(elem_id=f"{prefix}-composer", elem_classes=["flat-ai-composer"]):
        text = gr.Textbox(
            visible=not task_controls,
            label="输入任务",
            placeholder=cfg["ui"]["placeholder"],
            lines=2,
            max_lines=3,
            elem_id=f"{prefix}-input",
            interactive=True,
        )
        # File preview remains a full-width strip instead of squeezed inside the icon.
        attachments = gr.File(
            visible=not task_controls and not cli_only,
            label="添加附件或拖入文件/图片",
            file_count="multiple",
            type="filepath",
            height=60,
            elem_id=f"{prefix}-attachments",
            elem_classes=["composer-upload"],
        )
        with gr.Row(elem_classes=["composer-attachment-row"], visible=not task_controls and not cli_only):
            gr.HTML(
                "<button type='button' class='composer-attach' aria-label='添加附件' title='添加附件；也可拖入文件或图片'>＋</button>",
                elem_classes=["composer-attach-slot"],
            )
        with gr.Row(elem_id=f"{prefix}-composer-footer", elem_classes=["composer-toolbar"]):
            with gr.Row(elem_classes=["composer-backend-options"]):
                backend = gr.Dropdown(
                    cli_choices(api=None if cli_only or task_controls else "generic_agent"),
                    value=default_backend,
                    label="后台",
                    min_width=95,
                    scale=1,
                    elem_id=f"{prefix}-backend",
                    interactive=True,
                )
                permission = gr.Dropdown(
                    [(label, key) for key, label in cfg["permissions"].items()],
                    visible=not task_controls,
                    value="read-only",
                    label="访问权限",
                    min_width=75,
                    scale=1,
                    elem_id=f"{prefix}-permission",
                    interactive=False,
                )
            with gr.Row(elem_classes=["composer-options"]):
                with gr.Column(elem_classes=["composer-model-slot"], min_width=0, scale=1):
                    model = gr.Dropdown(
                        [
                            (name + " · " + catalog_config()["labels"]["unknown"], identifier)
                            for name, identifier in models
                        ]
                        or [(catalog_config()["labels"]["default"], "")],
                        value=(models[0][1] if models else None) if prefix == "ai-chat" else "",
                        label="模型",
                        min_width=0,
                        scale=1,
                        elem_id=f"{prefix}-model",
                        elem_classes=["no-i18n"],
                        interactive=True,
                    )
                    refresh = gr.Button(
                        "↻",
                        min_width=22,
                        scale=0,
                        elem_classes=["composer-refresh"],
                        elem_id=f"{prefix}-refresh-models",
                    )
                reasoning = gr.Dropdown(
                    [tuple(row) for row in cfg["efforts"]],
                    value="",
                    label="思考强度",
                    min_width=80,
                    scale=1,
                    elem_id=f"{prefix}-reasoning",
                    interactive=True,
                )
            send = gr.Button(
                "发送",
                visible=not task_controls,
                variant="primary",
                min_width=38,
                scale=0,
                elem_id=f"{prefix}-send",
                elem_classes=["composer-send"],
            )
        note = gr.Markdown(
            catalog_config()["messages"]["initial"]
            if default_backend == "generic_agent"
            else cfg["backends"][default_backend]["label"] + " · " + catalog_config()["labels"]["unknown"],
            elem_id=f"{prefix}-billing",
            elem_classes=["composer-backend-note", "no-i18n"],
        )
        state = gr.State({"backend": default_backend, "revision": 0, "catalog": {}})

    selection = CatalogSelection(models, model_loader)
    backend.input(
        safe(selection.begin),
        inputs=[backend, state],
        outputs=[state, model, reasoning, permission, note, send],
        queue=False,
        trigger_mode="multiple",
    ).then(
        safe(selection.load),
        inputs=state,
        outputs=[model, reasoning, permission, note, send],
        queue=False,
        trigger_mode="multiple",
    )
    refresh.click(
        safe(selection.refresh),
        inputs=state,
        outputs=[model, reasoning, permission, note, send],
        queue=False,
        trigger_mode="multiple",
    )
    model.input(safe(selection.select), inputs=[model, backend, state], outputs=[note, reasoning], queue=False)
    if load_event is not None:

        def initialize(current):
            return selection.load(current) if not current["catalog"] else (gr.skip(),) * 5

        load_event(safe(initialize), inputs=state, outputs=[model, reasoning, permission, note, send], queue=False)
    return Composer(text, attachments, backend, permission, model, reasoning, send)
