# -*- coding: utf-8 -*-
"""Unit + e2e tests for refactored egs_trade/rl/a001_proto_sb3."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ))

from src.rl.envs.StockTradingEnv0 import StockTradingEnv
from src.tools.file_io.find_files import find_file


def _make_df(n=50):
    rng = np.random.default_rng(0)
    base = np.cumsum(rng.normal(0, 1, n)) + 100
    df = pd.DataFrame({
        'date': pd.date_range('2022-01-01', periods=n, freq='D'),
        'open': base,
        'high': base + 1,
        'low': base - 1,
        'close': base,
        'volume': rng.integers(1_000_000, 5_000_000, n),
        'amount': rng.integers(1e8, 5e8, n),
        'adjustflag': np.ones(n),
        'tradestatus': np.ones(n),
        'pctChg': rng.normal(0, 0.02, n),
        'peTTM': rng.uniform(5, 30, n),
        'pbMRQ': rng.uniform(0.5, 5, n),
        'psTTM': rng.uniform(1, 8, n),
    })
    return df.sort_values('date').reset_index(drop=True)


class TestStockTradingEnv:
    def test_env_reset_returns_observation(self):
        df = _make_df(30)
        env = StockTradingEnv(df, 10000)
        obs, info = env.reset(seed=0)
        assert obs.shape == (19,)
        # observations are roughly normalized, allow tiny float drift around 0
        assert np.all(obs >= -1e-3) and np.all(obs <= 1.0 + 1e-3)
        assert isinstance(info, dict)

    def test_env_step_returns_correct_tuple(self):
        df = _make_df(20)
        env = StockTradingEnv(df, 10000)
        env.reset(seed=0)
        action = np.array([0.5, 0.5], dtype=np.float16)
        obs, reward, terminated, truncated, info = env.step(action)
        assert obs.shape == (19,)
        assert reward in (1, -100)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert info == {}

    def test_env_can_run_a_few_steps(self):
        df = _make_df(40)
        env = StockTradingEnv(df, 10000)
        env.reset(seed=0)
        for _ in range(10):
            action = np.array([1.0, 0.5], dtype=np.float16)
            obs, reward, terminated, truncated, _ = env.step(action)
            if terminated or truncated:
                break
        assert env.render() is not None


class TestFindFile:
    def test_find_existing_file(self, tmp_path):
        (tmp_path / 'sub').mkdir()
        target = tmp_path / 'sub' / '600036.csv'
        target.write_text('a,b\n1,2\n')
        assert find_file(str(tmp_path), '600036') == str(target)

    def test_missing_file_returns_none(self, tmp_path):
        assert find_file(str(tmp_path), 'no_such') is None


class TestE2ERL:
    def test_ppo_can_learn_a_few_steps(self, tmp_path):
        pytest.importorskip('stable_baselines3')
        from stable_baselines3.common.vec_env import DummyVecEnv
        from stable_baselines3 import PPO
        from stable_baselines3.ppo.policies import MlpPolicy

        df = _make_df(120)
        env = DummyVecEnv([lambda: StockTradingEnv(df, 10000)])
        model = PPO(MlpPolicy, env, verbose=0)
        model.learn(total_timesteps=64)  # tiny budget; only verifies the loop runs
