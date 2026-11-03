"""Every static chart label has domain-specific explanatory text."""

import ast
from pathlib import Path

from src.frontend.common.chart_help import catalog, chart_help_js, help_key


def test_chart_labels_have_specific_explanations():
    missing = []
    for path in Path("src/frontend/features").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Name)
                or node.func.id not in {"_plot", "plot"}
            ):
                continue
            label = next((item.value for item in node.keywords if item.arg == "label"), None)
            if isinstance(label, ast.Constant) and help_key(label.value) == "default":
                missing.append((str(path), label.value))
    assert not missing
    assert all(row["short"] and row["detail"] for row in catalog()["charts"].values())


def test_chart_help_does_not_inflate_gradio_page_payload():
    source = chart_help_js()
    assert len(source) < 1000
    assert "/static/chart_help.js" in source
    assert "innerHTML" not in Path("src/frontend/assets/chart_help.js").read_text(encoding="utf-8")
