"""JSON-only port RPC for explicitly reviewed custom strategy source."""

import contextlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

from src.strategy.execution_policy import execution_config
from src.strategy.loader import StrategyLoader
from src.strategy.ports import MarketEvent, StrategyContext
from src.strategy.worker_policy import install_policy


def main():
    protocol = sys.stdout
    maximum = execution_config()["worker"]["max_message_bytes"]
    adapter = None
    with contextlib.redirect_stdout(sys.stderr):
        for line in sys.stdin:
            try:
                if len(line.encode("utf-8")) > maximum:
                    raise ValueError("策略请求超过大小限制")
                request = json.loads(line)
                action = request["action"]
                if action == "load":
                    source, work = Path(request["source"]), Path(request["work"])
                    loader = StrategyLoader()
                    install_policy(work, source, execution_config()["worker"]["memory_bytes"])
                    adapter = loader._load_local(source, request["params"], request.get("entry")).adapter
                    runtime = getattr(getattr(adapter, "instance", None), "runtime", None)
                    result = {
                        "adapter_type": adapter.adapter_type,
                        "entry_name": adapter.entry_name,
                        "capabilities": adapter.capabilities,
                        "params_schema": adapter.params_schema,
                        "warmup": callable(getattr(runtime, "warmup", None)),
                        "order_type": getattr(runtime, "required_order_type", "market"),
                    }
                else:
                    if adapter is None:
                        raise ValueError("策略尚未加载")
                    context = StrategyContext(**request.get("context", {}))
                    if action == "warmup":
                        if runtime is None:
                            raise ValueError("该策略没有预热接口")
                        runtime.warmup(request["history"])
                        signals = None
                    elif action in {"on_start", "on_stop"}:
                        signals = getattr(adapter, action)(context)
                    else:
                        signals = getattr(adapter, action)(MarketEvent(**request["event"]), context)
                    result = {"signals": [asdict(signal) for signal in signals or []], "context": context.to_dict()}
                message = {"ok": True, "data": result}
            except Exception as exc:
                message = {"ok": False, "error_type": type(exc).__name__, "error": str(exc)}
            protocol.write(json.dumps(message, ensure_ascii=False, allow_nan=False) + "\n")
            protocol.flush()


if __name__ == "__main__":
    main()
