"""Each Gradio worker inherits its own request market and restores ambient state."""

from types import SimpleNamespace

import gradio as gr
import pytest
from gradio.context import LocalContext

from src.data.manager import REQUEST_MARKET, current_market
from src.frontend.common.callbacks import safe


def test_gradio_market_is_scoped_to_request_headers():
    outer = REQUEST_MARKET.set("US")
    request = LocalContext.request.set(SimpleNamespace(headers={"x-aiquant-market": "HK"}))
    try:
        assert safe(current_market)() == "HK"
        assert current_market() == "US"
    finally:
        LocalContext.request.reset(request)
        REQUEST_MARKET.reset(outer)


def test_gradio_error_restores_original_request_market():
    outer = REQUEST_MARKET.set("CN")
    request = LocalContext.request.set(SimpleNamespace(headers={"x-aiquant-market": "HK"}))

    def unavailable():
        assert current_market() == "HK"
        raise ValueError("Controlled callback failure")

    try:
        with pytest.raises(gr.Error):
            safe(unavailable)()
        assert current_market() == "CN"
    finally:
        LocalContext.request.reset(request)
        REQUEST_MARKET.reset(outer)
