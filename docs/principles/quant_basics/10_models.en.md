# 10 Small models and out-of-sample tests

**Goal:** Train and evaluate financial time series correctly. Prerequisites: [data](03_data.en.md), [factors](06_factors.en.md).

## Concepts

Linear models, trees and small neural networks map features to return forecasts, probabilities or ranks. Complexity is one dimension; data quality, label timing and execution constraints are often more important. Fix the prediction task, training window, feature availability and refresh frequency.

Split training, validation and test chronologically. Fit normalization, imputation and feature selection only on training data. Isolate overlapping multi-day labels at boundaries. Each rolling validation uses only labels matured before its decision date.

## Formula and synthetic examples

Mean squared error averages (prediction - outcome)². Predictions of 2% and 0% against outcomes of 1% and 1% yield MSE = 0.0001. Low prediction error does not guarantee profits after costs.

Train January–June, validate July–August and test September–October. If test results influence parameter selection, that interval becomes part of tuning: reserve another untouched sample or label the exercise retrospective.

## Pitfalls

Shuffling all dates, normalizing the complete dataset, reporting only the best model and omitting seeds/versions undermine reproducibility. Fluent Agent explanations are not predictive evidence; inspect citations, out-of-sample results and execution risk.

## Exercise and answer

**Exercise:** Does annual-mean normalization followed by first-half training leak information?

**Answer:** Yes. Second-half information enters the earlier transformation. Fit on training data, apply unchanged to later periods, and keep rolling transforms causal.
