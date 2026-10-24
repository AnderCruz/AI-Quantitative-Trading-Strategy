# Drawdown Methodology

## Purpose

This document defines the drawdown measures used in the historical
comparison of candidate equities.

The analysis uses adjusted closing prices from the locally stored
Yahoo Finance dataset.

## Period Maximum Drawdown

Period maximum drawdown measures the largest decline from a running
peak observed within the selected analysis period.

For each observation, the running peak is calculated using prices
from the beginning of the selected period up to the current date.

The period maximum drawdown is the minimum drawdown observed within
that period.

This measure is used to compare the severity of declines occurring
inside each historical window.

## Historical Maximum Drawdown Within a Period

Historical maximum drawdown within a period uses the full available
price history up to each observation, including observations before
the selected period begins.

For each date, the historical peak is the maximum adjusted closing
price observed from the beginning of the available dataset up to that
date.

The reported metric is the minimum historical drawdown observed
during the selected period.

This measure provides context about how far the asset remained below
a peak established earlier in its history.

It is not the maximum drawdown of the entire dataset unless the
selected period covers the entire dataset.

## Price Series

Both measures are calculated using adjusted closing prices
(`Adj Close`).

The resulting drawdowns describe the adjusted price series and should
not be interpreted as drawdowns calculated from unadjusted execution
prices.

## Limitations

- Historical drawdowns describe past price behaviour and do not
  predict future losses.
- The selected periods are exploratory windows rather than formally
  identified market regimes.
- These measures do not include strategy-specific entry and exit
  rules, transaction costs, slippage, or position sizing.
- Historical drawdowns of an individual asset are not equivalent to
  portfolio drawdowns.
