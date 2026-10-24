# Target Definition and Generation Policy

**Status:** Target-generation implementation completed; asset-specific validation and corporate-action review outstanding
**Project:** AI Quantitative Trading & Decision Intelligence System
**Current development asset:** Lloyds Banking Group (`LLOY.L`)
**Primary market-data source:** Yahoo Finance via `yfinance`
**Forecast horizons:** 1, 5 and 10 trading sessions

## 1. Purpose

This document defines the target variables used to develop and evaluate the quantitative trading models.

The targets represent forward price returns over fixed trading-session horizons. They are intended to support regression models that forecast returns and classification models that estimate whether the defined forward return is positive.

The target definition is fixed and must not be changed without explicit approval from the project owner.

The implementation of the target-generation function has been completed and tested with synthetic data. However, implementation correctness does not establish that the historical market data is suitable for modelling or that the targets are ready for training, backtesting or paper trading.

## 2. Current Project Scope

The current development and pilot asset is Lloyds Banking Group, listed on the London Stock Exchange under ticker `LLOY.L`.

The project uses Yahoo Finance through `yfinance` as its market-data source. The configured historical data range is:

* Start date: `2015-01-01`
* End date: `2026-10-23`
* Sampling frequency: daily
* Trading currency: GBP

The historical dataset has been acquired and its coverage measured. It contains 2,985 daily observations for `LLOY.L`, from `2015-01-02` through `2026-10-23`. However, historical price-series integrity and corporate-action reconciliation remain under investigation. The measured coverage does not, by itself, establish that the dataset or its derived targets are suitable for modelling.

The longer-term system must allow the user to select any eligible and supported equity listed on the NYSE, Nasdaq or London Stock Exchange. The system must train and validate an asset-specific model for the selected equity before exposing forecasts or trading signals.

The current development scope remains restricted to `LLOY.L`. Historical results from other equities must not be treated as validation evidence for this pilot asset.

## 3. Approved Target Definition

Let:

* \(t\) denote the current trading session;
* \(h\) denote the forecast horizon in trading sessions;
* \(Open_{t+1}\) denote the opening price of the next trading session;
* \(Close_{t+h}\) denote the closing price \(h\) trading sessions after session \(t\).

The approved forward-return target is:

$$
R(t,h)=\frac{Close(t+h)}{Open(t+1)}-1
$$

The supported horizons are:

$$
h \in \{1,5,10\}
$$

The formula is approved and must remain unchanged unless the project owner explicitly authorises a revision.

### 3.1 Interpretation

The target represents the price return between the opening price of the next trading session and the closing price at the end of the selected horizon.

The prediction is assumed to be generated after the close of session \(t\). The opening price of session \(t+1\) is therefore a future execution reference relative to the prediction time, not information available when the prediction is generated.

For a one-session horizon, the reference entry price is the next session's open and the reference exit price is that same session's close.

For five- and ten-session horizons, the reference exit prices are the closes of the fifth and tenth sessions, respectively, after the prediction date.

The return is a gross execution-price return. It does not represent a complete portfolio return.

### 3.2 Formula examples

For a one-session horizon:

$$
R(t,1)=\frac{Close(t+1)}{Open(t+1)}-1
$$

For a five-session horizon:

$$
R(t,5)=\frac{Close(t+5)}{Open(t+1)}-1
$$

For a ten-session horizon:

$$
R(t,10)=\frac{Close(t+10)}{Open(t+1)}-1
$$

All horizons use the same entry-price convention.

## 4. Target Variables

The implementation generates six target columns.

| Target column         | Type           | Definition                                                           |
| --------------------- | -------------- | -------------------------------------------------------------------- |
| `forward_return_1d`   | Regression     | Forward return over one trading session                              |
| `forward_return_5d`   | Regression     | Forward return over five trading sessions                            |
| `forward_return_10d`  | Regression     | Forward return over ten trading sessions                             |
| `positive_return_1d`  | Classification | 1 if `forward_return_1d` is strictly greater than zero; otherwise 0  |
| `positive_return_5d`  | Classification | 1 if `forward_return_5d` is strictly greater than zero; otherwise 0  |
| `positive_return_10d` | Classification | 1 if `forward_return_10d` is strictly greater than zero; otherwise 0 |

