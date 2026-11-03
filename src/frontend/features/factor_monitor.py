"""One lazily mounted monitor for market research and strategy construction."""

from __future__ import annotations

from typing import Any

import gradio as gr

from ..common.callbacks import safe
from ..common.components import plot, table
from ..handlers.base import DomainHandler


def render_factor_monitor(service: DomainHandler, strategy: bool = False) -> None:
    with gr.Column(elem_id="ai-factor-mining" if strategy else "factor-monitor"):
        settings = service.factor_ui_settings()
        controls, start = _controls(service, settings)
        outputs = _outputs()
        job_id, rendered = gr.State(""), gr.State("")
        events = gr.Markdown("选择股票池后运行；切页不会自动拉取全市场行情。", label="实际过程")
        timer = gr.Timer(settings["ui_poll_seconds"], active=False)
        _bind(service, controls, start, outputs, events, timer, job_id, rendered, settings)


def _controls(service: DomainHandler, settings: dict[str, Any]) -> tuple[list[Any], gr.Button]:
    choices = service.factor_universe_options()
    with gr.Row():
        scope = gr.Dropdown(choices, value=settings["default_universe_id"], label="监控范围")
        backend = gr.Dropdown(
            [("内置因子研究", "builtin"), ("Qlib信号分析", "qlib")], value="builtin", label="分析后端"
        )
        run = gr.Button("运行因子监控", variant="primary")
    text = gr.Textbox(
        label="自定义股票代码（仅自定义范围使用）", placeholder="逗号分隔标准代码；不再限制为默认几只股票"
    )
    with gr.Accordion("股票池版本、对照与缓存", open=False):
        with gr.Row():
            resource = gr.Number(label="资源池ID / 模拟账户ID", precision=0)
            as_of = gr.Textbox(label="观察日期", placeholder="YYYY-MM-DD，留空使用今天")
        version = gr.Textbox(
            label="历史成员清单版本（可选）", info="可通过API导入有效日期清单；未提供时明确标注当前成分回看"
        )
        compare = gr.Dropdown(choices, value=[], multiselect=True, label="对照股票池")
        refresh = gr.Checkbox(value=False, label="跳过结果缓存重新计算")
    return [text, scope, resource, backend, as_of, version, refresh, compare], run


def _outputs() -> list[Any]:
    status = gr.Markdown(elem_classes=["status-strip"])
    kpis = gr.HTML()
    with gr.Row():
        ic = plot(label="RankIC", elem_classes=["chart-panel"])
        quantile = plot(label="分位收益", elem_classes=["chart-panel"])
    diagnostic = plot(label="因子诊断", elem_classes=["chart-panel"])
    with gr.Row():
        history = plot(label="分层收益时序", elem_classes=["chart-panel"])
        exposure = plot(label="风格暴露", elem_classes=["chart-panel"])
    with gr.Accordion("有效性、覆盖与原始截面", open=False):
        metrics = table("因子有效性指标")
        alerts = table("因子告警")
        snapshots = table("最新因子截面")
        correlation = plot(label="因子相关性", elem_classes=["chart-panel"])
        environment = gr.Markdown()
        coverage = table("请求、加载与失败明细")
    with gr.Accordion("滚动稳定性与多池对照", open=False):
        rolling = table("滚动RankIC与未年化ICIR")
        stability = table("预先固定的时间分段")
        comparison = table("股票池对照")
    return [
        status,
        kpis,
        ic,
        quantile,
        diagnostic,
        history,
        exposure,
        metrics,
        alerts,
        snapshots,
        correlation,
        environment,
        coverage,
        rolling,
        stability,
        comparison,
    ]


def _bind(service, controls, start, outputs, events, timer, job_id, rendered, settings):
    def submit(text, scope, resource, backend, as_of, version, refresh, compare, request: gr.Request):
        identifier = service.factor_start_job(
            text, scope, resource, backend, as_of, version, refresh, compare, request.session_hash
        )
        return identifier, "任务已提交，正在等待后台执行。", "", "", gr.update(active=True)

    def poll(identifier: str, previous: str, request: gr.Request):
        skipped = tuple(gr.skip() for _ in range(len(outputs) + 3))
        if not identifier or identifier == previous:
            return skipped
        job = service.factor_job(identifier, request.session_hash)
        if job["status"] == "stale":
            return skipped
        process = "\n\n".join(
            f"{row['time']} · {row['message']}" for row in job["events"][-settings["ui_event_lines"] :]
        )
        if job["status"] != "completed":
            status = job["stage"] + ("：" + job["error"] if job["error"] else "")
            return (
                status,
                *(gr.skip() for _ in outputs[1:]),
                process,
                identifier if job["status"] == "failed" else gr.skip(),
                gr.update(active=False) if job["status"] == "failed" else gr.skip(),
            )
        values = service.factor_result_values(job["result"])
        if service.factor_job(identifier, request.session_hash)["status"] == "stale":
            return skipped
        return (*values, process, identifier, gr.update(active=False))

    start.click(safe(submit), inputs=controls, outputs=[job_id, outputs[0], events, rendered, timer], queue=False)
    timer.tick(safe(poll), inputs=[job_id, rendered], outputs=[*outputs, events, rendered, timer], queue=False)
