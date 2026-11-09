# 03 Market data and information timing

**Goal:** Separate what is known today from what was known then. Prerequisite: [instruments](02_instruments.en.md).

## Concepts

OHLCV means open, high, low, close and volume. A trading calendar excludes market holidays; weekdays alone are insufficient. Missing bars can reflect listing dates, suspensions or provider failures. Do not fill every gap with a zero price.

Adjustments handle distributions and splits, but their factors and dates affect reproducibility. Define signal prices separately from execution prices. Point-in-time information must have been available at the decision time; a financial period end is not the publication date. Using today's index members throughout history creates survivorship bias.

## Synthetic example

An asset closes at 100 on July 1, then splits to a price of 50 with twice as many shares on July 2. The raw price change is -50%, but value has not halved. Another asset is suspended on July 2: neither a zero price nor an executable order is justified.

## Pitfalls

Requesting January through June differs from receiving January 21 through June 30. Fetching the latest 120 bars and then filtering dates does not guarantee historical coverage. Retain requested and actual dates and coverage evidence; explain gaps rather than claiming completion.

## Exercise and answer

**Exercise:** Is a missing Saturday bar a data gap? May an unversioned constituent list be called a historical index universe?

**Answer:** First check whether that market traded on the Saturday; a scheduled closure is not a gap. Without historical membership evidence, describe the list as current rather than historical.
