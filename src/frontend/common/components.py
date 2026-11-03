"""Shared Gradio component factories."""

from __future__ import annotations

from collections.abc import Callable
from inspect import signature
from typing import Any

import gradio as gr

from .chart_help import help_key


def plot(*args: Any, **kwargs: Any) -> gr.Plot:
    classes = list(kwargs.pop("elem_classes", None) or [])
    classes.extend(["has-chart-help", "chart-help-key-" + help_key(str(kwargs.get("label") or ""))])
    return gr.Plot(*args, elem_classes=classes, **kwargs)


def supports_parameter(callable_object: Callable[..., Any], name: str) -> bool:
    return name in signature(callable_object).parameters


def table(
    label: str,
    height: int = 360,
    elem_classes: list[str] | None = None,
    datatype: str | list[str] | None = None,
    value: Any | None = None,
    elem_id: str | None = None,
) -> gr.Dataframe:
    height_parameter = "height" if supports_parameter(gr.Dataframe, "height") else "max_height"
    display_height = max(height, 520 if height_parameter == "height" else 640)
    options: dict[str, Any] = {
        "label": label,
        "interactive": False,
        "elem_classes": ["data-table", *(elem_classes or [])],
        height_parameter: display_height,
    }
    if value is not None:
        options["value"] = value
    if elem_id:
        options["elem_id"] = elem_id
    if supports_parameter(gr.Dataframe, "wrap"):
        options["wrap"] = True
    if supports_parameter(gr.Dataframe, "buttons"):
        options["buttons"] = ["fullscreen", "copy"]
    if datatype is not None and supports_parameter(gr.Dataframe, "datatype"):
        options["datatype"] = datatype
    return gr.Dataframe(**options)


def chatbot(label: str, height: int, elem_id: str) -> gr.Chatbot:
    options: dict[str, Any] = {"label": label, "height": height, "elem_id": elem_id}
    if supports_parameter(gr.Chatbot, "type"):
        options["type"] = "messages"
    if supports_parameter(gr.Chatbot, "show_copy_button"):
        options["show_copy_button"] = True
    elif supports_parameter(gr.Chatbot, "buttons"):
        options["buttons"] = ["copy"]
    return gr.Chatbot(**options)
