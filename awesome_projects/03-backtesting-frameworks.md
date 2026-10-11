# Backtesting Frameworks

## Stock

- **[backtrader](https://github.com/mementum/backtrader)** — Python backtesting library with rich docs and tutorials (GPL-3.0).
  - Metadata: Language: Python · Stars: 23,392 · License: GPL-3.0 · Maintenance: Recent (last push 2024-08-20)
  - Docs/Homepage: https://www.backtrader.com
  - Value: Useful for reproducible strategy replay; confirm compatibility and data model before adoption.
  - Tutorials: [learn_backtrader](https://github.com/jrothschild33/learn_backtrader) (7 lessons), [QuantWorld2022/backtrader](https://github.com/QuantWorld2022/backtrader) (8 lessons)
  - UI: [backtrader-pyqt-ui](https://github.com/Skinok/backtrader-pyqt-ui) (unofficial, MIT)

- **[pyalgotrade](https://github.com/gbeced/pyalgotrade)** — Event-driven backtesting framework in Python (pyalgotrade-cn integrates tushare for real-time quotes).
  - Metadata: Language: Python · Stars: 4,675 · License: Other/Custom · Maintenance: Archived (last push 2023-11-13)
  - Docs/Homepage: http://gbeced.github.io/pyalgotrade/
  - Value: Useful for reproducible strategy replay; confirm compatibility and data model before adoption.

- **[quantdigger](https://github.com/QuantFans/quantdigger)** — Python-based quant backtesting framework.
  - Metadata: Language: Python · Stars: 1,815 · License: Not specified · Maintenance: Inactive (last push 2020-05-02)
  - Docs/Homepage: -
  - Value: Useful for reproducible strategy replay; confirm compatibility and data model before adoption.

- **[rqalpha](https://github.com/ricequant/rqalpha)** — Extendable, replaceable Python backtesting engine.
  - Metadata: Language: Python · Stars: 6,809 · License: Other/Custom · Maintenance: Active (last push 2026-09-28)
  - Docs/Homepage: https://rqalpha.readthedocs.io/zh-cn/latest/
  - Value: Useful for reproducible strategy replay; confirm compatibility and data model before adoption.

- **[zipline](https://github.com/quantopian/zipline)** — Well-known free backtesting framework by Quantopian; JoinQuant/Uqer are built on it (Apache-2.0).
  - Metadata: Language: Python · Stars: 20,138 · License: APACHE-2.0 · Maintenance: Recent (last push 2024-02-13)
  - Docs/Homepage: https://www.zipline.io
  - Value: Useful for reproducible strategy replay; confirm compatibility and data model before adoption.

- **[backtesting.py](https://github.com/kernc/backtesting.py)** — Lightweight Python backtesting framework with concise strategy classes, optimization helpers and browser-based plots.
  - Metadata: Language: Python · Stars: 9,033 · License: AGPL-3.0 · Maintenance: Active (last push 2026-08-05)
  - Docs/Homepage: https://kernc.github.io/backtesting.py/
  - Value: Good fit for fast prototype backtests; AGPL licensing should be reviewed before embedding in commercial systems.

- **[vectorbt](https://github.com/polakowo/vectorbt)** — Vectorized backtesting and research engine for testing many parameter combinations quickly with NumPy/Pandas.
  - Metadata: Language: Python · Stars: 9,333 · License: Other/Custom · Maintenance: Active (last push 2026-10-10)
  - Docs/Homepage: https://vectorbt.dev
  - Value: Strong for large parameter sweeps and factor-style research; less natural for broker-execution simulation.

## Fund

- **[xalpha](https://github.com/refraction-ray/xalpha)** — Fund investment management & backtesting engine (NAV retrieval, account record analysis, strategy backtesting, scheduled reminders).
  - Metadata: Language: Python · Stars: 2,719 · License: MIT · Maintenance: Active (last push 2026-07-25)
  - Docs/Homepage: https://xalpha.readthedocs.io
  - Value: Useful for reproducible strategy replay; confirm compatibility and data model before adoption.

## Event-Driven / Multi-Asset

- **[NautilusTrader](https://github.com/nautechsystems/nautilus_trader)** — Production-grade Rust-native event-driven trading engine with Python bindings for backtesting and live trading across multiple venues.
  - Metadata: Language: Rust · Stars: 29,839 · License: LGPL-3.0 · Maintenance: Active (last push 2026-10-11)
  - Docs/Homepage: https://nautilustrader.io
  - Value: Strong candidate when the same engine must cover high-fidelity backtests and live execution.

## Additional Backtesting Frameworks

- **[fastquant](https://github.com/enzoampil/fastquant)** · MIT — Backtest & optimize strategies in 3 lines (US data).
  - Metadata: Language: Jupyter Notebook · Stars: 1,717 · License: MIT · Maintenance: Stale (last push 2023-09-15)
  - Docs/Homepage: -
  - Value: Useful as a shortlist source for the Backtesting Frameworks layer; verify fit before production adoption.

- **[bt](https://github.com/pmorissette/bt)** — Flexible backtesting (built on ffn).
  - Metadata: Language: Python · Stars: 2,993 · License: MIT · Maintenance: Active (last push 2026-10-03)
  - Docs/Homepage: http://pmorissette.github.io/bt
  - Value: Useful as a shortlist source for the Backtesting Frameworks layer; verify fit before production adoption.

- **[QUANTAXIS](https://github.com/yutiansut/QUANTAXIS)** — Data / backtest / simulation / live trading / visualization.
  - Metadata: Language: Python · Stars: 11,259 · License: MIT · Maintenance: Active (last push 2026-09-18)
  - Docs/Homepage: https://yutiansut.github.io/QUANTAXIS/
  - Value: Useful as a shortlist source for the Backtesting Frameworks layer; verify fit before production adoption.

- **[hikyuu](https://github.com/fasiondog/hikyuu)** — C++/Python quant framework (fast, active).
  - Metadata: Language: C++ · Stars: 3,544 · License: APACHE-2.0 · Maintenance: Active (last push 2026-10-04)
  - Docs/Homepage: http://hikyuu.org/
  - Value: Useful as a shortlist source for the Backtesting Frameworks layer; verify fit before production adoption.

- **[zvt](https://github.com/zvtvz/zvt)** — Modular quant framework (old repo: [fooltrader](https://github.com/zvtvz/zvt)).
  - Metadata: Language: Python · Stars: 4,310 · License: MIT · Maintenance: Active (last push 2026-07-01)
  - Docs/Homepage: https://zvt.readthedocs.io/en/latest/
  - Value: Useful as a shortlist source for the Backtesting Frameworks layer; verify fit before production adoption.

- **[qtrader](https://github.com/josephchenhk/qtrader)** — Lightweight event-driven algorithmic trading engine.
  - Metadata: Language: Python · Stars: 547 · License: Not specified · Maintenance: Active (last push 2026-09-07)
  - Docs/Homepage: -
  - Value: Useful as a shortlist source for the Backtesting Frameworks layer; verify fit before production adoption.

- **[abu](https://github.com/bbfamily/abu)** — Abu quant trading system (desktop + mobile app; ML-assisted).
  - Metadata: Language: Python · Stars: 18,566 · License: GPL-3.0 · Maintenance: Active (last push 2026-01-24)
  - Docs/Homepage: http://www.abuquant.com/
  - Value: Useful as a shortlist source for the Backtesting Frameworks layer; verify fit before production adoption.
