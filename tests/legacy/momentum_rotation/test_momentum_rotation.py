import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml

from egs_trade.vanilla.momentum_rotation.data import (
    normalize_trade_dates,
    select_tushare_universe,
)
from egs_trade.vanilla.momentum_rotation.run_backtest import run_from_config
from egs_trade.vanilla.momentum_rotation.strategy import (
    MomentumRotationBacktester,
    StrategyParams,
    TradingCost,
)


def write_fixture_config(config_path, fixture_dir):
    config = {
        "data": {
            "source": "csv",
            "csv_dir": str(fixture_dir),
            "start_date": "2023-01-02",
            "end_date": "2023-03-02",
            "benchmark": "000300.SH",
        },
        "split": {
            "train_start": "2023-01-02",
            "train_end": "2023-02-01",
            "test_start": "2023-02-02",
            "test_end": "2023-03-02",
        },
        "strategy": {
            "initial_cash": 100000,
            "lookback_windows": [2],
            "momentum_weights": [1.0],
            "trend_windows": [],
            "volatility_window": 2,
            "volatility_penalty": 0.0,
            "min_avg_amount": 0.0,
            "liquidity_window": 1,
        },
        "parameter_grid": {
            "top_n": [1, 2],
            "trailing_stop": [0.10],
            "market_filter_enabled": [False],
        },
        "order_cost": {
            "open_commission": 0.0,
            "close_commission": 0.0,
            "close_tax": 0.0,
            "min_commission": 0.0,
            "slippage_bps": 0.0,
        },
        "report": {"save_plots": True},
    }
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")


def make_panel(dates, price_by_code, amount=100000000.0):
    rows = []
    for code, prices in price_by_code.items():
        for trade_date, close in zip(dates, prices, strict=True):
            rows.append({
                "ts_code": code,
                "trade_date": trade_date,
                "open": close,
                "high": close * 1.02,
                "low": close * 0.98,
                "close": close,
                "vol": 1000000.0,
                "amount": amount,
            })
    return pd.DataFrame(rows)


