PARAMS_SCHEMA = [
    {"name": "quantity", "type": "int", "default": 100, "min": 1, "max": 100000},
    {"name": "close_threshold", "type": "float", "default": 10.2, "min": 0.0, "max": 100000.0},
]


def generate_signal(bar, context):
    params = context.get("params") or {}
    close_threshold = float(params.get("close_threshold", 10.2))
    quantity = int(params.get("quantity", 100))
    if float(bar.get("close") or 0) >= close_threshold:
        return {
            "symbol": bar.get("symbol"),
            "side": "buy",
            "quantity": quantity,
            "reason": "function_threshold",
        }
    return []
