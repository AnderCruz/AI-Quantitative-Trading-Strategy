# Price Series Policy

**Project:** AI Quantitative Trading & Decision Intelligence System
**Status:** Approved methodology; implementation pending
**Language:** British English

## 1. Purpose

This document defines how raw and adjusted market-price series are to be used in the project, maintaining consistency between historical analysis, feature engineering, portfolio accounting, and simulated execution.

The policy applies to `data/processed/candidate_stocks_daily.csv`, covering AAPL, MSFT, NVDA, and TSLA.

## 2. Available fields

- Raw OHLC prices: `open`, `high`, `low`, `close`
- Adjusted OHLC prices: `adjOpen`, `adjHigh`, `adjLow`, `adjClose`
- Raw volume: `volume`
- Adjusted volume: `adjVolume`
- Cash dividends: `divCash`
- Split factor: `splitFactor`
- Identifiers: `date`, `ticker`

Adjusted values may be revised retrospectively following corporate actions. The provider's full adjustment methodology and the availability of point-in-time adjusted data have not yet been independently verified.

## 3. Policy by use case

| Use case | Preferred data | Policy |
|---|---|---|
| Historical price returns | `adjClose` | Calculate returns from a consistently adjusted closing-price series. |
| Historical volatility | Returns derived from `adjClose` | Use the same return convention throughout each analysis. |
| Moving averages and price-based indicators | Consistent adjusted price series | Avoid artificial discontinuities caused by stock splits. |
| OHLC technical indicators | `adjOpen`, `adjHigh`, `adjLow`, `adjClose` | Use adjusted OHLC fields together; do not mix raw and adjusted OHLC fields in one formula without explicit justification. |
| Volume-based indicators | `volume` or `adjVolume` | Choose according to the indicator definition and document the choice. Do not assume these fields must be equal. |
| Simulated order execution | Raw market prices, subject to an execution model | Use plausible executable prices, with transaction costs and execution assumptions modelled explicitly. |
| Position and portfolio accounting | Market prices and simulated share quantities | Apply corporate actions to positions and account for cash flows consistently. |
| Dividends | `divCash` and explicit accounting rules | Account for dividends according to the strategy and reported return metric. |
| Stock splits | `splitFactor` and explicit position-adjustment rules | Adjust simulated share quantities and prices consistently; do not treat a split as an investment loss or gain. |

## 4. Consistency rules

1. Do not combine raw and adjusted OHLC fields in the same calculation unless the calculation explicitly requires it and the rationale is documented.
2. Calculate historical returns using one consistently defined price series.
3. Do not remove extreme returns solely because they exceed a fixed threshold. Investigate suspected data errors and preserve genuine market movements.
4. Keep the source dataset unchanged during audits. Future transformations must be reproducible and written to a separately defined output.
5. Record assumptions about dividends, splits, transaction costs, execution timing, and portfolio valuation in the relevant backtesting documentation.

## 5. Look-ahead bias and point-in-time integrity

Adjusted historical prices can be revised retrospectively when later corporate actions occur. Their use does not by itself guarantee the absence of look-ahead bias.

Before finalising the backtesting methodology, the project must establish:

- whether point-in-time adjusted data is available or can be reconstructed reliably;
- which data would have been available at each simulated decision time;
- how features and prediction targets are aligned chronologically;
- how splits, dividends, execution prices, and transaction costs are represented;
- that training, validation, and test periods are chronological and future information cannot enter historical decisions.

Predictions must use only information available at the decision time. Simulated execution must follow an explicit timing convention and must not assume execution at a price that was not yet available.

## 6. Read-only audit results

The audit covered 11,064 rows (2,766 observations per ticker) and did not modify source files.

| Check | Result |
|---|---:|
| Missing or non-finite values in raw/adjusted OHLC and volume fields | 0 |
| Non-positive raw or adjusted prices | 0 |
| Raw OHLC relationship violations | 0 |
| Adjusted OHLC relationship violations | 0 |
| Rows with inconsistent OHLC adjustment ratios above `1e-6` | 0 |
| Maximum within-row adjustment-ratio spread | `4.478691723e-12` |
| Missing, negative, or zero raw-volume values | 0 |
| Missing, negative, or zero adjusted-volume values | 0 |

The audit supports internal consistency between raw and adjusted OHLC fields. It does not independently certify every historical observation against exchange records or prove the provider's full adjustment methodology.

Five adjusted daily returns greater than 20% in absolute value were investigated:

- NVDA, 11 November 2016: +29.81%
- NVDA, 25 May 2023: +24.37%
- TSLA, 8 September 2020: -21.06%
- TSLA, 24 October 2024: +21.92%
- TSLA, 9 April 2025: +22.69%

These observations are consistent with historically documented market movements and do not coincide with the stock-split dates identified in the dataset. They are retained. Historical context alone is not proof of exact price accuracy.

## 7. Known limitations and follow-up work

The following items remain open before claiming complete market-data validation or finalising the backtesting engine:

1. Independently verify the provider's adjustment methodology and, where possible, selected historical observations.
2. Decide how to obtain or reconstruct point-in-time-consistent prices for historical simulations.
3. Define the exact treatment of dividends and stock splits in total-return calculations and portfolio accounting.
4. Specify execution timing, slippage, transaction costs, and order-fill assumptions.
5. Define the appropriate volume field for each volume-based feature.

This policy does not authorise feature engineering, model training, or backtesting by itself. Those steps remain subject to the project's staged workflow and validation requirements.

## 8. Decision record

The project adopts adjusted OHLC series for historical price analysis and price-based indicators, raw prices for simulated execution subject to explicit corporate-action handling, and explicit accounting for dividends and splits. Raw and adjusted fields must not be mixed casually. The source dataset remains unchanged.

**Decision status:** Approved by the project owner on 20 October 2026.
**Next step:** Review this document in the repository, then address the remaining point-in-time and corporate-action questions before feature engineering.
