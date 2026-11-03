"""A small Gradio HTML bootstrap loads the shared runtime once per document."""

import json
from hashlib import sha256

from src.core.config import get_settings
from src.frontend.theme import theme_runtime_js


def runtime_source() -> str:
    return "(" + theme_runtime_js(get_settings().ui_theme) + ")();"


def runtime_loader_js() -> str:
    revision = sha256(runtime_source().encode("utf-8")).hexdigest()[:16]
    url = json.dumps(get_settings().api_prefix + "/ui/runtime.js?v=" + revision)
    return (
        """if (!document.querySelector('script[data-aiquant-runtime]')) {
const script = document.createElement('script'); script.dataset.aiquantRuntime = '1';
script.src = """
        + url
        + "; document.head.append(script); }"
    )
