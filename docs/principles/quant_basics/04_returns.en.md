# 04 Returns, compounding and benchmarks

**Goal:** Compare net returns over consistent periods. Prerequisite: [data timing](03_data.en.md).

## Formulas

Simple return r = ending value / starting value - 1. Cumulative return = product of (1+r) - 1; returns across periods cannot simply be added. Annualized return = (ending / starting value)^(annual trading days / actual trading days) - 1. State the calendar, period and cash-flow treatment. Annualizing a short sample magnifies it and does not predict a full future year.

Match benchmarks to universe, currency, exposure, dates and adjustments. Excess return may mean a return difference or relative NAV growth; specify which. Deposits and withdrawals require time-weighted or money-weighted methods rather than a simple ending/starting balance ratio.

## Synthetic example

Starting with 100, a 10% gain produces 110, followed by a 10% loss producing 99. The cumulative return is -1%, not zero. Strategy and benchmark returns of 8% and 6% differ by 2 percentage points; relative NAV growth is 1.08 / 1.06 - 1, approximately 1.89%.

## Pitfalls

Do not omit commissions, slippage and tax from a gross-return display. Align strategy and benchmark coverage. Unfilled target returns are not account returns. Treat open positions and final liquidation fees consistently.

## Exercise and answer

**Exercise:** What gain recovers a 20% loss?

**Answer:** A value of 100 falls to 80; recovering requires 100/80 - 1 = 25%. This illustrates why losses and compounding matter.
