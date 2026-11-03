"""Normalize Gradio text blocks before reusing chat history or model context."""

from typing import Any


def chat_content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list | tuple):
        return "\n".join(text for item in value if (text := chat_content_text(item)))
    if isinstance(value, dict):
        # Keep text blocks readable; do not expose file dictionaries or encoded image data.
        if isinstance(value.get("text"), str):
            return value["text"]
        if "content" in value:
            return chat_content_text(value["content"])
        return ""
    return "" if value is None else str(value)
