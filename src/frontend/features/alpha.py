"""One compact Gradio view, with linked research stages instead of deeper tabs."""

import gradio as gr
from src.alpha_mining.config import config
from src.core.timeutil import utc_now_iso
from src.engine.execution.config import cost_config

from ..common.callbacks import safe
from ..common.navigation import workspace_link
from ..common.provider_controls import provider_controls


def render_alpha(service, tab):
    cfg = config()
    loaded = gr.State(False)
    gr.Markdown("### Alpha研究\n\n" + cfg["ui"]["disclaimer"])
    gr.HTML(workspace_link("查看图形策略工坊中的研究组件", "strategy", "workshop"))
    with gr.Row():
        selected = gr.Dropdown([], label="研究项目", elem_id="alpha-study", interactive=True, scale=3)
        refresh = gr.Button("刷新研究目录", scale=1)
    status = gr.Markdown(elem_classes=["status-strip"], elem_id="alpha-status")
    with gr.Accordion("数据与来源（先导入或选择已核验归档）", open=False):
        gr.Markdown(
            cfg["ui"]["source_explanation"]
            + "\n\n[行情模板](/api/v1/alpha/templates/market) · [主题资料模板](/api/v1/alpha/templates/documents) · [宏观PIT模板](/api/v1/alpha/templates/macro)"
        )
        with gr.Row():
            dataset = gr.Dropdown([], label="研究数据", interactive=True, elem_id="alpha-dataset")
            data_kind = gr.Dropdown(["market", "documents", "macro"], value="market", label="导入类型")
        upload = gr.File(label="导入数据文件", file_types=[".csv", ".json", ".yaml", ".yml"], elem_id="alpha-upload")
        import_data = gr.Button("校验并导入数据")
        with gr.Row():
            snapshot_id = gr.Textbox(label="现有组合行情归档SHA256（可选）")
            import_snapshot = gr.Button("读取服务器归档")
    with gr.Accordion("新建研究与统一政策", open=True):
        with gr.Row():
            name = gr.Textbox(label="研究名称", elem_id="alpha-name")
            mode = gr.Dropdown(cfg["ui"]["modes"], value="alpha", label="研究流程", elem_id="alpha-mode")
            model = gr.Dropdown([], label="已配置的真实模型", interactive=True, elem_id="alpha-model")
        purpose = gr.Textbox(label="研究目标 / 主题", value=cfg["study_defaults"]["purpose"], lines=2)
        backend, model_name = provider_controls("alpha")
        with gr.Row():
            reasoning = gr.Dropdown(["", "low", "medium", "high", "xhigh"], value="", label="模型支持的思考强度")
            batch = gr.Number(value=cfg["study_defaults"]["batch_size"], precision=0, label="预登记候选槽位")
            budget = gr.Number(value=cfg["study_defaults"]["model_call_budget"], precision=0, label="实际调用预算")
        with gr.Row():
            cutoff = gr.Textbox(value=utc_now_iso(), label="主题/体制截止时点（含时区）")
            costs = gr.Dropdown(
                [(value["description"], key) for key, value in cost_config()["profiles"].items()],
                value="inherit",
                label="统一执行费用方案",
            )
        with gr.Accordion("高级配置：政策、模型分工、八配置及资产映射", open=False):
            gr.Markdown(
                "填写YAML对象覆盖设置。体制流程需asset_mapping；configurations可指定1至8个不同模型/思考配置。market_dataset_id关联回测行情。policy和execution_costs分别控制研究门槛及滑点/佣金/税费，创建后冻结。"
            )
            advanced = gr.Code(value="{}", language="yaml", label="研究配置覆盖", elem_id="alpha-advanced", lines=8)
        create = gr.Button("登记新研究并冻结配置", variant="primary", elem_id="alpha-create")
    with gr.Row():
        run = gr.Button("发现假设 / 执行流程", variant="primary", elem_id="alpha-run")
        seal = gr.Button("冻结候选家族", elem_id="alpha-seal")
        validate = gr.Button("运行冻结验证", elem_id="alpha-validate")
        holdout = gr.Button("一次性最终留出", elem_id="alpha-holdout")
        cancel = gr.Button("取消研究", elem_id="alpha-cancel")
    with gr.Row():
        candidate = gr.Dropdown([], label="候选及实现关联", interactive=True, elem_id="alpha-candidate")
        stage = gr.Radio(cfg["ui"]["stages"], value="假设", label="研究步骤", elem_id="alpha-stage")
    inspection = gr.JSON(label="当前步骤的实际证据", elem_id="alpha-inspection")
    with gr.Accordion("Python产物（只读审阅）", open=False):
        source = gr.Code(language="python", interactive=False, label="生成的受控Python", lines=12)
    process = gr.Textbox(
        label="真实角色输出、工具观察及阶段事件", lines=10, max_lines=18, interactive=False, elem_id="alpha-process"
    )
    report = gr.HTML(elem_id="alpha-report")
    with gr.Accordion("人工假设（使用相同门槛）", open=False):
        hypothesis = gr.Code(value="{}", language="yaml", label="预登记假设", lines=5)
        implementation = gr.Code(value="{}", language="yaml", label="受控因子实现", lines=5)
        add = gr.Button("登记人工候选")
    with gr.Accordion("来源核验与双轨人工复核", open=False):
        gr.Markdown(
            "来源核验会创建新数据版本，须在登记研究前完成。经济轨和技术轨分别留痕；本地确认不等于独立双人认证，不能覆盖硬失败。"
        )
        reviewer = gr.Textbox(label="实际复核者")
        evidence = gr.Code(
            value="{}", language="yaml", label="复核证据（reason；来源核验另需source_reference）", lines=4
        )
        attest = gr.Button("核验当前资料来源，创建新数据版本")
        with gr.Row():
            track = gr.Dropdown(
                [("经济逻辑", "economic"), ("技术与测试", "technical")], value="economic", label="复核轨道"
            )
            decision = gr.Dropdown([("通过", "approve"), ("拒绝", "reject")], value="approve", label="人工意见")
            review = gr.Button("记录复核意见", elem_id="alpha-review")
        with gr.Row():
            configuration = gr.Number(value=1, precision=0, label="导出的体制配置序号")
            export = gr.Button("导出图形工坊草稿", elem_id="alpha-export")
    with gr.Row():
        artifact = gr.Dropdown([], label="已生成的研究产物", interactive=True)
        open_artifact = gr.Button("在侧边阅读产物")
    artifact_reader = gr.HTML(elem_id="alpha-file-reader")
    timer = gr.Timer(cfg["limits"]["poll_seconds"], active=False)
    outputs = [status, candidate, process, inspection, source, report, artifact, timer]
    poll_inputs = [selected, stage, candidate]
    for button, action in (
        (run, "start"),
        (seal, "seal"),
        (validate, "validate"),
        (holdout, "holdout"),
        (cancel, "cancel"),
    ):
        button.click(
            safe(lambda study, choice, step, op=action: service.alpha_operate(study, op, choice, step)),
            inputs=[selected, candidate, stage],
            outputs=outputs,
        )
    selected.change(safe(service.alpha_poll), inputs=poll_inputs, outputs=outputs, queue=False)
    stage.change(safe(service.alpha_poll), inputs=poll_inputs, outputs=outputs, queue=False)
    candidate.input(safe(service.alpha_poll), inputs=poll_inputs, outputs=outputs, queue=False)
    timer.tick(safe(service.alpha_poll), inputs=poll_inputs, outputs=outputs, queue=False)
    create.click(
        safe(service.alpha_create),
        inputs=[
            name,
            mode,
            dataset,
            model,
            reasoning,
            budget,
            batch,
            purpose,
            cutoff,
            costs,
            advanced,
            backend,
            model_name,
        ],
        outputs=[selected, status],
    )
    import_data.click(safe(service.alpha_import), inputs=[data_kind, upload], outputs=[dataset, status])
    import_snapshot.click(safe(service.alpha_snapshot), inputs=snapshot_id, outputs=[dataset, status])
    attest.click(safe(service.alpha_attest), inputs=[dataset, reviewer, evidence], outputs=[dataset, status])
    review.click(
        safe(service.alpha_review),
        inputs=[selected, candidate, track, decision, reviewer, evidence, stage],
        outputs=outputs,
    )
    export.click(safe(service.alpha_export), inputs=[selected, candidate, configuration], outputs=status)
    add.click(safe(service.alpha_add), inputs=[selected, hypothesis, implementation, stage], outputs=outputs)
    open_artifact.click(safe(service.alpha_open_artifact), inputs=[selected, artifact], outputs=artifact_reader)
    refresh.click(safe(service.alpha_catalog), inputs=selected, outputs=[selected, dataset, model], queue=False)

    def first_visit(done):
        return (gr.skip(), gr.skip(), gr.skip(), True) if done else (*service.alpha_catalog(), True)

    tab.select(safe(first_visit), inputs=loaded, outputs=[selected, dataset, model, loaded], queue=False)
