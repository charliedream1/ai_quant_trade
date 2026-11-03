"""Backend process entry point."""

import os
import sys
from pathlib import Path

import uvicorn

from src.core.config import get_settings
from src.core.logger import get_logger, intercept_stdlib_logging, setup_logging
from src.core.runtime_environment import enforce_startup_runtime


def main() -> None:
    settings = get_settings()
    setup_logging(settings.data_dir / "logs", settings.log_level)
    intercept_stdlib_logging()
    log = get_logger("main")
    enforce_startup_runtime()
    log.info(
        "backend runtime fingerprint | pid={} executable={} python={} cwd={} command={} project_root={}",
        os.getpid(),
        sys.executable,
        sys.version.split()[0],
        Path.cwd(),
        " ".join(sys.argv),
        settings.project_root,
    )
    log.info(
        "启动 AIQuant智投一体化平台 | data_mode={} | http://{}:{} | data_dir={} | db_path={}",
        settings.data_mode,
        settings.host,
        settings.port,
        settings.data_dir,
        settings.db_path,
    )
    # log_config=None：禁止 uvicorn 重新 dictConfig，全部日志走 loguru 拦截器
    uvicorn.run(
        "src.api.app:app",
        host=settings.host,
        port=settings.port,
        log_level="warning",
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
