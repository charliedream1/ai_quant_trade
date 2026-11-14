"""Bounded CLI transport validates capability events before accepting generated text."""

import json
import subprocess
from queue import Empty, Queue
from threading import Thread
from time import monotonic
from typing import Any

from src.agent.providers.events import check_research_event
from src.core.process_control import stop_process_tree


def _read_events(stream, queue, maximum):
    size = 0
    try:
        while True:
            line = stream.readline(maximum + 1)
            if not line:
                break
            size += len(line)
            if size > maximum:
                raise ValueError("CLI event stream exceeds response budget")
            if line.startswith(b"{"):
                queue.put(json.loads(line))
    except Exception:
        queue.put(ValueError("CLI event stream is invalid or exceeds response budget"))
    finally:
        queue.put(None)


def _write_prompt(stream, prompt):
    try:
        stream.write(prompt.encode("utf-8"))
        stream.flush()
    except (OSError, ValueError):
        pass  # The reader or process exit reports a rejected request.
    finally:
        stream.close()


def _discard_errors(stream, chunk_bytes):
    # Discard CLI diagnostics: they may contain authentication or installation data.
    while stream.read(chunk_bytes):
        pass


def text_only_process(command, environment, directory, prompt, limits, cancelled, observe):
    queue: Queue[Any] = Queue()
    started, initialized, final = monotonic(), False, None
    with subprocess.Popen(
        command,
        cwd=directory,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    ) as process:
        threads = [
            Thread(target=_read_events, args=(process.stdout, queue, limits["output_chars"] * 20), daemon=True),
            Thread(target=_discard_errors, args=(process.stderr, limits["stream_chunk_bytes"]), daemon=True),
            Thread(target=_write_prompt, args=(process.stdin, prompt), daemon=True),
        ]
        for thread in threads:
            thread.start()
        try:
            while True:
                if cancelled() or monotonic() - started > limits["model_seconds"]:
                    raise InterruptedError("Graph CLI request cancelled or timed out")
                try:
                    event = queue.get(timeout=0.2)
                except Empty:
                    continue
                if event is None:
                    break
                if isinstance(event, Exception):
                    raise event
                observe(event)
                check_research_event({"raw": event})
                if event.get("type") == "system" and event.get("subtype") == "init":
                    # WorkBuddy's native schema reports tools/MCP; optional Skill/plugin
                    # fields are rejected when nonempty by check_research_event above.
                    required = ("tools", "mcp_servers")
                    if any(event.get(key) != [] for key in required):
                        raise ValueError("Graph CLI initialization must prove all native capabilities are disabled")
                    initialized = True
                elif event.get("type") in {"assistant", "result", "stream_event"} and not initialized:
                    raise ValueError("Graph CLI generated output before verified initialization")
                if event.get("type") == "result":
                    final = event
            if not initialized or not final:
                raise ValueError("Graph CLI did not provide verified initialization and a result")
            process.wait(timeout=1)
            if process.returncode:
                raise ValueError("Graph CLI process exited unsuccessfully")
            return final
        finally:
            if process.poll() is None:
                stop_process_tree(process)
                process.wait(timeout=5)
            for thread in threads:
                thread.join(timeout=1)
