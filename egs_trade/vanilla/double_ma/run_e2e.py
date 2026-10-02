# -*- coding: utf-8 -*-
"""End-to-end run script for double_ma.

Boots the actual ``back_tester.main()`` entry point with synthetic
TuShare data and a deterministic price series. The TuShare client
has no real token in this environment, so we monkey-patch
``back_tester.TuShareData`` before calling ``main()``.

Run from the project root:

    python run_e2e.py
"""
import sys
import shutil
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

# 1. Inject mocks for optional third-party libs that aren't installed.
for _name in ('tushare', 'ffn', 'talib', 'mplfinance',
              'mplfinance.original_flavor',
              'data', 'data.private'):
    sys.modules.setdefault(_name, mock.MagicMock())
_token = mock.MagicMock()
_token.tushare_token = 'TEST_TOKEN'
sys.modules['data.private.tushare_token'] = _token

# 2. Resolve project root.
PROJ = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJ))

import yaml  # noqa: E402

with open(PROJ / 'conf' / 'double_ma.yaml', 'r', encoding='utf-8') as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)
stock_lst = cfg['data_condition']['stock_lst']
benchmark = cfg['data_condition']['benchmark']

# 3. Build synthetic market data.
n = 60
dates = pd.date_range('2022-01-01', periods=n, freq='D').strftime('%Y%m%d')
df_dict = {benchmark: pd.DataFrame({
    'trade_date': dates, 'close': np.linspace(3000, 3200, n),
    'pct_chg': np.zeros(n),
})}
for i, code in enumerate(stock_lst):
    slope = 0.05 if i == 0 else -0.03
    base = np.linspace(10 + i * 5, 10 + i * 5 + slope * n, n)
    df_dict[code] = pd.DataFrame({
        'trade_date': dates,
        'open': base, 'high': base * 1.02, 'low': base * 0.98,
        'close': base, 'vol': np.ones(n) * 1_000_000,
    })


class FakeTuShareData:
    def __init__(self):
        pass
    def get_df_data(self, *a, **kw):
        return df_dict


# 4. Patch TuShareData at the call site + suppress plotting.
exp_dir = PROJ / 'exp_e2e'
if exp_dir.exists():
    shutil.rmtree(exp_dir)
exp_dir.mkdir()

import back_tester  # noqa: E402


def _main():
    args = back_tester.get_args()
    args.config = str(PROJ / 'conf' / 'double_ma.yaml')
    args.data_dir = str(PROJ / 'data_e2e')
    args.exp_dir = str(exp_dir)
    args.override_config = []
    back_tester.BackTester(args).offline_back_test_ctrl()


with mock.patch('back_tester.TuShareData', FakeTuShareData), \
     mock.patch('back_tester.plot_trades_on_capital'), \
     mock.patch('back_tester.plot_trades_on_k_line'), \
     mock.patch('back_tester.show_plt'):
    _main()

# 5. Validate output.
risk_csv = exp_dir / 'risk_indicator.csv'
trading_csv = exp_dir / 'trading_info.csv'
assert risk_csv.exists(), f'missing {risk_csv}'
assert trading_csv.exists(), f'missing {trading_csv}'
print('E2E OK: back_tester.main() ran end-to-end.')
print('  risk_indicator.csv ->', risk_csv)
print('  trading_info.csv   ->', trading_csv)