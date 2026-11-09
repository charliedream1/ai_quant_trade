# 07 Trend, reversal and rotation

**Goal:** Define explicit signals with decision times. Prerequisite: [factors](06_factors.en.md).

## Concepts

Trend rules assume persistence, reversal rules assume deviations revert, and rotation compares assets and reallocates capital. Their usefulness depends on regime and horizon; none is universally effective. Moving-average crossings, momentum rankings and deviation thresholds require explicit windows, triggers and holding periods.

Cascades progressively filter candidates, for example rules → model → Agent. Parallel branches score the same universe before aggregation on a common scale. Input/output types must agree: a score is not a position. Agent outputs require traceable evidence and portfolio, risk and execution constraints.

## Synthetic example

Two assets return 8% and -2% over the previous 20 days. “Buy the highest-ranked positive asset” selects the first; if both are negative, cash is a defined outcome. A signal confirmed at close t normally cannot be filled at the already-past open t.

## Pitfalls

Do not add scores with incompatible units, confuse similar-model votes with independent evidence, or force purchases after a cascade rejects every candidate. Version changes and retain stage relationships and rejection reasons.

## Exercise and answer

**Exercise:** Rules retain ten assets, the model retains three, and the Agent rejects all. What follows?

**Answer:** Apply the predefined empty-universe policy: cash or permitted existing holdings, with reasons recorded. Do not silently weaken thresholds to produce an answer.
