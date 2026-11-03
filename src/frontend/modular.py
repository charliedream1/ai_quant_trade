"""Independent Gradio Blocks factories for each frontend domain."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import gradio as gr

from .common.callbacks import safe as _safe
from .common.components import supports_parameter as _supports_parameter
from .features import (
    render_admin,
    render_ai,
    render_dashboard,
    render_floating_assistant,
    render_knowledge,
    render_live,
    render_market,
    render_research,
    render_simulation,
    render_strategy,
)
from .features.learning import render_learning
from .handlers import build_frontend_handlers
from .header import header_html
from .navigation import module_navigation_html
from .registry import get_module
from .service.foundation import (
    AI_EXPERT_CHOICES,
    AI_JOB_TEMPLATE_CHOICES,
    AI_TASK_TYPE_CHOICES,
    AI_TEAM_CHOICES,
    RELATION_TYPE_CHOICES,
    current_market,
    strategy_example_choices,
    switch_ui_market,
)
from .service_dispatch import CallbackServices
from .theme import APP_JS, CSS, HOME_CSS, gradio_mount_options
from .theme import theme as _theme

MODULAR_CSS = """
#module-navigation {
  display: flex;
  align-items: center;
  gap: 4px;
  overflow-x: auto;
  padding: 7px 8px;
  margin: 0 0 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 255, 255, .94);
  scrollbar-width: thin;
}
#module-navigation .module-nav-link {
  flex: 0 0 auto;
  padding: 7px 11px;
  color: #36505d;
  border: 1px solid transparent;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
}
#module-navigation .module-nav-link:hover {
  color: var(--brand-strong);
  border-color: var(--line-strong);
  background: #eff7ff;
}
#module-navigation .module-nav-link.active {
  color: #fff;
  border-color: var(--brand-strong);
  background: var(--brand-strong);
}
#module-navigation {
  padding: 6px 8px;
  border-color: var(--line);
  border-radius: var(--radius-panel);
  background: color-mix(in srgb, var(--surface-raised) 92%, var(--canvas));
  box-shadow: var(--shadow-soft);
}
#module-navigation .module-nav-link {
  padding: 7px 12px;
  border-radius: 8px;
  color: var(--muted);
  font-weight: 650;
}
#module-navigation .module-nav-link:hover {
  color: var(--brand-strong);
  border-color: color-mix(in srgb, var(--brand) 22%, var(--line));
  background: color-mix(in srgb, var(--brand) 7%, transparent);
}
#module-navigation .module-nav-link.active {
  color: var(--brand-strong);
  border-color: color-mix(in srgb, var(--brand) 18%, var(--line));
  background: color-mix(in srgb, var(--brand) 12%, var(--surface-raised));
  box-shadow: inset 0 -2px 0 var(--brand);
}
.modular-page-heading {
  margin: 0 0 8px;
  color: var(--ink);
}
html.gradio-embedded .gradio-container {
  max-width: none !important;
  padding-top: 0 !important;
}
html.gradio-embedded .app-header,
html.gradio-embedded #module-navigation,
html.gradio-embedded #module-app-header,
html.gradio-embedded #module-navigation-container,
html.gradio-embedded #main-navigation > .tab-wrapper,
html.gradio-embedded .module-tabs > .tab-wrapper {
  display: none !important;
}
html.gradio-embedded #main-navigation > .tabitem { padding-top: 0 !important; }
@media (max-width: 720px) {
  #module-navigation { padding: 6px; }
  #module-navigation .module-nav-link { padding: 6px 9px; font-size: 12px; }
}
"""


def modular_gradio_mount_options(theme_mode: str | None = None, module_key: str | None = None) -> dict[str, Any]:
    options = dict(gradio_mount_options(theme_mode))
    if "css" in options:
        options["css"] = f"{options['css']}\n{MODULAR_CSS}"
        if module_key == "dashboard":
            options["css"] += HOME_CSS
    return options


def _market_controls() -> tuple[gr.Radio, gr.Markdown]:
    with gr.Row(elem_id="market-switcher-row"):
        market_switcher = gr.Radio(
            ["A股", "美股"],
            # A cached Blocks default must not suppress the browser's market-sync change event after reload.
            value=None,
            label="市场",
            interactive=True,
            elem_id="market-switcher",
            scale=0,
            min_width=260,
        )
        market_status = gr.Markdown(
            f"当前市场：**{'美股' if current_market() == 'US' else 'A股'}**  ·  切换后按需刷新当前模块",
            elem_classes=["market-status-strip"],
        )
    return market_switcher, market_status


def _bind_basic_market_switch(market_switcher: gr.Radio, market_status: gr.Markdown) -> None:
    def change_market(value: str) -> str:
        market = switch_ui_market(value)
        label = "美股" if market == "US" else "A股"
        return f"当前市场：**{label}**  ·  已切换并清空当日缓存，请刷新当前数据"

    market_switcher.change(
        _safe(change_market),
        inputs=market_switcher,
        outputs=market_status,
        queue=False,
    )


@lru_cache(maxsize=16)
def build_gradio_module(module_key: str) -> gr.Blocks:
    module = get_module(module_key)
    service = CallbackServices()
    handlers = build_frontend_handlers(service)
    handler = getattr(handlers, "knowledge" if module.key == "learning" else module.key)
    blocks_options: dict[str, Any] = {
        "title": f"{module.title} - 一体化量化交易平台",
        "fill_width": True,
    }
    if _supports_parameter(gr.Blocks, "theme"):
        blocks_options.update(
            theme=_theme(), css=f"{CSS}\n{MODULAR_CSS}{HOME_CSS if module.key == 'dashboard' else ''}", js=APP_JS
        )

    with gr.Blocks(**blocks_options) as demo:
        gr.HTML(header_html(), elem_id="module-app-header")
        gr.HTML(module_navigation_html(module.key), elem_id="module-navigation-container")
        market_switcher, market_status = _market_controls()

        with gr.Tabs(elem_id="main-navigation"):
            if module.key == "dashboard":
                render_dashboard(handler, market_switcher, market_status, demo.load)
            elif module.key == "market":
                _bind_basic_market_switch(market_switcher, market_status)
                render_market(handler, [value for _, value in RELATION_TYPE_CHOICES])
            elif module.key == "research":
                _bind_basic_market_switch(market_switcher, market_status)
                render_research(handler)
            elif module.key == "strategy":
                _bind_basic_market_switch(market_switcher, market_status)
                render_strategy(handler, strategy_example_choices())
            elif module.key == "simulation":
                _bind_basic_market_switch(market_switcher, market_status)
                render_simulation(handler)
            elif module.key == "live":
                _bind_basic_market_switch(market_switcher, market_status)
                render_live(handler)
            elif module.key == "ai":
                _bind_basic_market_switch(market_switcher, market_status)
                render_ai(
                    handler,
                    AI_TASK_TYPE_CHOICES[0][1] if AI_TASK_TYPE_CHOICES else "general",
                    AI_EXPERT_CHOICES[0][1] if AI_EXPERT_CHOICES else "",
                    AI_TEAM_CHOICES[0][1] if AI_TEAM_CHOICES else "",
                    AI_JOB_TEMPLATE_CHOICES[0][1] if AI_JOB_TEMPLATE_CHOICES else "",
                    demo.load,
                )
            elif module.key == "knowledge":
                _bind_basic_market_switch(market_switcher, market_status)
                render_knowledge(handler)
            elif module.key == "learning":
                render_learning()
            elif module.key == "admin":
                _bind_basic_market_switch(market_switcher, market_status)
                render_admin(handler)

        render_floating_assistant(handlers.assistant)
        gr.HTML(
            "<div class='compact-note'><p>仅供学习和研究使用，不构成投资建议。"
            "数据源与交易通道状态以系统配置为准。</p></div>"
        )

    return demo.queue(default_concurrency_limit=8)
