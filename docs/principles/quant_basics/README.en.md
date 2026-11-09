# Quantitative research course

The goal is to read strategy, backtest and risk results critically and identify their evidence and limits. Basic arithmetic is sufficient to start; learn statistics and programming alongside the lessons. This is an educational course, not investment advice. All numerical examples are synthetic.

## Learning path

Begin with research questions, instruments and data. Continue with returns, statistics and factors, then signals, execution, allocation and models. Finish with rotation research and paper-trading review. The application's Learning Space provides chapter navigation and previous/next controls; the same lessons are available in MkDocs.

| Chapter | Question to answer |
| --- | --- |
| [01 Research](01_research.en.md) | How do hypotheses, validation and execution differ? |
| [02 Instruments](02_instruments.en.md) | Why are stocks, indexes and ETFs different? |
| [03 Data](03_data.en.md) | How do adjustments and historical membership affect a result? |
| [04 Returns](04_returns.en.md) | Why should returns be compounded? |
| [05 Statistics](05_statistics.en.md) | What can correlation and drawdown establish? |
| [06 Factors](06_factors.en.md) | How does IC differ from trading returns? |
| [07 Signals](07_signals.en.md) | How are trend, reversal and rotation rules defined? |
| [08 Execution](08_execution.en.md) | How are fills, costs and biases checked? |
| [09 Portfolio risk](09_portfolio.en.md) | How do target weights become actual positions? |
| [10 Models](10_models.en.md) | What makes a result out of sample? |
| [11 Rotation](11_rotation.en.md) | What historical evidence does a rotation universe require? |
| [12 Operations](12_operations.en.md) | Does successful paper trading imply live readiness? |

## A minimal synthetic study

At time t, compare the previous 20 trading days of returns for three assets. Hold equal weights in assets with positive returns and attempt execution at t+1. If none qualifies, hold cash. Retain the universe available at the decision time, input bars, signals, target weights, orders, fills and costs. Check selection and actual purchases separately.

## Pitfalls and exercise

A strong return does not establish a hypothesis. A completed task does not establish historical coverage, and mock mode is not real market data. Check definitions before increasing algorithmic complexity.

**Exercise:** Can a NAV screenshot without instruments, dates or trade records reproduce a study?

**Answer:** No. At minimum retain data source, availability times, adjustments, parameters and versions, requested and actual dates, benchmark, orders, fills and costs. The next chapter organizes these into a research process.
