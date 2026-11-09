# 01 Research process and hypotheses

**Goal:** Turn investment intuition into a falsifiable question. Prerequisite: [course introduction](README.en.md).

## Concepts and process

A hypothesis specifies the universe, observation period, available information, trading rule and failure criteria. “Assets that rose over the previous 20 days perform better over the following 5 days” is more testable than “the model predicts markets.” Define samples and benchmarks before cleaning data, generating signals, allocating capital, charging execution costs and evaluating out-of-sample results.

Research, paper trading and live trading provide different evidence. Research tests rules; paper trading checks operations and orders. Live execution additionally depends on broker capabilities, applicable rules and actual market impact. Simple strategies and graph compositions share a backtest entry but use different engines.

## Synthetic example

A rule returns 12% in training, 2% in validation and -3% out of sample. Equal-weight benchmarks return 10%, 3% and -1%. Out-of-sample excess return is -3% - (-1%) = -2 percentage points. Reporting only the 12% training return does not establish effectiveness.

## Pitfalls

Testing many parameters and reporting only the winner creates selection bias. Changing the universe, dates and parameters together obscures the cause of an improvement. Define evaluation and stopping rules first, and retain failed experiments.

## Exercise and answer

**Exercise:** After 100 parameter trials, may the best profitable in-sample configuration go straight to production?

**Answer:** No. Record the search count, validate chronologically and on untouched data, then check costs, stability and paper execution. Results support a conditional hypothesis, not a promise of returns.
