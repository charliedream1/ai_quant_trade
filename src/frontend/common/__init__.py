"""Shared UI exports without importing Gradio into source workers."""

from importlib import import_module

EXPORTS = {
    "callback_location": (".callbacks", "callback_location"),
    "safe": (".callbacks", "safe"),
    "chatbot": (".components", "chatbot"),
    "supports_parameter": (".components", "supports_parameter"),
    "table": (".components", "table"),
}
__all__ = ["callback_location", "safe", "chatbot", "supports_parameter", "table"]


def __getattr__(name):
    if name not in EXPORTS:
        raise AttributeError(name)
    module, symbol = EXPORTS[name]
    value = getattr(import_module(module, __name__), symbol)
    globals()[name] = value
    return value
