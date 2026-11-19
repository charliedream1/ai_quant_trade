# 回测框架

[English](../en/03-backtesting-frameworks.md) | [中文](../zh/03-backtesting-frameworks.md) | [分类目录](README.md) | [语言入口](../README.md)

## 股票

- **[backtrader](https://github.com/mementum/backtrader)** — Python 回测库，文档与教程丰富，采用 GPL-3.0 许可证。
  - 元数据： 语言： Python · 星标数： 23,392 · 许可证： GPL-3.0 · 维护状态： 近期维护 (最近推送 2024-08-20)
  - 文档／主页： https://www.backtrader.com
  - 使用点评：可用于可复现的策略回放；采用前需确认兼容性与数据模型。
  - 教程：[learn_backtrader](https://github.com/jrothschild33/learn_backtrader)（7 课）、[QuantWorld2022/backtrader](https://github.com/QuantWorld2022/backtrader)（8 课）
  - 界面：[backtrader-pyqt-ui](https://github.com/Skinok/backtrader-pyqt-ui)（非官方，MIT）

- **[pyalgotrade](https://github.com/gbeced/pyalgotrade)** — Python 事件驱动回测框架；pyalgotrade-cn 集成了 Tushare 实时行情。
  - 元数据： 语言： Python · 星标数： 4,675 · 许可证： 其他／自定义 · 维护状态： 已归档 (最近推送 2023-11-13)
  - 文档／主页： http://gbeced.github.io/pyalgotrade/
  - 使用点评：可用于可复现的策略回放；采用前需确认兼容性与数据模型。

- **[quantdigger](https://github.com/QuantFans/quantdigger)** — 基于 Python 的量化回测框架。
  - 元数据： 语言： Python · 星标数： 1,815 · 许可证： 未注明 · 维护状态： 不活跃 (最近推送 2020-05-02)
  - 文档／主页： -
  - 使用点评：可用于可复现的策略回放；采用前需确认兼容性与数据模型。

- **[rqalpha](https://github.com/ricequant/rqalpha)** — 可扩展、可替换的 Python 回测引擎。
  - 元数据： 语言： Python · 星标数： 6,809 · 许可证： 其他／自定义 · 维护状态： 活跃 (最近推送 2026-09-28)
  - 文档／主页： https://rqalpha.readthedocs.io/zh-cn/latest/
  - 使用点评：可用于可复现的策略回放；采用前需确认兼容性与数据模型。

- **[zipline](https://github.com/quantopian/zipline)** — Quantopian 开发的知名免费回测框架，聚宽与优矿基于其构建，采用 Apache-2.0 许可证。
  - 元数据： 语言： Python · 星标数： 20,138 · 许可证： APACHE-2.0 · 维护状态： 近期维护 (最近推送 2024-02-13)
  - 文档／主页： https://www.zipline.io
  - 使用点评：可用于可复现的策略回放；采用前需确认兼容性与数据模型。

- **[backtesting.py](https://github.com/kernc/backtesting.py)** — 轻量级 Python 回测框架，提供简洁的策略类、优化辅助工具和浏览器图表。
  - 元数据： 语言： Python · 星标数： 9,033 · 许可证： AGPL-3.0 · 维护状态： 活跃 (最近推送 2026-08-05)
  - 文档／主页： https://kernc.github.io/backtesting.py/
  - 使用点评：适合快速构建回测原型；嵌入商业系统前应审查 AGPL 许可要求。

- **[vectorbt](https://github.com/polakowo/vectorbt)** — 基于 NumPy/Pandas 的向量化回测与研究引擎，可快速测试大量参数组合。
  - 元数据： 语言： Python · 星标数： 9,333 · 许可证： 其他／自定义 · 维护状态： 活跃 (最近推送 2026-10-10)
  - 文档／主页： https://vectorbt.dev
  - 使用点评：擅长大规模参数扫描与因子研究，相对不适合模拟券商执行细节。

## 基金

- **[xalpha](https://github.com/refraction-ray/xalpha)** — 基金投资管理与回测引擎，涵盖净值获取、账户记录分析、策略回测与定时提醒。
  - 元数据： 语言： Python · 星标数： 2,719 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-07-25)
  - 文档／主页： https://xalpha.readthedocs.io
  - 使用点评：可用于可复现的策略回放；采用前需确认兼容性与数据模型。

## 事件驱动与多资产

- **[NautilusTrader](https://github.com/nautechsystems/nautilus_trader)** — 面向生产环境、以 Rust 原生实现的事件驱动交易引擎，提供 Python 接口，支持跨交易场所回测与实盘。
  - 元数据： 语言： Rust · 星标数： 29,839 · 许可证： LGPL-3.0 · 维护状态： 活跃 (最近推送 2026-10-11)
  - 文档／主页： https://nautilustrader.io
  - 使用点评：适合需要同一引擎同时支持高保真回测与实盘执行的场景。

## 其他回测框架

- **[fastquant](https://github.com/enzoampil/fastquant)** · MIT — 仅需 3 行代码即可回测和优化策略，使用美国市场数据。
  - 元数据： 语言： Jupyter Notebook · 星标数： 1,717 · 许可证： MIT · 维护状态： 较久未更新 (最近推送 2023-09-15)
  - 文档／主页： -
  - 使用点评：可作为回测框架层的候选资源；生产采用前需验证适配性。

- **[bt](https://github.com/pmorissette/bt)** — 基于 ffn 的灵活回测框架。
  - 元数据： 语言： Python · 星标数： 2,993 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-10-03)
  - 文档／主页： http://pmorissette.github.io/bt
  - 使用点评：可作为回测框架层的候选资源；生产采用前需验证适配性。

- **[QUANTAXIS](https://github.com/yutiansut/QUANTAXIS)** — 涵盖数据、回测、模拟、实盘与可视化。
  - 元数据： 语言： Python · 星标数： 11,259 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-09-18)
  - 文档／主页： https://yutiansut.github.io/QUANTAXIS/
  - 使用点评：可作为回测框架层的候选资源；生产采用前需验证适配性。

- **[hikyuu](https://github.com/fasiondog/hikyuu)** — C++/Python 量化框架，速度快且持续维护。
  - 元数据： 语言： C++ · 星标数： 3,544 · 许可证： APACHE-2.0 · 维护状态： 活跃 (最近推送 2026-10-04)
  - 文档／主页： http://hikyuu.org/
  - 使用点评：可作为回测框架层的候选资源；生产采用前需验证适配性。

- **[zvt](https://github.com/zvtvz/zvt)** — 模块化量化框架，旧仓库为 [fooltrader](https://github.com/zvtvz/zvt)。
  - 元数据： 语言： Python · 星标数： 4,310 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-07-01)
  - 文档／主页： https://zvt.readthedocs.io/en/latest/
  - 使用点评：可作为回测框架层的候选资源；生产采用前需验证适配性。

- **[qtrader](https://github.com/josephchenhk/qtrader)** — 轻量级事件驱动算法交易引擎。
  - 元数据： 语言： Python · 星标数： 547 · 许可证： 未注明 · 维护状态： 活跃 (最近推送 2026-09-07)
  - 文档／主页： -
  - 使用点评：可作为回测框架层的候选资源；生产采用前需验证适配性。

- **[abu](https://github.com/bbfamily/abu)** — 阿布量化交易系统，提供桌面与移动端应用，并结合机器学习。
  - 元数据： 语言： Python · 星标数： 18,566 · 许可证： GPL-3.0 · 维护状态： 活跃 (最近推送 2026-01-24)
  - 文档／主页： http://www.abuquant.com/
  - 使用点评：可作为回测框架层的候选资源；生产采用前需验证适配性。
