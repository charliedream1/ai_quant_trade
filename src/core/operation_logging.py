"""Loguru operation timing; failures remain failures rather than exiting successfully."""

from functools import wraps
from time import perf_counter

from loguru import logger

SECONDS_PER_MINUTE = 60
log = logger


def init_log(name="root"):
    return logger.bind(module=name)


def time_str(seconds):
    if seconds < SECONDS_PER_MINUTE:
        return f"{seconds:.2f} sec"
    return f"{seconds / SECONDS_PER_MINUTE:.2f} min"


def addlog(name=""):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            started = perf_counter()
            operation = name or function.__qualname__
            logger.info("Operation started | operation={}", operation)
            try:
                result = function(*args, **kwargs)
            except Exception as exc:
                logger.error("Operation failed | operation={} error_type={}", operation, type(exc).__name__)
                raise
            logger.info("Operation completed | operation={} duration={}", operation, time_str(perf_counter() - started))
            return result

        return wrapped

    return decorate
