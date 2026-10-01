# -*- coding: utf-8 -*-
"""Unit tests for refactored egs_trade/paper_trade/wind.

WindPy is mocked throughout because no Wind key is available.
"""
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ))


# Provide a minimal ``WindPy`` stub at import time so that
# ``src.data_io.wind.*`` modules, which do ``from WindPy import w``
# at module load time, can be imported in the test environment where
# WindPy is not installed. Tests that need a live ``w`` mock inject
# their own via ``_patch_wind``.
if 'WindPy' not in sys.modules:
    sys.modules['WindPy'] = types.SimpleNamespace(
        w=mock.MagicMock(),
    )


class FakeWindRet:
    """Mimics the small surface of WindPy.WindData used by our code."""
    def __init__(self, error=0, fields=None, data=None):
        self.ErrorCode = error
        self.Fields = fields or []
        self.Data = data or []


def _make_fake_w(start_error=0, tlogon_data=(12345,),
                 tquery_fields=None, tquery_data=None):
    """Build a fresh MagicMock that quacks like WindPy.w."""
    fake_w = mock.MagicMock()
    fake_w.start.return_value = FakeWindRet(error=start_error)
    fake_w.tlogon.return_value = FakeWindRet(
        error=0, fields=['LogonID'], data=[[v] for v in tlogon_data],
    )
    if tquery_data is None:
        fake_w.tquery.return_value = FakeWindRet(
            error=0, fields=['AvailableFund'], data=[[1000.0]],
        )
    else:
        fake_w.tquery.return_value = FakeWindRet(
            error=0, fields=tquery_fields or ['AvailableFund'],
            data=tquery_data,
        )
    return fake_w


def _patch_wind(monkeypatch, fake_w):
    """Inject ``fake_w`` everywhere WindPy is imported in our src tree.

    We patch ``sys.modules['WindPy']`` so that any future ``import WindPy``
    or ``from WindPy import w`` resolves to our fake, AND we patch the
    already-imported ``w`` attribute in every ``src.data_io.wind.*``
    module that did ``from WindPy import w`` at import time. This avoids
    the per-test cache problem where stale references linger.
    """
    monkeypatch.setitem(sys.modules, 'WindPy', types.SimpleNamespace(w=fake_w))
    for mod_name in list(sys.modules):
        if mod_name.startswith('src.data_io.wind') and mod_name != 'src.data_io.wind':
            mod = sys.modules.get(mod_name)
            if mod is not None and hasattr(mod, 'w'):
                monkeypatch.setattr(mod, 'w', fake_w)


def test_double_ma_timing():
    from src.rules.timing_ctrl.moving_average import double_ma_timing
    assert double_ma_timing(10.0, 9.0, hold=False) == 'buy'
    assert double_ma_timing(9.0, 10.0, hold=True) == 'sell'
    assert double_ma_timing(10.0, 9.0, hold=True) == ''
    assert double_ma_timing(9.0, 10.0, hold=False) == ''


def test_parse_val_extracts_requested_fields():
    # parse_val does not touch WindPy at runtime; we just exercise the
    # pure logic
    fake_data = types.SimpleNamespace(
        Fields=['RT_LAST', 'RT_MA_5D', 'RT_MA_20D'],
        Data=[[100.5], [99.8], [97.2]],
    )
    from src.data_io.wind.utils import parse_val
    ret = parse_val(fake_data, ['RT_LAST', 'RT_MA_20D'])
    assert ret == {'RT_LAST': 100.5, 'RT_MA_20D': 97.2}


def test_logon_account_raises_when_file_missing(tmp_path, monkeypatch):
    _patch_wind(monkeypatch, _make_fake_w())
    from src.data_io.wind.account_login import logon_account
    with pytest.raises(FileNotFoundError):
        logon_account(str(tmp_path / 'missing.txt'), 'SHSZ')


def test_logon_account_parses_account_file(tmp_path, monkeypatch):
    fake_w = _make_fake_w(tlogon_data=(777,))
    _patch_wind(monkeypatch, fake_w)

    p = tmp_path / 'acc.txt'
    p.write_text('TEST_ACC\n', encoding='utf-8')

    from src.data_io.wind.account_login import logon_account
    account, log_id = logon_account(str(p), 'SHSZ')
    assert account == 'TEST_ACC'
    assert log_id == 777


def test_check_account_smoke(tmp_path, monkeypatch):
    fake_w = _make_fake_w(
        tquery_fields=['AvailableFund'], tquery_data=[[500.0]],
    )
    _patch_wind(monkeypatch, fake_w)

    from src.data_io.wind.account_login import logon_wind, logon_account
    from src.data_io.wind.query_rt_data import check_account_info

    p = tmp_path / 'acc.txt'
    p.write_text('USER1\n', encoding='utf-8')

    logon_wind()  # should not raise since start ErrorCode=0
    _, log_id = logon_account(str(p), 'SHSZ')
    check_account_info(log_id)  # should not raise