Classification labels must only be populated when the corresponding regression target is valid.

A return equal to zero is classified as `0`, not `1`. A missing or invalid forward-return target must remain missing rather than being converted into a negative-return label.

These binary targets describe the sign of the defined forward price return. They do not, by themselves, constitute BUY, HOLD, SELL or WAIT trading signals.

## 5. Price Fields and Corporate Actions

### 5.1 Required price fields

Target generation requires the following columns:

* `date`
* `ticker`
* `Open`
* `Close`

The current implementation uses the `Open` and `Close` fields supplied in the input DataFrame. It does not replace the approved formula with an adjusted-close return calculation.

The acquisition workflow requests Yahoo Finance data with `auto_adjust=False`, retaining raw OHLC fields separately from the provider-supplied `Adj Close` field.

The meaning and historical adjustment treatment of provider-supplied fields must be considered when assessing data quality. The presence of `Adj Close` does not establish that the `Open` and `Close` fields are point-in-time prices or that all corporate-action effects have been independently reconciled.

### 5.2 Stock splits

A stock split changes the number of shares and the nominal price per share without, by itself, creating an equivalent economic gain or loss.

The target-generation formula must not be changed silently to compensate for a suspected split adjustment.

Before targets are accepted for modelling, the `LLOY.L` historical series must be checked for relevant stock splits and other corporate actions. Any split affecting a target's entry-to-exit interval must be investigated to determine whether the input prices produce an economically meaningful return under the approved formula.

The investigation must establish whether the provider's historical prices already reflect the relevant split adjustments. Additional split adjustments must not be applied without evidence that they are required.

If the price series cannot be reconciled satisfactorily, the affected observations must not be treated as validated targets.

### 5.3 Dividends

The approved target represents a price return only. Dividend cash flows are excluded.

The `Dividends` and `Adj Close` fields may be retained for separate data-quality and corporate-action analysis. Their presence does not mean that dividend cash flows are included in the target.

Dividend dates, amounts and share-basis conventions must be reconciled before dividend-sensitive portfolio accounting or total-return backtesting is approved.

Dividend cash flows must not be added implicitly to this target, and the target must not be described as a total shareholder return.

## 6. Target Alignment and Missing Values

For each ticker, observations must be ordered chronologically before future prices are aligned to the current observation.

The target calculation must not cross ticker boundaries. The future prices used for one ticker must never be drawn from another ticker's observations.

For each horizon, observations without the required future entry or exit price cannot have a valid target.

Consequently, the final observations in each sufficiently long price series will have missing targets. With complete consecutive observations, the implementation is expected to leave one, five and ten terminal observations without valid regression targets for the respective horizons.

The actual number of missing targets must be assessed against the available observations and any missing or irregular dates. Missing values must not be filled with fabricated future prices or converted into classification labels.

The implementation also validates the input structure, rejects duplicate ticker-date observations and checks that the relevant prices are finite and positive.

## 7. Temporal Integrity and Leakage Prevention

Target generation must preserve the distinction between information available at prediction time and prices observed in the future.

The following requirements apply:

1. Features for session \(t\) must use only information available by the prediction time after the close of session \(t\).
2. Future prices may be used to construct labels, but must not enter the feature matrix for the same prediction.
3. The target formula and feature timestamps must remain aligned.
4. Observations must not be randomly shuffled to create the primary training, validation and test partitions.
5. Evaluation must use chronological validation, with a documented walk-forward design.
6. Overlapping target intervals must be considered when defining validation boundaries.
7. Purging and, where justified by the final design, an embargo must prevent overlapping label information from contaminating evaluation.
8. All preprocessing, feature selection, scaling, imputation and model-selection decisions must be fitted or selected without using future validation or test information.
9. The final evaluation period must not be used to tune the model or select the reported result.

For a horizon of \(h\) sessions, the target for an observation at \(t\) depends on future price information through \(t+h\). Validation design must account for this dependency.

