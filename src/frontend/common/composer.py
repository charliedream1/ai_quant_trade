"""One compact, accessible composer shared by workbench and floating assistant."""

from collections.abc import Callable
from dataclasses import dataclass

import gradio as gr
from src.agent.composer_config import composer_config, normalize_backend
from src.agent.qoder_cli import model_choices as qoder_models


@dataclass
class Composer:
    text: gr.Textbox
    attachments: gr.File
    backend: gr.Dropdown
    permission: gr.Dropdown
    model: gr.Dropdown
    reasoning: gr.Dropdown
    send: gr.Button


def render_composer(prefix: str, models: list[tuple[str, str]], model_loader: Callable | None = None) -> Composer:
    cfg = composer_config()
    with gr.Column(elem_id=f"{prefix}-composer", elem_classes=["flat-ai-composer"]):
        text = gr.Textbox(
            label="输入任务",
            placeholder=cfg["ui"]["placeholder"],
            lines=2,
            max_lines=3,
            elem_id=f"{prefix}-input",
            interactive=True,
        )
        # File preview remains a full-width strip instead of squeezed inside the icon.
        attachments = gr.File(
            label="添加附件或拖入文件/图片",
            file_count="multiple",
            type="filepath",
            height=60,
            elem_id=f"{prefix}-attachments",
            elem_classes=["composer-upload"],
        )
        with gr.Row(elem_classes=["composer-attachment-row"]):
            gr.HTML(
                "<button type='button' class='composer-attach' aria-label='添加附件' title='添加附件；也可拖入文件或图片'>＋</button>",
                elem_classes=["composer-attach-slot"],
            )
        with gr.Row(elem_id=f"{prefix}-composer-footer", elem_classes=["composer-toolbar"]):
            with gr.Row(elem_classes=["composer-backend-options"]):
                backend = gr.Dropdown(
                    [(profile["label"], key) for key, profile in cfg["backends"].items()],
                    value="generic_agent",
                    label="后台",
                    min_width=95,
                    scale=1,
                    elem_id=f"{prefix}-backend",
                    interactive=True,
                )
                permission = gr.Dropdown(
                    [(label, key) for key, label in cfg["permissions"].items()],
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
                        models,
                        value="",
                        label="模型",
                        min_width=0,
                        scale=1,
                        elem_id=f"{prefix}-model",
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
                variant="primary",
                min_width=38,
                scale=0,
                elem_id=f"{prefix}-send",
                elem_classes=["composer-send"],
            )
        note = gr.Markdown(visible=False, elem_classes=["composer-backend-note"])

    def select_backend(selected, refresh_models=False):
        selected = normalize_backend(selected)
        profile = cfg["backends"][selected]
        choices, hint = (
            model_loader() if refresh_models and selected == "generic_agent" and model_loader else models,
            "",
        )
        if selected == "qoder":
            choices, hint = qoder_models(refresh=refresh_models)
        elif selected != "generic_agent":
            choices = [("默认模型", "")]
        return (
            gr.update(choices=choices, value="", allow_custom_value=selected in {"codex", "qoder", "codebuddy"}),
            gr.update(value="", interactive=len(profile["efforts"]) > 1),
            gr.update(value="read-only", interactive=len(profile["permissions"]) > 1),
            gr.update(value=hint, visible=bool(hint)),
        )

    backend.change(
        lambda: (gr.update(value=""), gr.update(value=""), gr.update(value="read-only")),
        outputs=[model, reasoning, permission],
        queue=False,
    ).then(select_backend, inputs=backend, outputs=[model, reasoning, permission, note], queue=False)
    refresh.click(
        lambda selected: select_backend(selected, True),
        inputs=backend,
        outputs=[model, reasoning, permission, note],
        queue=False,
    )
    return Composer(text, attachments, backend, permission, model, reasoning, send)
