"""Small structured editor instead of requiring users to hand-write a complete DAG."""

from html import escape

import yaml

import gradio as gr
from src.frontend.common.callbacks import safe
from src.strategy.composition.config import config


def flow(text):
    try:
        plan = yaml.safe_load(text) or {}
        nodes = plan.get("nodes") or []
        chips = "".join(
            "<div style='border:1px solid #8dadd155;border-radius:12px;padding:10px;min-width:120px'>"
            f"<strong>{escape(str(node.get('id', '')))}</strong><br>"
            f"{escape(str(node.get('component', '')))}<br><small>← {escape(', '.join(node.get('inputs') or ['universe']))}</small></div>"
            for node in nodes
        )
        return f"<div aria-label='方案依赖流程' style='display:flex;flex-wrap:wrap;gap:8px'>{chips}</div>"
    except (ValueError, TypeError, AttributeError, yaml.YAMLError):
        return ""


def render_editor(service, definition, version_id, graph_binding=None):
    cfg = config()
    with gr.Accordion("步骤、组合与风控编辑", open=False) as editor:
        gr.Markdown("编辑草稿后点击校验，再保存发布。父级依赖决定执行顺序；上移下移只调整独立阶段顺序。")
        diagram = gr.HTML(value=flow(definition.value))
        table = gr.Dataframe(headers=["阶段", "组件", "输入"], interactive=False)
        with gr.Row():
            selected = gr.Dropdown([("新增阶段", "")], value="", label="选择阶段", interactive=True)
            up = gr.Button("上移")
            down = gr.Button("下移")
        with gr.Row():
            node_id = gr.Textbox(label="阶段标识", interactive=True)
            component = gr.Dropdown(
                [(v["label"], key) for key, v in cfg["components"].items()],
                value="trend",
                label="组件",
                interactive=True,
            )
        parents = gr.Textbox(value="universe", label="输入阶段（逗号分隔）", interactive=True)
        parameters = gr.Textbox(value="{}", label="该阶段参数（JSON）", interactive=True)
        apply_node = gr.Button("添加或更新阶段")
        output = gr.Dropdown(["universe"], value="universe", label="最终输出阶段", interactive=True)
        name = gr.Textbox(label="方案名称", interactive=True)
        method = gr.Dropdown(
            [(v, k) for k, v in cfg["portfolios"].items()], value="equal", label="Portfolio分配方式", interactive=True
        )
        allocation = gr.Textbox(value="{}", label="Portfolio参数（JSON）", interactive=True)
        risk = gr.Textbox(value="{}", label="Risk参数（JSON；完整默认值见参数预览）", lines=3, interactive=True)
        apply_settings = gr.Button("更新名称、输出与Risk/Portfolio")
        with gr.Accordion("子策略资金组合", open=False):
            gr.Markdown("template 填预置方案标识；预算之和不超过1。应用后改为多策略总组合。")
            sleeves = gr.Dataframe(
                headers=["id", "template", "budget"], datatype=["str", "str", "number"], row_count=3, interactive=True
            )
            apply_sleeves = gr.Button("应用子策略预算")
    state_outputs = [table, selected, name, method, allocation, risk, sleeves, output]
    definition.change(flow, inputs=definition, outputs=diagram, queue=False)
    editor.expand(
        safe(service.pipeline_editor_state), inputs=[definition, selected], outputs=state_outputs, queue=False
    )
    definition.change(
        safe(service.pipeline_editor_state), inputs=[definition, selected], outputs=state_outputs, queue=False
    )
    definition.input(lambda: None, outputs=version_id, queue=False)
    selected.change(
        safe(service.pipeline_node_detail),
        inputs=[definition, selected],
        outputs=[node_id, component, parents, parameters],
        queue=False,
    )
    edits = [
        apply_node.click(
            safe(service.pipeline_edit_node),
            inputs=[definition, node_id, component, parents, parameters],
            outputs=definition,
            queue=False,
        ),
        up.click(safe(service.pipeline_move_up), inputs=[definition, selected], outputs=definition, queue=False),
        down.click(safe(service.pipeline_move_down), inputs=[definition, selected], outputs=definition, queue=False),
        apply_settings.click(
            safe(service.pipeline_edit_settings),
            inputs=[definition, name, method, allocation, risk, output],
            outputs=definition,
            queue=False,
        ),
        apply_sleeves.click(
            safe(service.pipeline_edit_sleeves), inputs=[definition, sleeves], outputs=definition, queue=False
        ),
    ]
    for event in edits:
        event.then(lambda: None, outputs=version_id, queue=False)
        if graph_binding:
            graph, pipeline_id, run_id = graph_binding
            event.then(
                service.pipeline_graph_sync, inputs=[definition, graph, pipeline_id, run_id], outputs=graph, queue=False
            )
