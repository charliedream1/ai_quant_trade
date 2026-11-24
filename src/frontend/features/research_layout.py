"""Stable research panels and tabs shared by embedded and standalone pages."""

from html import escape

import gradio as gr

from ..common.navigation import navigation_config


def research_tabs(view: str):
    group = navigation_config()["tab_groups"][f"market/{view}"]
    buttons = "".join(
        f'<button type="button" role="tab" id="research-tab-{name}" data-tab-id="{name}" '
        f'aria-controls="research-panel-{name}" aria-selected="false" tabindex="-1">{escape(tab["label"])}</button>'
        for name, tab in group["tabs"].items()
    )
    gr.HTML(f'<div class="tab-wrapper research-tab-strip" role="tablist">{buttons}</div>', elem_id=group["id"])


def research_panels(view: str):
    group = navigation_config()["tab_groups"][f"market/{view}"]
    return gr.Tabs(
        selected=group["default"],
        elem_id=f"{group['id']}-panels",
        elem_classes=["research-native-tabs"],
    )


def research_panel(name: str):
    return gr.Tab(name, id=name, elem_id=f"research-panel-{name}", render_children=False)
