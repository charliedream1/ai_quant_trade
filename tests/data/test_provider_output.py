"""Provider stdout is routed per call without global monkeypatches or hidden failures."""

import sys

import pytest
from loguru import logger

from src.data.provider_output import provider_call


def sdk_operation(value):
    sys.stdout.write("")
    print(value)  # A synthetic third-party SDK function, never production output.
    return value


def test_sdk_success_is_debug_and_original_output_is_unchanged(capsys):
    records = []
    sink = logger.add(lambda message: records.append(message.record), level="DEBUG")
    original_stdout = sys.stdout
    try:
        assert provider_call(sdk_operation, "login success!") == "login success!"
        assert sys.stdout is original_stdout
        assert not capsys.readouterr().out
        assert records[-1]["level"].name == "DEBUG"
        assert "print" not in sdk_operation.__globals__
        provider_call(sdk_operation, "login failed!")
        assert records[-1]["level"].name == "WARNING"
    finally:
        logger.remove(sink)


def test_provider_exception_is_not_swallowed():
    def failed():
        raise OSError("provider unavailable")

    with pytest.raises(OSError, match="provider unavailable"):
        provider_call(failed)