A correctly calculated target does not, on its own, guarantee that the complete modelling pipeline is free from look-ahead bias.

## 8. Implementation Behaviour

The target-generation function is implemented in `src/target_generation.py`.

The current implementation:

* accepts a pandas DataFrame;
* checks the required input columns;
* validates ticker and date values;
* rejects duplicate ticker-date observations;
* checks that the relevant prices are numeric, finite and positive;
* orders observations by ticker and date for the calculation;
* calculates the three forward-return targets;
* creates the three corresponding binary classification targets;
* prevents future-price alignment from crossing ticker boundaries;
* preserves the original input DataFrame;
* restores the original row order in the result;
* leaves targets missing when the required future prices are unavailable.

The implementation uses the approved formula and the configured horizons of one, five and ten trading sessions.

The implementation status describes software behaviour, not the suitability of a particular historical dataset.

## 9. Historical Corporate-Action Evidence

### 9.1 Current pilot scope

The current pilot asset is Lloyds Banking Group (`LLOY.L`), listed on the London Stock Exchange and denominated in GBP.

The acquired historical dataset is stored at:

`data/raw/yahoo/configured/LLOY.L.csv`

The dataset contains 2,985 observations covering 2 January 2015 to 23 October 2026. Basic structural checks have been executed, but the historical price series and corporate-action records have not yet been fully reconciled.

### 9.2 Documented OHLC inconsistencies

Three observations in the acquired dataset violate expected OHLC relationships:

| Date          |      Open |      High |       Low |     Close | Inconsistency       |
| ------------- | --------: | --------: | --------: | --------: | ------------------- |
| 31 March 2015 | 79.389999 | 79.650002 | 78.300003 | 78.279999 | Close is below Low  |
| 15 June 2020  | 30.445000 | 32.939999 | 30.889999 | 31.530001 | Low is above Open   |
| 1 May 2024    | 52.099998 | 52.139999 | 51.980000 | 52.200001 | Close is above High |

The recorded values were verified against the original acquired CSV file. No source observations have been modified.

The causes of these inconsistencies remain unresolved. They must not automatically be attributed to corporate actions, provider adjustments or data errors without supporting evidence.

The 15 June 2020 observation requires particular attention because the approved target uses the next session's Open as the reference entry price. Its implications for target interpretation and any future execution simulation must be assessed before the affected observation is authorised for those purposes.

### 9.3 Dividends, stock splits and price adjustments

The dataset includes `Adj Close`, `Dividends` and `Stock Splits` fields. The presence of these fields does not establish that all corporate actions have been reconciled or that the relationship between raw OHLC prices and adjusted closing prices is fully understood.

The following checks remain necessary:

* review the available split and dividend records for the pilot asset;
* investigate the adjustment conventions represented in the acquired data;
* assess relevant discrepancies between raw OHLC prices and `Adj Close`;
* determine whether identified corporate actions affect the interpretation of historical prices or the approved target;
* document any limitations affecting future execution simulations.

No additional split adjustment or other price transformation is authorised by this document.

### 9.4 Implications for the approved target

The approved target remains:

$$
R(t,h)=\frac{Close(t+h)}{Open(t+1)}-1
$$

This target measures the gross return between the specified reference entry and exit prices. It does not include dividend cash flows, transaction costs, slippage, taxes or other execution effects.

The formula must not be changed to compensate for unresolved data-quality issues. Any future proposal to modify the target definition requires explicit review and approval.

Until the relevant price-series and corporate-action investigations have been completed, the target-generation implementation must be distinguished from approval of the historical observations for modelling or simulated execution.

## 10. Implementation and Test Status

### 10.1 Current implementation status

**Target-generation implementation:** Completed.

The current implementation in `src/target_generation.py` generates the six approved target columns for the supported horizons.

### 10.2 Current automated test evidence

On 24 October 2026, the following command was reported as executed:

```bash
pytest -q tests/test_target_generation.py
```

Reported result:

```text
27 passed in 0.68s
```

