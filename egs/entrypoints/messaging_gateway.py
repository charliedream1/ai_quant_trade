"""Standalone gateway sharing the configured platform database and local environment."""

import signal
import sys
from pathlib import Path
from threading import Event

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.channels.config import channel_config  # noqa: E402
from src.channels.runtime import Gateway  # noqa: E402


def main():
    if not channel_config()["enabled"]:
        logger.error("Enable messaging explicitly in local configuration before starting the gateway")
        return 1
    stopped = Event()
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    gateway = Gateway()
    gateway.start()
    try:
        while not stopped.wait(1):
            if gateway.thread and not gateway.thread.is_alive():
                return 1
    finally:
        gateway.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
