"""One analysis workspace for backtest, paper and live evidence, preserving source IDs."""

import gradio as gr

from ..common.callbacks import safe
from ..common.components import table
from ..common.navigation import navigation_config
from ..service.foundation import QUANT_WORKFLOW_MODE_CHOICES, QUANT_WORKFLOW_SOP_CHOICES


def render_analysis(service):
    gr.Markdown("### 运行归因与闭环分析\n\n选择来源与实际ID；回测、模拟账户和实盘运行保留独立证据口径。")
    cfg = navigation_config()
    route_mode = gr.Textbox(elem_id="route-analysis-mode", elem_classes=["route-control"])
    with gr.Row():
        mode = gr.Radio(QUANT_WORKFLOW_MODE_CHOICES, value="simulation", label="分析来源")
        sop = gr.Dropdown(QUANT_WORKFLOW_SOP_CHOICES, value=cfg["analysis_sops"]["simulation"], label="SOP")
    with gr.Row():
        strategy = gr.Number(label="策略 ID", precision=0, elem_id="route-analysis-strategy-id")
        backtest = gr.Number(label="回测 ID", precision=0, elem_id="route-analysis-backtest-id")
        account = gr.Number(label="模拟账户 ID", precision=0, elem_id="route-analysis-account-id")
        live = gr.Number(label="实盘运行 ID", precision=0, elem_id="route-analysis-live-run-id")
    with gr.Row():
        title = gr.Textbox(label="运行标题")
        refresh = gr.Button("生成分析快照", variant="primary")
        save = gr.Button("保存分析运行")
        history_refresh = gr.Button("刷新分析历史")
    summary = gr.Markdown(elem_classes=["status-strip"])
    board = gr.HTML(elem_id="quant-workflow-board")
    with gr.Tabs():
        with gr.Tab("流程步骤"):
            steps = table("流程步骤", 300)
        with gr.Tab("归因洞察"):
            insights = table("归因洞察", 320)
        with gr.Tab("问数清单"):
            questions = table("问数清单", 280)
        with gr.Tab("迭代建议"):
            advice = table("迭代建议", 320)
        with gr.Tab("产物与历史"):
            artifacts = table("证据产物", 260)
            saved = gr.Code(language="json", label="保存结果")
            history = table("分析运行历史", 260)
    inputs = [mode, sop, strategy, backtest, account, live]
    refresh.click(
        safe(service.quant_workflow_snapshot),
        inputs=inputs,
        outputs=[summary, board, steps, insights, questions, advice, artifacts],
    )
    save.click(
        safe(service.quant_workflow_create_run),
        inputs=[mode, sop, title, strategy, backtest, account, live],
        outputs=[saved, history],
    )
    history_refresh.click(safe(service.quant_workflow_runs), inputs=mode, outputs=history, queue=False)
    mode.change(lambda value: cfg["analysis_sops"][value], inputs=mode, outputs=sop, queue=False)
    route_mode.change(
        lambda value: gr.update(value=value) if value in cfg["analysis_sops"] else gr.skip(),
        inputs=route_mode,
        outputs=mode,
        queue=False,
    )
