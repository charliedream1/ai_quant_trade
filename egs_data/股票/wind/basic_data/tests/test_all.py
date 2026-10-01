# -*- coding: utf-8 -*-
"""Unit tests for refactored egs_data/股票/wind/basic_data (WindPy mocked)."""
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ))


class FakeWindRet:
    def __init__(self, error=0, fields=None, data=None):
        self.ErrorCode = error
        self.Fields = fields or []
        self.Data = data or []


def _install_wind_mock():
    fake_w = mock.MagicMock()
    fake_w.start.return_value = FakeWindRet(error=0)
    # w.wset returns (error, dataframe)
    fake_w.wset.return_value = (0, None)
    fake_w.tlogon.return_value = FakeWindRet(error=0, fields=['LogonID'], data=[[1]])
    sys.modules['WindPy'] = types.SimpleNamespace(w=fake_w)
    return fake_w


def test_parse_val_extracts_fields():
    _install_wind_mock()
    fake_data = types.SimpleNamespace(
        Fields=['RT_LAST', 'RT_MA_5D'],
        Data=[[100.5], [99.0]],
    )
    from src.data_io.wind.utils import parse_val
    ret = parse_val(fake_data, ['RT_LAST'])
    assert ret == {'RT_LAST': 100.5}


def test_make_dirs_idempotent(tmp_path):
    from src.tools.file_io.make_nd_clean_dirs import make_dirs
    target = tmp_path / 'a' / 'b' / 'c'
    make_dirs(str(target))
    assert target.exists()
    # calling again is a no-op
    make_dirs(str(target))
    assert target.exists()


def test_wind_data_loader_construction():
    """WindDataLoader.__init__ calls w.start(); with a mock it just records the call."""
    fake_w = _install_wind_mock()
    # import lazily so the WindPy mock is in place
    from src.data_io.wind.dump_data import WindDataLoader
    loader = WindDataLoader()
    assert fake_w.start.called


def test_dump_data_module_importable():
    """Just importing the module already covers the rewrite of imports."""
    import importlib
    mod = importlib.import_module('src.data_io.wind.dump_data')
    assert hasattr(mod, 'WindDataLoader')
    assert hasattr(mod, 'make_dirs')
    assert hasattr(mod, 'clean_dirs')


def test_save_index_data_module_importable():
    """Make sure the patched entry script still imports cleanly."""
    import importlib
    spec = importlib.util.spec_from_file_location(
        'save_index_data',
        str(PROJ / 'save_index_data.py'),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, 'WindDataLoader')


def test_save_market_data_module_importable():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'save_market_data',
        str(PROJ / 'save_market_data.py'),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, 'WindDataLoader')
