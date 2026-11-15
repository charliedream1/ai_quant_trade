"""Convert pandas styling to the existing UI wire format without importing the UI SDK."""

from typing import Any


def styled_table(value) -> dict[str, Any]:
    # Pandas' computed representation is also the contract consumed by both supported Gradio versions.
    translated = value._compute()._translate(None, None)
    styles = {
        selector: "; ".join(f"{key}: {cell}" for key, cell in style.get("props", []))
        for style in translated.get("cellstyle", [])
        for selector in style.get("selectors", [])
    }
    hidden = set(getattr(value, "hidden_columns", []))
    columns = [index for index in range(len(value.data.columns)) if index not in hidden]
    visible = [
        [cell for index, cell in enumerate([cell for cell in row if cell["type"] == "td"]) if index not in hidden]
        for row in translated["body"]
    ]
    return {
        "headers": list(value.data.columns),
        "data": value.data.iloc[:, columns].to_dict(orient="split")["data"],
        "metadata": {
            "display_value": [[cell["display_value"] for cell in row] for row in visible],
            "styling": [[styles.get(cell.get("id"), "") for cell in row] for row in visible],
        },
    }
