"""Bounded read-only CLI metadata exchange without generation or shell commands."""

import json
import os

# Metadata uses fixed argument vectors and never invokes a shell.
import subprocess  # nosec B404
from queue import Empty, Queue
from threading import Thread
from time import monotonic

from json_repair import loads

from src.core.process_control import stop_process_tree
from src.core.stream_control import stream_cancelled


def metadata(command, environment, directory, limits, *, rpc=False):
    events: Queue = Queue()

    def read(stream, collect):
        size = 0
        while line := stream.readline(limits["max_bytes"] + 1):
            size += len(line)
            if size > limits["max_bytes"]:
                events.put(ValueError("Metadata exceeds configured limit"))
                return
            if collect:
                events.put(line)
        if collect:
            events.put(None)

    with subprocess.Popen(
        command,
        cwd=directory,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=os.name != "nt",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    ) as process:  # nosec B603
        for stream, collect in ((process.stdout, True), (process.stderr, False)):
            Thread(target=read, args=(stream, collect), daemon=True).start()

        def send(value):
            if process.stdin is None:
                raise ValueError("Metadata input pipe unavailable")
            process.stdin.write((json.dumps(value) + "\n").encode())
            process.stdin.flush()

        try:
            if rpc:
                send(
                    {
                        "id": 1,
                        "method": "initialize",
                        "params": {"clientInfo": {"name": "aiquant_catalog", "version": "1.0"}},
                    }
                )
            deadline = monotonic() + limits["timeout_seconds"]
            lines: list[bytes] = []
            while monotonic() < deadline:
                if stream_cancelled():
                    raise InterruptedError("Metadata request cancelled")
                try:
                    line = events.get(timeout=min(0.1, max(0.001, deadline - monotonic())))
                except Empty:
                    continue
                if isinstance(line, Exception):
                    raise line
                if line is None:
                    if rpc or process.wait(timeout=1):
                        raise ValueError("Metadata command failed")
                    return loads(b"".join(lines).decode("utf-8", errors="replace"))
                if not rpc:
                    lines.append(line)
                    continue
                value = loads(line.decode("utf-8", errors="replace"))
                if not isinstance(value, dict):
                    continue
                if value.get("error"):
                    raise ValueError("Metadata RPC rejected")
                if value.get("id") == 1:
                    send({"method": "initialized"})
                    send(
                        {
                            "id": 2,
                            "method": "model/list",
                            "params": {"limit": limits["max_models"], "includeHidden": False},
                        }
                    )
                elif value.get("id") == 2:
                    return value.get("result") or {}
            raise TimeoutError("Metadata request timed out")
        finally:
            if process.poll() is None:
                stop_process_tree(process)
            process.wait(timeout=3)
