"""Stateful strategy RPC keeps reviewed custom code outside the Web process."""

import json
import subprocess
import sys
import threading
from collections import deque
from dataclasses import asdict
from queue import Empty, Full, Queue
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from src.core.config import PROJECT_ROOT, get_settings
from src.core.process_env import process_environment
from src.strategy.execution_policy import execution_config
from src.strategy.ports import StrategySignal
from src.strategy.worker_limits import attach_limits, close_limits


class ProcessStrategyPort:
    adapter_type: str
    entry_name: str
    capabilities: list[str]
    params_schema: Any

    def __init__(self, source_path, params, entry, *, source: bytes | None = None):
        self.policy = execution_config()["worker"]
        self.work = get_settings().data_dir / "strategy_workers" / uuid4().hex
        self.work.mkdir(parents=True, exist_ok=False)
        snapshot = self.work / "strategy.py"
        snapshot.write_bytes(source_path.read_bytes() if source is None else source)
        env = process_environment(
            "strategy",
            supplied={
                "ALL_IN_ONE_DATA_DIR": str(self.work / "data"),
                "ALL_IN_ONE_DB_PATH": str(self.work / "data/platform.db"),
                "ALL_IN_ONE_DOCUMENT_STORAGE_DIR": str(self.work / "data/documents"),
                "TEMP": str(self.work),
                "TMP": str(self.work),
                "HOME": str(self.work),
                "USERPROFILE": str(self.work),
            },
        )
        self.process = subprocess.Popen(
            [sys.executable, "-B", "-u", str(PROJECT_ROOT / "egs/entrypoints/strategy_worker.py")],
            cwd=self.work,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.responses: Queue[dict[str, Any]] = Queue(maxsize=2)
        self.stderr: deque[str] = deque(maxlen=self.policy["stderr_lines"])
        assert self.process.stdin is not None and self.process.stdout is not None and self.process.stderr is not None
        self.input, self.output, self.errors = self.process.stdin, self.process.stdout, self.process.stderr
        self.lock = threading.Lock()
        try:
            self.limit_handle = attach_limits(self.process, self.policy["memory_bytes"])
        except BaseException:
            self.process.kill()
            self.process.wait(timeout=5)
            raise
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._stderr, daemon=True).start()
        try:
            info = self._call(
                {"action": "load", "source": str(snapshot), "work": str(self.work), "params": params, "entry": entry}
            )
            for key in ("adapter_type", "entry_name", "capabilities", "params_schema"):
                setattr(self, key, info[key])
            if info["warmup"]:
                self.instance = SimpleNamespace(
                    runtime=SimpleNamespace(warmup=self._warmup, required_order_type=info["order_type"])
                )
        except BaseException:
            self.close()
            raise

    def _read(self):
        try:
            for line in iter(lambda: self.output.readline(self.policy["max_message_bytes"] + 1), ""):
                if len(line.encode("utf-8")) > self.policy["max_message_bytes"]:
                    self._offer({"ok": False, "error": "策略响应超过大小限制"})
                    self.process.kill()
                    return
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError("非法响应对象")
                except ValueError:
                    value = {"ok": False, "error": "策略工作进程返回非法协议"}
                if not self._offer(value):
                    return
        except (ValueError, OSError):
            pass
        finally:
            self._offer({"ok": False, "error": "策略工作进程已退出"})

    def _offer(self, value):
        try:
            self.responses.put_nowait(value)
            return True
        except Full:
            if self.process.poll() is None:
                self.process.kill()
            return False

    def _stderr(self):
        try:
            for line in iter(lambda: self.errors.readline(4096), ""):
                self.stderr.append(line[:1000])
        except (ValueError, OSError):
            pass

    def _call(self, request):
        with self.lock:
            message = json.dumps(request, ensure_ascii=False, allow_nan=False) + "\n"
            if len(message.encode("utf-8")) > self.policy["max_message_bytes"]:
                raise ValueError("策略上下文超过工作进程消息上限")
            self.input.write(message)
            self.input.flush()
            try:
                response = self.responses.get(
                    timeout=self.policy["startup_seconds"]
                    if request["action"] == "load"
                    else self.policy["call_seconds"]
                )
            except Empty:
                self.close()
                raise TimeoutError("策略工作进程未在截止时间内返回") from None
            if not response.get("ok"):
                raise ValueError(
                    str(response.get("error") or "策略工作进程失败")
                    + (" | " + "".join(self.stderr)[-1000:] if self.process.poll() is not None else "")
                )
            return response["data"]

    def _event(self, action, context, event=None):
        payload = {"action": action, "context": context.to_dict()}
        if event is not None:
            payload["event"] = asdict(event)
        value = self._call(payload)
        context.metadata.update(value["context"]["metadata"])
        return [StrategySignal(**row) for row in value["signals"]]

    def _warmup(self, history):
        self._call({"action": "warmup", "history": history})

    def on_start(self, context):
        self._event("on_start", context)

    def on_bar(self, event, context):
        return self._event("on_bar", context, event)

    def on_tick(self, event, context):
        return self._event("on_tick", context, event)

    def on_stop(self, context):
        try:
            self._event("on_stop", context)
        finally:
            self.close()

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=5)
        close_limits(getattr(self, "limit_handle", None))
        self.limit_handle = None
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream:
                stream.close()

    def __del__(self):
        try:
            self.close()
        except (OSError, ValueError, AttributeError):
            pass
