# 依赖升级日志（Dependency Upgrade Log）

> Track record of dependency and toolchain changes that affect end users.
> 本文档记录影响最终用户的依赖与工具链变更，由 README「🔐 Dependency Upgrade Log」章节迁移而来。

## Why this section exists

To stay compatible with the latest AI / RL / LLM ecosystem and to clear
the 46 GitHub Dependabot security alerts flagged in Sep 2026, we rolled
out a coordinated upgrade in [PR #25](https://github.com/charliedream1/ai_quant_trade/pull/25)
and the follow-up [PR #43](https://github.com/charliedream1/ai_quant_trade/pull/43).
All upgraded projects were end-to-end verified before merge.

## 2026-10-01 — Major upgrade (CVE sweep + gym migration)

| Project | Package | Before | After | Reason |
|---|---|---|---|---|
| `egs_trade/rl/a001_proto_sb3` | `torch` | 1.13.1 | 2.7.1 | Critical CVE-2024-31580 (torch.load RCE) |
| `egs_trade/rl/a001_proto_sb3` | `stable-baselines3` | 1.6.2 | 2.5.0 | SB3 ≥2.0 uses `gymnasium` natively |
| `egs_trade/rl/a001_proto_sb3` | `gym` | 0.21 | **removed** | Replaced by `gymnasium` 0.29.1 |
| `egs_trade/rl/a001_proto_sb3` | `gymnasium` | — | 0.29.1 | New dependency |
| `egs_trade/rl/a002_finRL_tutorial` | `torch` | 1.13.1 | 2.7.1 | Critical CVE-2024-31580 |
| `egs_trade/rl/a002_finRL_tutorial` | `stable-baselines3` | 1.7.0 | 2.5.0 | SB3 ≥2.0 uses `gymnasium` natively |
| `egs_trade/rl/a002_finRL_tutorial` | `gymnasium` | — | 0.29.1 | New dependency |
| `egs_llm/.../a04_train` | `torch` | 2.4.0+cu121 | 2.7.1 | Moderate: unpickle / Improper Resource CVEs |
| `egs_llm/.../a04_train` | `transformers` | 4.51.3 | 4.56.2 | High: ReDoS, Trainer RCE |
| `egs_llm/.../a04_train` | `accelerate` | 1.6.0 | 1.10.1 | High: incomplete cleanup |
| `egs_llm/.../a04_train` | `protobuf` | 3.20.3 | 6.31.1 | High: heap overflow in decoder |
| All workflows | `actions/checkout` | v4 | v5 | Node.js 24 runtime |
| All workflows | `actions/setup-python` | v5 | v6 | Node.js 24 runtime |

## Migration notes for users

1. **`gym` → `gymnasium`**. Custom environments built on `gym` 0.21 must:
   - import `gymnasium as gym` and `from gymnasium import spaces`;
   - return `obs, reward, terminated, truncated, info` from `step()`;
   - return `obs, info` from `reset()` and accept a `seed=` kwarg;
   - rename `metadata = {'render.modes': [...]}` to `metadata = {'render_modes': [...]}`.
   See [`StockTradingEnv0.py`](../egs_trade/rl/a001_proto_sb3/src/rl/envs/StockTradingEnv0.py) for a worked example.

2. **Python 3.8 still supported**; 3.10+ should now install cleanly thanks to new wheels.

3. **Apple Silicon**: still prefer `conda create -n quant python=3.8` first.

## End-to-end verification

Each affected project ships a `run_e2e.py` smoke test:

```bash
# RL project (a001)
cd egs_trade/rl/a001_proto_sb3 && python run_e2e.py

# RL project (a002 / finRL tutorial)
cd egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018 && python run_e2e.py

# LLM project (a04 — needs GPU ≥16 GB)
cd egs_llm/a01_train/a01_unsloth_stock_forcaster/a04_train && python run_e2e.py
```

These scripts are the upgrade regression baseline and are re-run after every
dependency change to ensure the original examples still execute end-to-end.

## Keeping dependencies fresh

- [`.github/dependabot.yml`](../.github/dependabot.yml) — weekly scans for
  GitHub Actions + pip packages; safe-version PRs are opened automatically.
- [`.github/workflows/codeql.yml`](../.github/workflows/codeql.yml) — weekly
  CodeQL security + quality scan on `master`.
- See [Security tab](https://github.com/charliedream1/ai_quant_trade/security)
  for live alerts.
