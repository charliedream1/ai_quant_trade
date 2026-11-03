"""Lazily rendered strategy workshop, using the shared domain execution path."""

import pandas as pd
import yaml

import gradio as gr
from src.frontend.common.callbacks import safe
from src.strategy.composition.config import config, templates

from .agent_strategy_controls import render_agent_controls
from .composition_editor import render_editor
from .composition_graph import render_graph
from .execution_costs import render_execution_controls


def render_composition(service):
    cfg = config()
    ui = cfg["ui"]
    first = next(row for row in templates() if row["id"] == cfg["defaults"]["default_template"])
    gr.Markdown(f"### {ui['title']}\n\n{ui['intro']}")
    with gr.Row():
        preset = gr.Dropdown(
            service.pipeline_templates(),
            value=first["id"],
            label=ui["template"],
            interactive=True,
            elem_id="pipeline-preset",
        )
        load = gr.Button(ui["load"])
    route_version = gr.Textbox(label="定位冻结版本", elem_id="pipeline-route-version", elem_classes=["route-control"])
    definition = gr.Textbox(
        value=yaml.safe_dump(first["definition"], allow_unicode=True, sort_keys=False),
        label=ui["definition"],
        lines=16,
        interactive=True,
        render=False,
    )
    pipeline_id = gr.Number(label=ui["pipeline_id"], precision=0, interactive=True, render=False)
    version_id = gr.Number(label=ui["version_id"], precision=0, interactive=True, render=False)
    run_id = gr.Textbox(label="运行ID", interactive=True, render=False)
    graph_control = render_graph(service, definition, version_id, pipeline_id, run_id, first["id"])
    graph_enabled = graph_control is not None
    if graph_control is None:
        graph_control = gr.State(None)
    execution_costs = render_execution_controls(service, definition=definition)
    agent_controls = render_agent_controls()
    with gr.Row():
        with gr.Column(scale=1, min_width=260):
            mode = gr.Dropdown([tuple(row) for row in ui["modes"]], value="screen", label=ui["mode"], interactive=True)
            symbols = gr.Textbox(label=ui["symbols"], interactive=True)
            backend = gr.Dropdown(
                [tuple(row) for row in ui["backends"]], value="api", label=ui["backend"], interactive=True
            )
            with gr.Accordion(ui["definition"], open=False):
                definition.render()
                variant = gr.Dropdown(
                    list(first["definition"]["variants"]), value="baseline", label="参数方案", interactive=True
                )
                overrides = gr.Textbox(value="{}", label=ui["overrides"], lines=3, interactive=True)
                preview = gr.Button(ui["validate"])
                resolved = gr.Textbox(label="生效预览（不训练、不调用模型）", lines=8, interactive=False)
                pipeline_id.render()
                version_id.render()
                publish = gr.Button(ui["publish"])
            with gr.Accordion("日期、模型与模拟账户", open=False):
                start = gr.Textbox(label=ui["start"], interactive=True)
                end = gr.Textbox(label=ui["end"], interactive=True)
                snapshot_id = gr.Textbox(label="行情快照ID（可选；重用已归档真实行情）", interactive=True)
                model_id = gr.Number(label=ui["model_id"], value=0, precision=0, interactive=True)
                model_name = gr.Textbox(label=ui["model_name"], interactive=True)
                effort = gr.Dropdown(
                    ["", "low", "medium", "high", "xhigh"], value="", label=ui["reasoning"], interactive=True
                )
                account_id = gr.Number(label=ui["account"], precision=0, interactive=True)
                refresh_decision = gr.Checkbox(label=ui["refresh_decision"], value=False, interactive=True)
                replay_ids = gr.Textbox(label="回放决定ID（逗号分隔；仅使用已保存的当时决定）", interactive=True)
                monitor = gr.Checkbox(label=ui["monitor"], value=False, interactive=True)
                enable = gr.Button("保存监控状态")
                reset = gr.Button(ui["risk_reset"])
            run = gr.Button(ui["run"], variant="primary")
            cancel = gr.Button(ui["cancel"])
            history = gr.Dropdown(label="历史运行", choices=[], interactive=True)
            refresh = gr.Button(ui["refresh"])
            open_history = gr.Button(ui["open"])
        with gr.Column(scale=3, min_width=400):
            status = gr.Textbox(label=ui["status"], value=ui["no_result"], interactive=False)
            run_id.render()
            with gr.Accordion(ui["events"], open=True):
                process = gr.Textbox(label=ui["events"], lines=8, max_lines=16, interactive=False)
            html = gr.HTML()
            report = gr.File(label=ui["report"], interactive=False, visible=False)
            with gr.Accordion("组件、参数及风险目录", open=False):
                gr.Dataframe(value=pd.DataFrame(service.pipeline_components()), interactive=False)
    render_editor(service, definition, version_id, (graph_control, pipeline_id, run_id) if graph_enabled else None)
    preset.change(
        lambda selected: gr.update(open=str(selected or "").startswith("agent_")),
        inputs=preset,
        outputs=agent_controls.panel,
        queue=False,
    )
    outputs = [status, process, html, report, run_id, account_id, version_id]
    if graph_enabled:

        def _open_version(key, graph):
            selected = "version:" + str(int(key))
            return (
                gr.update(choices=service.pipeline_templates(), value=selected),
                *service.pipeline_graph_load(selected, graph),
            )

        route_version.change(
            safe(_open_version),
            inputs=[route_version, graph_control],
            outputs=[preset, definition, variant, pipeline_id, version_id, status, graph_control],
            queue=False,
        )
    load.click(
        safe(service.pipeline_graph_load if graph_enabled else service.pipeline_load),
        inputs=[preset, graph_control] if graph_enabled else preset,
        outputs=[definition, variant, pipeline_id, version_id, status, graph_control]
        if graph_enabled
        else [definition, variant, pipeline_id, version_id, status],
        queue=False,
    )
    preview.click(
        safe(service.pipeline_preview), inputs=[definition, overrides, variant], outputs=resolved, queue=False
    )
    publish.click(
        safe(service.pipeline_publish),
        inputs=[definition, overrides, variant, pipeline_id],
        outputs=[status, pipeline_id, version_id],
    )

    def _pipeline_run(*values):
        yield from service.pipeline_run(
            *values[:17],
            **agent_controls.parse(values[17:23]),
            execution_costs=execution_costs.parse(values[23:]),
        )

    run.click(
        safe(_pipeline_run),
        inputs=[
            definition,
            overrides,
            variant,
            version_id,
            symbols,
            mode,
            backend,
            model_id,
            model_name,
            effort,
            start,
            end,
            account_id,
            refresh_decision,
            replay_ids,
            snapshot_id,
            graph_control,
            *agent_controls.inputs,
            *execution_costs.inputs,
        ],
        outputs=outputs,
        concurrency_id="composition-runs",
        concurrency_limit=2,
    )
    cancel.click(safe(service.pipeline_cancel), inputs=run_id, outputs=status, queue=False)
    refresh.click(safe(service.pipeline_history), outputs=history, queue=False)
    open_history.click(safe(service.pipeline_open), inputs=history, outputs=outputs)
    enable.click(safe(service.pipeline_account_monitor), inputs=[account_id, monitor], outputs=status)
    reset.click(safe(service.pipeline_account_reset), inputs=account_id, outputs=status)
