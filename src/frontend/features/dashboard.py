"""Gradio UI for the dashboard domain."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import gradio as gr

from ..common.callbacks import safe as _safe
from ..common.components import plot as _plot
from ..common.components import table as _table
from ..handlers import DomainHandler
from ..service.foundation import (
    ACCOUNT_MODE_CHOICES,
    DASHBOARD_MODULE_CHOICES,
    DASHBOARD_MODULE_KEYS,
    DASHBOARD_MODULES,
)
from ..service.home_tables import home_styled_frame
from .home import render_home


def render_dashboard(
    service: DomainHandler,
    market_switcher: gr.Radio,
    market_status: gr.Markdown,
    load_event: Callable[..., Any],
) -> None:
    with gr.Tab("投研看板"):
        with gr.Tabs(elem_classes=["module-tabs"]):
            with gr.Tab("总览"):
                render_home(service, market_switcher, market_status, load_event)

            with gr.Tab("自定义仪表盘") as custom_dashboard_tab:
                initial_custom_layout = service.load_dashboard_layout()
                with gr.Row():
                    custom_account_mode = gr.Radio(
                        ACCOUNT_MODE_CHOICES,
                        value="paper",
                        label="账户视角",
                        scale=1,
                    )
                    custom_layout_modules = gr.CheckboxGroup(
                        DASHBOARD_MODULE_CHOICES,
                        value=initial_custom_layout,
                        label="显示模块（勾选即时显隐；点击“保存布局”后刷新页面按保存顺序排列）",
                        scale=4,
                    )
                    custom_layout_save = gr.Button("保存布局", variant="primary", scale=0, min_width=110)
                    custom_refresh = gr.Button("刷新模块", scale=0, min_width=110, elem_classes=["page-refresh-btn"])
                custom_status = gr.Markdown(elem_classes=["status-strip"])
                custom_components: dict[str, Any] = {}
                custom_columns: dict[str, Any] = {}
                for module_key, module_label, module_kind in DASHBOARD_MODULES:
                    with gr.Column(
                        visible=module_key in initial_custom_layout,
                        elem_classes=["dashboard-module"],
                    ) as panel:
                        if module_kind == "html":
                            gr.Markdown(f"##### {module_label}")
                            custom_components[module_key] = gr.HTML()
                        elif module_kind == "plot":
                            custom_components[module_key] = _plot(
                                label=module_label,
                                elem_classes=["chart-panel"],
                            )
                        else:
                            custom_components[module_key] = _table(
                                module_label, 300, elem_classes=["home-semantic-table"]
                            )
                    custom_columns[module_key] = panel

                def _toggle_dashboard_modules(selected: Any) -> tuple[Any, ...]:
                    selected_keys = {str(key) for key in (selected or [])}
                    return tuple(gr.update(visible=module_key in selected_keys) for module_key in DASHBOARD_MODULE_KEYS)

                custom_market_outputs = [
                    custom_components["monitor"],
                    custom_components["style"],
                    custom_components["theme_chain"],
                    custom_components["paths"],
                    custom_components["indices"],
                    custom_components["watchlist"],
                    custom_components["sector_plot"],
                ]
                custom_account_outputs = [
                    custom_components["risk"],
                    custom_components["holdings"],
                    custom_components["account_plot"],
                ]
                custom_strategy_outputs = [custom_components["actions"], custom_components["strategy"]]

                def _custom_market(mode: str, force: bool) -> tuple:
                    result = service.dashboard_market(mode, force_refresh=force)
                    return (*(home_styled_frame(frame) for frame in result[:4]), *result[4:])

                def _bind_custom_dashboard_progressive(event_method: Callable[..., Any], force_refresh: bool) -> None:
                    event_method(
                        _safe(lambda mode: service.dashboard_summary(mode, force_refresh=force_refresh)),
                        inputs=custom_account_mode,
                        outputs=[custom_status, custom_components["kpis"]],
                        queue=False,
                    )
                    event_method(
                        _safe(lambda mode: _custom_market(mode, force_refresh)),
                        inputs=custom_account_mode,
                        outputs=custom_market_outputs,
                        queue=False,
                    )
                    event_method(
                        _safe(lambda mode: service.dashboard_account(mode, force_refresh=force_refresh)),
                        inputs=custom_account_mode,
                        outputs=custom_account_outputs,
                        queue=False,
                    )
                    event_method(
                        _safe(
                            lambda mode: tuple(
                                home_styled_frame(frame)
                                for frame in service.dashboard_strategy(mode, force_refresh=force_refresh)
                            )
                        ),
                        inputs=custom_account_mode,
                        outputs=custom_strategy_outputs,
                        queue=False,
                    )

                _bind_custom_dashboard_progressive(custom_refresh.click, True)
                _bind_custom_dashboard_progressive(custom_dashboard_tab.select, False)
                _bind_custom_dashboard_progressive(custom_account_mode.change, False)
                custom_layout_modules.change(
                    _toggle_dashboard_modules,
                    inputs=custom_layout_modules,
                    outputs=[custom_columns[key] for key in DASHBOARD_MODULE_KEYS],
                    queue=False,
                )
                custom_layout_save.click(
                    _safe(service.save_dashboard_layout),
                    inputs=custom_layout_modules,
                    outputs=custom_status,
                    queue=False,
                )
