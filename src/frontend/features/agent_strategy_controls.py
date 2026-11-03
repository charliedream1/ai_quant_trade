"""Optional Agent research controls, isolated from the workshop rendering function."""

from dataclasses import dataclass

import yaml

import gradio as gr
from src.agent_strategies.config import settings
from src.frontend.common.navigation import workspace_link


@dataclass
class AgentControls:
    panel: gr.Accordion
    inputs: list

    def parse(self, values) -> dict:
        documents, depth, predictor, calls, mode, roles = values
        return {
            "agent_documents_dataset_id": documents,
            "agent_strategy_options": {
                "depth": depth,
                "predictor": predictor,
                "calls": int(calls),
                "role_models": yaml.safe_load(roles) or {},
            },
            "agent_mode": mode or None,
        }


def render_agent_controls() -> AgentControls:
    cfg = settings()
    with gr.Accordion("Agent策略设置（中文多空 / 双团队竞赛）", open=False) as panel:
        gr.Markdown(
            "在上方方案库选择 Agent方案；资料可在Alpha研究导入。缺少必需证据时仅研究、不配置资金。默认回测关闭Agent；历史生成需显式选择并承担模型训练记忆风险。"
        )
        gr.HTML(workspace_link("导入行情/PIT资料或下载模板", "strategy", "alpha"))
        with gr.Row():
            documents = gr.Number(
                label="PIT资料数据集ID（可选）",
                precision=0,
                value=0,
                elem_id="agent-strategy-documents",
                interactive=True,
            )
            depth = gr.Dropdown(
                list(cfg["depths"]),
                value=cfg["defaults"]["depth"],
                label="研究深度",
                elem_id="agent-strategy-depth",
                interactive=True,
            )
            predictor = gr.Dropdown(
                ["baseline", "lightgbm"],
                value=cfg["defaults"]["predictor"],
                label="成熟成绩效用预测器",
                elem_id="agent-strategy-predictor",
                interactive=True,
            )
            calls = gr.Number(
                value=cfg["defaults"]["calls"],
                precision=0,
                label="整轮实际模型请求上限",
                elem_id="agent-strategy-calls",
                interactive=True,
            )
        mode = gr.Dropdown(
            [
                ("自动（历史回测为纯量化对照）", ""),
                ("当前研究", "live"),
                ("历史模型研究（非当时决定回放）", "research"),
                ("当时决定回放", "replay"),
            ],
            value="",
            label="Agent执行模式",
            elem_id="agent-strategy-mode",
            interactive=True,
        )
        with gr.Accordion("按角色指定模型（可选）", open=False):
            roles = gr.Textbox(
                value="{}",
                lines=3,
                label="角色模型 YAML（空对象沿用下方统一后端/模型）",
                info="键为角色名，值可填 model_id、backend、model_name、reasoning_effort；详细示例见使用文档。",
                elem_id="agent-strategy-role-models",
                interactive=True,
            )
    return AgentControls(panel, [documents, depth, predictor, calls, mode, roles])
