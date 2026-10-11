# -*- coding: utf-8 -*-
"""Loguru 日志统一配置

使用方式：
    from excel_monitor.logger import get_logger
    logger = get_logger("ExcelManager")
    logger.info("已打开 Excel: ...")

或在模块顶层：
    from excel_monitor.logger import logger
    logger.info("启动...")
"""
import sys

from loguru import logger as _logger


def _configure_logger():
    """配置 loguru 默认 handler

    - 输出到 stderr（与原 logging.basicConfig 行为一致）
    - 格式: HH:MM:SS [LEVEL] 模块名: 消息
    """
    _logger.remove()
    _logger.configure(extra={"name": "root"})
    _logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "<green>{time:HH:mm:ss}</green> "
            "[<level>{level}</level>] "
            "<cyan>{extra[name]}</cyan>: {message}"
        ),
    )


# 模块加载时即完成配置
_configure_logger()


def get_logger(name: str):
    """获取绑定模块名的 logger

    Args:
        name: 模块名（通常是类名或 'main'）

    Returns:
        绑定了 name 的 loguru logger
    """
    return _logger.bind(name=name)


# 导出全局 logger（已绑定默认 name=root）
logger = _logger.bind(name="root")
