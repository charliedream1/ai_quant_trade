"""Batch research import controls shared by report and paper search."""

from collections import Counter

import gradio as gr

from src.core.repository import Repository
from src.knowledge.config import knowledge_config
from src.knowledge.files import KnowledgeFiles
from src.knowledge.research_batches import ResearchBatches
from src.knowledge.research_classification import policy
from src.knowledge.research_onnx import install, model_directory

from ..common.callbacks import safe

STATUS = {
    "queued": "排队中",
    "running": "处理中",
    "waiting": "队列已满，请重试",
    "interrupted": "已中断，可重试",
    "completed": "处理完成",
    "cancelled": "已取消",
    "pending": "待处理",
    "starting": "准备中",
    "downloading": "下载全文",
    "parsing": "解析全文",
    "classifying": "分类中",
    "saving": "保存中",
    "imported": "已入库",
    "review": "待审核",
    "failed": "失败",
    "duplicate": "已存在",
}


def render_research_batch(kind, filters):
    cfg = policy()
    prefix = f"research-batch-{kind}"
    with gr.Accordion("批量分类入库", open=False, elem_id=prefix):
        prepared = gr.State("")
        running = gr.State("")
        with gr.Row():
            prepare = gr.Button("准备检索范围", elem_id=f"{prefix}-prepare")
            window = gr.Number(label="来源批次（从 1 开始）", value=1, minimum=1, precision=0)
            target = gr.Dropdown(
                KnowledgeFiles().libraries(),
                value=knowledge_config()["default_library"],
                allow_custom_value=True,
                label="目标知识库",
            )
        scope = gr.Markdown()
        with gr.Row():
            selection = gr.Dropdown([], multiselect=True, label="选择待入库资料", elem_id=f"{prefix}-selection")
            full = gr.Checkbox(label="导入本批全部结果", elem_id=f"{prefix}-all")
        with gr.Row():
            mode = gr.Dropdown(
                [("传统 TF-IDF", "traditional"), ("本地零样本", "zero_shot"), ("大模型", "llm")],
                value=cfg["default_classifier"],
                label="分类方式",
            )
            models = gr.Dropdown(
                [
                    (row["model_name"], row["id"])
                    for row in Repository().db.query("SELECT id,model_name FROM llm_models WHERE enabled=1 ORDER BY id")
                ],
                label="大模型分类配置",
                interactive=True,
            )
        gr.Markdown("选择大模型后，所选服务会收到标题、摘要和限长正文。")
        with gr.Accordion("本地模型安装", open=False):
            size = sum(item[0] for item in cfg["model"]["files"].values()) / 1_000_000
            gr.Markdown(f"模型文件约 {size:.0f} MB。安装位置可通过 {cfg['model']['directory_env']} 配置。")
            gr.Textbox(label="本地模型目录", value=lambda: str(model_directory()), interactive=False)
            confirmed = gr.Checkbox(label="确认下载固定版本的本地分类模型")
            download = gr.Button("下载分类模型")
            installation = gr.Markdown()
            download.click(safe(install), inputs=confirmed, outputs=installation)
        with gr.Row():
            start = gr.Button("开始批量入库", variant="primary", elem_id=f"{prefix}-start")
            cancel = gr.Button("取消批次")
            retry = gr.Button("重试未完成项")
        with gr.Row():
            history = gr.Dropdown([], label="历史入库任务", interactive=True)
            refresh = gr.Button("刷新任务列表")
        status = gr.Markdown(elem_id=f"{prefix}-status")
        details = gr.Dataframe(headers=["标题", "状态", "文档 ID", "说明"], interactive=False)
        timer = gr.Timer(cfg["limits"]["poll_seconds"], active=False)

    def prepare_batch(*values):
        key, coverage, choices = ResearchBatches().prepare(kind, values)
        message = f"已固定本次筛选范围，共 {len(choices)} 条 · {coverage['market']}"
        if not coverage["complete"]:
            message += f" · 来源覆盖有限（{coverage['reason']}）"
            if coverage["reason"] in {"page_limit", "result_limit"}:
                message += f" · 后续结果请准备来源批次 {coverage['window'] + 1}"
        return key, gr.update(choices=choices, value=[]), False, message

    def start_batch(key, selected, all_results, library, method, model, *values):
        if not key:
            raise ValueError("请先准备检索范围")
        ResearchBatches().start(key, selected, all_results, library, method, model, expected_filters=values)
        return key, *read_batch(key)

    def read_batch(key):
        if not key:
            return "", [], gr.update(active=False)
        state, rows = ResearchBatches().status(key)
        counts = Counter(row[1] for row in rows)
        summary = f"**{STATUS.get(state, state)}** · {len(rows)} 条"
        summary += "".join(f" · {STATUS.get(code, code)} {count}" for code, count in counts.items())
        return (
            summary,
            [[title, STATUS.get(item, item), doc_id, detail] for title, item, doc_id, detail in rows],
            gr.update(active=state in {"queued", "running"}),
        )

    def control(key, action):
        if not key:
            raise ValueError("请选择任务")
        getattr(ResearchBatches(), action)(key)
        return read_batch(key)

    search_scope = [*filters, window]
    prepare.click(safe(prepare_batch), inputs=search_scope, outputs=[prepared, selection, full, scope])
    for field in search_scope:
        field.input(
            lambda: ("", gr.update(choices=[], value=[]), False, ""),
            outputs=[prepared, selection, full, scope],
            queue=False,
        )
    result = [status, details, timer]
    start.click(safe(start_batch), [prepared, selection, full, target, mode, models, *search_scope], [running, *result])
    timer.tick(safe(read_batch), running, result, queue=False)
    cancel.click(safe(lambda key: control(key, "cancel")), running, result, queue=False)
    retry.click(safe(lambda key: control(key, "retry")), running, result, queue=False)
    refresh.click(safe(lambda: gr.update(choices=ResearchBatches().history(kind))), outputs=history)
    history.input(safe(lambda key: (key, *read_batch(key))), history, [running, *result])
