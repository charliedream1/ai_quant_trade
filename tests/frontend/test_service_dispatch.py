"""The lazy callback registry preserves the actual public and private facade surface."""

from src.frontend.service_dispatch import CallbackServices, callback_registry
from src.frontend.services import FrontendService


def test_registry_covers_legacy_callbacks_and_binds_same_owners():
    legacy, lazy = FrontendService(), CallbackServices()
    expected = {
        name
        for name in dir(FrontendService)
        if not name.startswith("__") and name != "callback" and callable(getattr(FrontendService, name))
    }
    assert expected == set(callback_registry())
    for name in expected:
        left, right = getattr(legacy, name), lazy.callback(name)
        assert getattr(left, "__func__", left) is getattr(right, "__func__", right)