These tests cover target calculation and related input-validation behaviour using synthetic test data. They provide evidence that the tested implementation behaves as expected for those test cases.

They do not establish that the historical `LLOY.L` dataset is complete, accurate, free from material corporate-action issues or suitable for modelling.

This result refers only to `tests/test_target_generation.py`. It must not be represented as confirmation that the complete project test suite passed.

### 10.3 Current Pilot Audit Evidence

The current pilot uses the historical dataset:

`data/raw/yahoo/configured/LLOY.L.csv`

The dataset contains 2,985 observations covering 2 January 2015 to 23 October 2026.

The target-generation implementation has been exercised against synthetic test cases, and the approved target-generation test file has previously reported 27 passing tests.

Additional implementation and audit work has established that:

* the target-generation function creates the six approved target columns for the one-, five- and ten-session horizons;
* target calculations respect ticker boundaries and chronological ordering;
* missing future prices produce missing targets rather than fabricated outcomes;
* target-maturity dates are calculated using observed trading sessions;
* temporal eligibility checks exclude observations whose target outcomes were not yet known at the relevant cutoff.

These results support the implementation and temporal-eligibility behaviour tested to date. They do not establish that all historical prices or corporate-action records are accurate.

The documented OHLC inconsistencies and outstanding corporate-action review remain separate data-quality concerns.

### 10.4 Outstanding Validation

The following work remains outstanding for the current pilot:

* investigate the three documented OHLC inconsistencies and record their causes or unresolved status;
* reconcile raw OHLC prices, `Adj Close`, dividends and stock splits;
* assess the implications of unresolved price-series issues for the approved target and any future execution simulation;
* review point-in-time data integrity and the possible effects of retrospective provider adjustments;
* review temporal validation boundaries, overlapping target intervals, purging and embargo, and document any required decisions;
* execute the complete project test suite and record the actual result when appropriate;
* review the outstanding data-quality findings before authorising model training or trading evaluation.

Basic structural checks, historical coverage measurement, target-generation implementation and temporal-eligibility audits have already been executed. Their completion must not be interpreted as approval of the historical price series.

The target formula remains unchanged. Any proposed change requires explicit review and approval.

## 11. Limitations and Open Decisions

The target definition fixes the gross price-return calculation. It does not determine all the assumptions required for a complete trading system.

The following limitations remain relevant:

1. The historical accuracy and completeness of the `LLOY.L` series have not yet been established by this document.
2. The provider's full adjustment methodology and point-in-time data availability have not been independently established.
3. Corporate-action treatment must be investigated for the current pilot asset.
4. Dividend cash flows are excluded from the target.
5. The target excludes transaction costs, bid-ask spread, slippage, commissions, taxes and other execution costs.
6. A positive forward return does not guarantee that a trade would be profitable after costs.
7. A target-generation test passing does not demonstrate predictive performance or trading profitability.
8. The binary positive-return labels do not directly determine BUY, HOLD, SELL or WAIT signals.
9. Model selection, probability calibration, position sizing, portfolio accounting and risk controls require separate documented decisions and validation.

Any unresolved material data-quality issue must be addressed before the affected targets are approved for modelling.

## 12. Approval Gate

The following distinctions must be maintained:

| Item                                          | Current status                            |
| --------------------------------------------- | ----------------------------------------- |
| Approved target formula                       | Fixed                                     |
| Forecast horizons                             | Fixed at 1, 5 and 10 trading sessions     |
| Target-generation implementation              | Completed                                 |
| Synthetic target-generation tests             | 27 passed, as reported on 24 October 2026 |
| Legacy four-equity target audit               | Historical claim recorded; evidence not verified |
| `LLOY.L` historical target validation         | Outstanding                               |
| Current pilot corporate-action reconciliation | Outstanding                               |
| Final temporal validation design              | Requires completion and approval          |
| Model training                                | Not authorised                            |
| Backtesting                                   | Not authorised                            |
| Paper trading                                 | Not authorised                            |

The project owner must explicitly approve the relevant data-quality and validation findings before the targets are used for model training or backtesting.

No change to the approved target formula is permitted without explicit approval from the project owner.
