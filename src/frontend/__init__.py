"""Gradio frontend for the all-in-one trading platform."""

from importlib import import_module


def __getattr__(name):
    if name == "build_gradio_app":
        return import_module("src.frontend.app").build_gradio_app
    if name == "gradio_mount_options":
        return import_module("src.frontend.theme").gradio_mount_options
    raise AttributeError(name)


__all__ = ["build_gradio_app", "gradio_mount_options"]