class MomentumRotationStrategyTest(unittest.TestCase):
    def test_tushare_stock_list_skips_stock_basic_call(self):
        class ExplodingPro:
            def stock_basic(self, *args, **kwargs):
                raise AssertionError("stock_basic should not be called")

        with tempfile.TemporaryDirectory() as tmp:
            stock_basic_path = Path(tmp) / "stock_basic.csv"

            stock_basic, codes = select_tushare_universe(
                ExplodingPro(),
                stock_list=["000001.SZ", "600000.SH"],
                stock_basic_path=stock_basic_path,
            )

            self.assertEqual(["000001.SZ", "600000.SH"], codes)
            self.assertEqual(["000001.SZ", "600000.SH"], stock_basic["ts_code"].tolist())
            self.assertTrue(stock_basic_path.exists())

    def test_normalize_tushare_numeric_trade_dates(self):
        df = pd.DataFrame({
            "ts_code": ["AAA"],
            "trade_date": [20230102],
            "open": [10],
            "high": [11],
            "low": [9],
            "close": [10],
            "vol": [1],
            "amount": [1],
        })

        normalized = normalize_trade_dates(df)

        self.assertEqual(pd.Timestamp("2023-01-02"), normalized["trade_date"].iloc[0])

    def test_monthly_rebalance_uses_previous_day_scores(self):
        dates = pd.bdate_range("2023-01-24", "2023-02-03").strftime("%Y-%m-%d").tolist()
        data = make_panel(dates, {
            "AAA": [10, 11, 12, 13, 14, 15, 16, 17, 18],
            "BBB": [10, 10, 10, 10, 10, 10, 30, 31, 32],
        })
        params = StrategyParams(
            initial_cash=100000.0,
            top_n=1,
            lookback_windows=(2,),
            momentum_weights=(1.0,),
            trend_windows=(),
            volatility_window=2,
            volatility_penalty=0.0,
            min_avg_amount=0.0,
            liquidity_window=1,
            trailing_stop=0.20,
            market_filter_enabled=False,
        )

        result = MomentumRotationBacktester(data, params=params, cost=TradingCost()).run(
            start_date="2023-02-01",
            end_date="2023-02-03",
        )

        first_buys = result.trades[result.trades["side"] == "buy"]
        self.assertEqual(["AAA"], first_buys["ts_code"].tolist())

    def test_top_n_positions_and_exposure_are_capped(self):
        dates = pd.bdate_range("2023-01-24", "2023-02-03").strftime("%Y-%m-%d").tolist()
        data = make_panel(dates, {
            "AAA": [10, 11, 12, 13, 14, 15, 16, 17, 18],
            "BBB": [10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5, 14],
            "CCC": [10, 9.9, 10, 9.8, 10, 9.7, 10, 9.6, 10],
        })
        params = StrategyParams(
            initial_cash=100000.0,
            top_n=2,
            lookback_windows=(2,),
            momentum_weights=(1.0,),
            trend_windows=(),
            volatility_window=2,
            volatility_penalty=0.0,
            min_avg_amount=0.0,
            liquidity_window=1,
            trailing_stop=0.20,
            market_filter_enabled=False,
        )

        result = MomentumRotationBacktester(data, params=params, cost=TradingCost()).run(
            start_date="2023-02-01",
            end_date="2023-02-03",
        )

        self.assertLessEqual(result.equity_curve["gross_exposure"].max(), 1.000001)
        bought_codes = result.trades[result.trades["side"] == "buy"]["ts_code"].tolist()
        self.assertEqual(["AAA", "BBB"], bought_codes)

    def test_trailing_stop_exits_without_capping_winners(self):
        dates = pd.bdate_range("2023-01-02", "2023-01-13").strftime("%Y-%m-%d").tolist()
        data = make_panel(dates, {
            "AAA": [10, 11, 12, 14, 16, 20, 19, 17, 17, 17],
        })
        params = StrategyParams(
            initial_cash=100000.0,
            top_n=1,
            lookback_windows=(2,),
            momentum_weights=(1.0,),
            trend_windows=(),
            volatility_window=2,
            volatility_penalty=0.0,
            min_avg_amount=0.0,
            liquidity_window=1,
            trailing_stop=0.10,
            market_filter_enabled=False,
        )

        result = MomentumRotationBacktester(data, params=params, cost=TradingCost()).run(
            start_date="2023-01-05",
            end_date="2023-01-13",
        )

        sells = result.trades[result.trades["side"] == "sell"]
        self.assertIn("trailing_stop", sells["reason"].tolist())
        buy_date = result.trades[result.trades["side"] == "buy"]["trade_date"].iloc[0]
        sell_date = sells[sells["reason"] == "trailing_stop"]["trade_date"].iloc[0]
        self.assertGreater(pd.Timestamp(sell_date), pd.Timestamp(buy_date))

    def test_transaction_costs_reduce_final_equity(self):
        dates = pd.bdate_range("2023-01-24", "2023-02-03").strftime("%Y-%m-%d").tolist()
        data = make_panel(dates, {
            "AAA": [10, 11, 12, 13, 14, 15, 16, 17, 18],
            "BBB": [10, 10, 10, 10, 10, 10, 10, 10, 10],
        })
        params = StrategyParams(
            initial_cash=100000.0,
            top_n=1,
            lookback_windows=(2,),
            momentum_weights=(1.0,),
            trend_windows=(),
            volatility_window=2,
            volatility_penalty=0.0,
            min_avg_amount=0.0,
            liquidity_window=1,
            trailing_stop=0.20,
            market_filter_enabled=False,
        )

        no_cost = MomentumRotationBacktester(data, params=params, cost=TradingCost()).run(
            start_date="2023-02-01",
            end_date="2023-02-03",
        )
        with_cost = MomentumRotationBacktester(
            data,
            params=params,
            cost=TradingCost(open_commission=0.001, close_commission=0.001, min_commission=5.0),
        ).run(start_date="2023-02-01", end_date="2023-02-03")

        self.assertLess(
            with_cost.equity_curve["equity"].iloc[-1],
            no_cost.equity_curve["equity"].iloc[-1],
        )

    def test_csv_fixture_smoke_outputs_reports_without_tushare_token(self):
        fixture_dir = Path(__file__).parent / "fixtures" / "momentum_rotation"
        with tempfile.TemporaryDirectory() as tmp:
            exp_dir = Path(tmp) / "exp"
            config_path = Path(tmp) / "momentum_rotation.yaml"
            write_fixture_config(config_path, fixture_dir)

            run_from_config(str(config_path), str(exp_dir))

            self.assertTrue((exp_dir / "leaderboard.csv").exists())
            self.assertTrue((exp_dir / "trades.csv").exists())
            self.assertTrue((exp_dir / "equity_curve.csv").exists())
            self.assertTrue((exp_dir / "equity_curve.png").exists())
            leaderboard = pd.read_csv(exp_dir / "leaderboard.csv")
            self.assertEqual(
                leaderboard["test_cagr"].tolist(),
                sorted(leaderboard["test_cagr"].tolist(), reverse=True),
            )

    def test_cli_runs_from_strategy_directory(self):
        repo_root = Path(__file__).resolve().parents[3]
        strategy_dir = repo_root / "egs_trade" / "vanilla" / "momentum_rotation"
        fixture_dir = Path(__file__).parent / "fixtures" / "momentum_rotation"
        with tempfile.TemporaryDirectory() as tmp:
            exp_dir = Path(tmp) / "exp"
            config_path = Path(tmp) / "momentum_rotation.yaml"
            write_fixture_config(config_path, fixture_dir)

            completed = subprocess.run(
                [
                    sys.executable,
                    "run_backtest.py",
                    "--config",
                    str(config_path),
                    "--exp_dir",
                    str(exp_dir),
                ],
                cwd=strategy_dir,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(
                0,
                completed.returncode,
                completed.stdout + completed.stderr,
            )
            self.assertTrue((exp_dir / "leaderboard.csv").exists())


if __name__ == "__main__":
    unittest.main()
