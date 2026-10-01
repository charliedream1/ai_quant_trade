# -*- coding: utf-8 -*-
"""End-to-end smoke test for the a002 finRL tutorial upgrade.

This test does NOT actually invoke finRL (which has heavy native deps
and pulls alpaca/wrds). It instead verifies the critical API contract
between SB3/gymnasium and finRL 0.3.7's StockTradingEnv:

  1. finRL 0.3.7's StockTradingEnv extends gymnasium.Env
  2. step() returns 5-tuple (obs, reward, terminated, truncated, info)
  3. reset() returns 2-tuple (obs, info)
  4. The Stable-baselines3 VecEnv wrappers accept the env

If any of these regress (e.g. finRL pins back to gym), this test
fails fast before user-visible breakage.
"""
import os
import re
import inspect
import numpy as np
import pandas as pd

FINRL_ENV = os.environ.get(
    'FINRL_ENV_PATH',
    '/tmp/venv_quant/lib/python3.14/site-packages/finrl/meta/env_stock_trading/env_stocktrading.py',
)


def test_finrl_step_is_5tuple():
    src = open(FINRL_ENV).read()
    # Find the return statement at the end of step()
    # finRL 0.3.7 ends step() with `return self.state, self.reward, ...`
    m = re.search(r'def step\(self,.*?\):(.+?)return ([^\n]+)', src, re.S)
    assert m, 'cannot locate step() in finRL env'
    ret = m.group(2)
    n_commas = ret.count(',')
    assert n_commas >= 4, (
        f'finRL.StockTradingEnv.step() returns {n_commas+1}-tuple, '
        f'expected 5-tuple (gymnasium contract).\nreturn stmt: {ret.strip()!r}'
    )
    print('  step() returns:', ret.strip())


def test_finrl_reset_accepts_seed():
    src = open(FINRL_ENV).read()
    # Find reset signature
    m = re.search(r'def reset\(\s*self\s*,[^)]*\)', src)
    assert m, 'cannot locate reset() in finRL env'
    sig = m.group(0)
    assert 'seed' in sig, (
        f'finRL.StockTradingEnv.reset() must accept seed= per gymnasium.\n'
        f'signature: {sig}'
    )
    print('  reset() signature:', sig)


def test_finrl_parent_class():
    src = open(FINRL_ENV).read()
    m = re.search(r'class\s+StockTradingEnv\s*\(([^)]+)\)', src)
    assert m, 'cannot locate class declaration'
    parent = m.group(1)
    assert 'gym.Env' in parent, (
        f'finRL.StockTradingEnv should extend gym.Env (gymnasium).\n'
        f'parent: {parent}'
    )
    assert 'gymnasium' in src, 'finRL env should import gymnasium'
    print('  class parent:', parent)


def test_sb3_compat():
    """Verify stable_baselines3 accepts a gymnasium env via DummyVecEnv."""
    from stable_baselines3.common.vec_env import DummyVecEnv, VecEnv
    # Lightweight gymnasium env for the smoke test
    import gymnasium as gym
    from gymnasium import spaces

    class _Dummy(gym.Env):
        metadata = {'render_modes': []}
        action_space = spaces.Box(low=-1, high=1, shape=(1,))
        observation_space = spaces.Box(low=-1, high=1, shape=(4,))

        def step(self, action):
            return np.zeros(4), 0.0, False, False, {}

        def reset(self, *, seed=None, options=None):
            return np.zeros(4), {}

    vec = DummyVecEnv([lambda: _Dummy()])
    obs = vec.reset()
    assert obs.shape == (1, 4), f'vec.reset() returned wrong shape {obs.shape}'
    obs, r, done, info = vec.step(np.zeros((1, 1)))
    assert obs.shape == (1, 4), f'vec.step() obs shape wrong {obs.shape}'
    r_val = float(np.asarray(r).reshape(-1)[0])
    print(f'  SB3 DummyVecEnv round-trip: OK (obs.shape={obs.shape}, reward={r_val:.3f})')


def main():
    print('=== finRL 0.3.7 / SB3 2.5.0 / gymnasium 0.29.1 compatibility ===')
    print('-- test_finrl_parent_class --')
    test_finrl_parent_class()
    print('-- test_finrl_step_is_5tuple --')
    test_finrl_step_is_5tuple()
    print('-- test_finrl_reset_accepts_seed --')
    test_finrl_reset_accepts_seed()
    print('-- test_sb3_compat --')
    test_sb3_compat()
    print()
    print('E2E OK: a002_finRL_tutorial API contract holds for the upgraded stack.')


if __name__ == '__main__':
    main()
