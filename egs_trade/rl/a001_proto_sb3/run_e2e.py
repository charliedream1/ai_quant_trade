# -*- coding: utf-8 -*-
"""End-to-end run script for a001_proto_sb3.

Prepares a tiny synthetic price CSV in the format that
``StockTradingEnv`` reads, then drives the real ``ProtoRLSb3.train``
and ``ProtoRLSb3.test`` pipeline (the same code path as
``test_a_stock_trade``).

Run from the project root:

    python run_e2e.py
"""
import os
import sys
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJ))

# 1. Build synthetic CSV data shaped like baostock output.
train_dir = PROJ / 'e2e_data' / 'train'
test_dir = PROJ / 'e2e_data' / 'test'
out_dir = PROJ / 'e2e_out'
for d in (train_dir, test_dir, out_dir):
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)

def _make_csv(path: Path, n: int, base: float, slope: float):
    rng = np.random.default_rng(0)
    dates = pd.date_range('2022-01-01', periods=n, freq='D')
    close = base + np.cumsum(rng.normal(0, 0.5, n)) + np.linspace(0, slope * n, n)
    df = pd.DataFrame({
        'date': dates.strftime('%Y-%m-%d'),
        'open': close - 0.1,
        'high': close + 0.5,
        'low': close - 0.5,
        'close': close,
        'volume': rng.integers(1_000_000, 5_000_000, n),
        'amount': rng.integers(1e8, 5e8, n),
        'adjustflag': np.ones(n),
        'tradestatus': np.ones(n),
        'pctChg': rng.normal(0, 0.02, n),
        'peTTM': rng.uniform(5, 30, n),
        'pbMRQ': rng.uniform(0.5, 5, n),
        'psTTM': rng.uniform(1, 8, n),
    })
    df.to_csv(path, index=False)


stock_code = '600036'
_make_csv(train_dir / f'{stock_code}.csv', 80, base=10.0, slope=0.10)
_make_csv(test_dir / f'{stock_code}.csv', 40, base=18.0, slope=-0.05)

# 2. Drive the real RL pipeline.
from main import ProtoRLSb3, test_a_stock_trade  # noqa: E402

init_balance = 10000

# direct call into the project's RL wrapper (same path as main())
mdl = ProtoRLSb3(init_balance)
mdl.train(str(train_dir / f'{stock_code}.csv'))
profits = mdl.test(str(test_dir / f'{stock_code}.csv'))

assert len(profits) > 0, 'no profit steps returned'
print('E2E OK: ProtoRLSb3.train/test pipeline produced',
      len(profits), 'profit steps for', stock_code)

# also exercise the wrapper function that main() uses
import matplotlib
matplotlib.use('Agg')  # non-interactive backend
test_a_stock_trade(str(train_dir), str(test_dir),
                   stock_code, init_balance, out_path=str(out_dir))
assert (out_dir / f'{stock_code}.png').exists()
print('E2E OK: test_a_stock_trade wrapper produced plot at',
      out_dir / f'{stock_code}.png')