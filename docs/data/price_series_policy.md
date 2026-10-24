# Price Series Policy

**Project:** AI Quantitative Trading & Decision Intelligence System
**Status:** Policy defined; asset-specific validation pending
**Language:** British English

## 1. Purpose

This document defines how raw and adjusted market-price series, trading volume, dividends, and stock splits must be handled throughout the project.

The policy aims to maintain consistency between historical analysis, feature engineering, target generation, simulated execution, and portfolio accounting. It also establishes safeguards against look-ahead bias, inconsistent price adjustments, and unsupported assumptions about corporate actions.

The initial development asset is Lloyds Banking Group (`LLOY.L`), listed on the London Stock Exchange (LSE). Yahoo Finance, accessed through `yfinance`, is the approved market-data source.

The future system must allow users to select any eligible and supported equity listed on the New York Stock Exchange (NYSE), Nasdaq, or LSE. Each selected asset must undergo asset-specific data validation before its forecasting models or trading signals become available.

The configured historical acquisition window is 1 January 2015 to 23 October 2026. This is a configuration range, not evidence that every expected observation has been retrieved, validated, or approved for modelling.

## 2. Data Source and Field Definitions

### 2.1 Approved data source

Yahoo Finance is the sole approved market-data source for the current project scope.

Daily observations are retrieved using `yfinance`. The acquisition process requests raw prices, adjusted closing prices, trading volume, dividend events, and stock-split events where the provider makes them available.

The exact returned columns and their data types must be verified against the acquired dataset. Column names may be normalised internally, but the transformation must be documented and reproducible.

### 2.2 Expected fields

The acquisition layer may return the following fields:

| Field          | Meaning                                                | Primary considerations                                                                     |
| -------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `Date`         | Trading-session date                                   | Must be parsed consistently and ordered chronologically.                                   |
| `Open`         | Reported opening price                                 | Used by the approved target definition as the next-session entry-price reference.          |
| `High`         | Reported session high                                  | Must be positive and consistent with the other raw OHLC values.                            |
| `Low`          | Reported session low                                   | Must be positive and consistent with the other raw OHLC values.                            |
| `Close`        | Reported closing price                                 | Used by the approved target definition as the future exit-price reference.                 |
| `Adj Close`    | Provider-adjusted closing price                        | Adjustment methodology and historical revision implications must be considered.            |
| `Volume`       | Reported trading volume                                | Units, missing values, and split-related changes must be investigated.                     |
| `Dividends`    | Provider-reported dividend events                      | Event dates, amounts, and adjustment conventions require validation before accounting use. |
| `Stock Splits` | Provider-reported split events                         | Event dates and split ratios require validation before position accounting.                |
| `ticker`       | Asset identifier, if included by the acquisition layer | Must match the requested asset.                                                            |

The acquisition implementation may use normalised column names internally. Any normalisation must preserve the distinction between raw and adjusted prices.

The presence of a field does not establish its correctness, completeness, adjustment convention, or suitability for a particular calculation.

## 3. Policy by Use Case

| Use case                                   | Preferred data                                                            | Policy                                                                                                                                            |
| ------------------------------------------ | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Approved forecasting target                | Raw `Open` and `Close`                                                    | Use the fixed target formula defined in `target_definition.md`. Do not substitute adjusted prices without explicit project-owner approval.        |
| Historical close-to-close returns          | Consistently adjusted closing-price series, subject to validation         | Document the return convention and verify the treatment of corporate actions.                                                                     |
| Historical volatility                      | Returns derived from a consistently defined price series                  | Do not mix return conventions within the same analysis.                                                                                           |
| Moving averages and price-based indicators | A consistent price series with documented adjustment treatment            | Investigate artificial discontinuities caused by splits and potential retrospective revisions.                                                    |
| OHLC technical indicators                  | A consistent OHLC series                                                  | Do not combine raw and adjusted OHLC values within a calculation unless the method is explicitly justified and documented.                        |
| Volume-based indicators                    | `Volume`, subject to validation                                           | Establish the volume convention and investigate split-related changes before using volume for liquidity or execution modelling.                   |
| Simulated order execution                  | Raw market prices and a documented execution model                        | Include explicit assumptions for execution timing, transaction costs, slippage, and liquidity constraints.                                        |
| Position and portfolio accounting          | Simulated prices, share quantities, and validated corporate-action events | Account for changes in share quantities and cash balances consistently.                                                                           |
| Dividend accounting                        | Validated dividend events and explicit cash-flow rules                    | Do not assume that a provider-reported dividend field is independently verified or suitable for accounting without reconciliation.                |
| Stock-split accounting                     | Validated split events and explicit position-adjustment rules             | Adjust simulated share quantities and the applicable price basis consistently. A split must not be treated as an economic gain or loss by itself. |

## 4. Approved Target Price Convention

The forecasting target is governed by `target_definition.md`. This policy does not modify that specification.

For a forecast generated after the close of session \(t\), the gross price return for horizon \(h\) is:

$$
R(t,h)=\frac{Close(t+h)}{Open(t+1)}-1
$$

The approved horizons are:

* 1 trading session;
* 5 trading sessions;
* 10 trading sessions.

The entry-price reference is the raw opening price of the next trading session. The exit-price reference is the raw closing price at the specified horizon.

The target excludes transaction costs, slippage, taxes, and dividend cash flows. These exclusions must remain explicit when interpreting forecast performance and any subsequent trading simulation.

The following rules are mandatory:

1. Use raw `Open` and `Close` prices for target generation.
2. Do not silently replace either price with an adjusted value.
3. Do not add dividends to the target return.
4. Do not change the entry timing, exit timing, or horizon definitions without explicit project-owner approval.
5. Validate corporate-action effects before accepting the target series for modelling.
6. Treat unavailable future entry or exit prices as unavailable targets rather than fabricating observations.
7. Prevent future target values from entering features or preprocessing fitted on earlier observations.

The target-generation implementation has passed its dedicated synthetic unit tests. This does not establish that the target is fully validated against the historical `LLOY.L` dataset.

## 5. Raw and Adjusted Prices

### 5.1 Raw prices

Raw OHLC prices represent the provider-reported prices for individual trading sessions.

They are required for the approved target convention and are the starting point for modelling plausible execution prices. They do not, by themselves, establish that an order could have been filled at the reported price.

Simulated execution must account for relevant practical constraints, including transaction costs, slippage, liquidity, and the availability of a trading opportunity at the assumed time.

### 5.2 Adjusted closing prices

`Adj Close` is a provider-adjusted historical series. It may incorporate adjustments associated with corporate actions, including dividends and stock splits, according to the provider's methodology.

Adjusted prices can be useful for historical return analysis and certain price-based indicators. However, the adjustment methodology, revision behaviour, and point-in-time availability must be considered.

A retrospectively adjusted series may contain information about corporate actions that occurred after an earlier observation date. Whether and how this affects a specific feature must be assessed before the feature is approved for model training.

The project must not assume that a historically downloaded adjusted series is identical to the series that would have been available to a user at each historical forecast date.

### 5.3 Consistency requirements

The following rules apply:

1. Do not mix raw and adjusted prices within a calculation without a documented mathematical justification.
2. Record which price series is used by each feature, target, evaluation metric, and portfolio-accounting calculation.
3. Do not calculate the approved target using `Adj Close`.
4. Do not assume that an adjusted series is automatically free of look-ahead bias.
5. Investigate large apparent price changes before classifying them as errors or removing them.
6. Preserve genuine market movements; do not remove extreme returns solely because they exceed a fixed threshold.
7. Keep downloaded source observations unchanged during audits. Any transformations must be reproducible and written to a separately defined output.

## 6. Dividends

### 6.1 Current policy

Dividend events returned by Yahoo Finance must be treated as provider-supplied observations requiring validation.

Before dividends are used in portfolio accounting or total-return analysis, the project must investigate:

* the event date and relevant trading-session alignment;
* the reported cash amount and currency;
* the applicable share basis;
* the effect of any relevant stock split;
* consistency with an authoritative corporate record where available;
* whether the selected price series already reflects dividend adjustments.

The scope and results of any reconciliation must be recorded.

### 6.2 Target and accounting separation

The approved forecasting target measures gross price return and excludes dividend cash flows.

Dividends must not be added implicitly to the target or used to alter its definition.

If dividend-inclusive portfolio returns are introduced later, they must be implemented as a separate, explicitly documented accounting calculation. The implementation must prevent double-counting when the selected price series already incorporates relevant adjustments.

### 6.3 Current validation status

Dividend history for `LLOY.L` has been retrieved as part of the configured historical dataset, but its accuracy and consistency with authoritative corporate-action records have not yet been fully reconciled.

The structural audit confirmed that the source dataset contains the `Dividends` field and no missing values in the source columns. These checks do not establish that individual dividend events, amounts, dates, currencies, or adjustment effects are correct.

Consequently:

* Dividend-inclusive performance claims remain unvalidated.
* Dividend-dependent portfolio accounting must not yet be treated as validated.
* The approved forecasting target remains a gross price return and excludes dividend cash flows.
* Dividend reconciliation must be completed before dividend-inclusive portfolio performance is evaluated.

## 7. Stock Splits and Other Corporate Actions

Stock splits can change quoted prices and share quantities without, by themselves, changing the economic value of a position.

The project must investigate corporate-action events that may affect the continuity or interpretation of the historical price series.

For each relevant event, validation should consider:

1. the event date;
2. the reported event or split ratio;
3. the raw prices surrounding the event;
4. the adjusted-price behaviour surrounding the event;
5. the consistency of share-quantity and price transformations;
6. the effect on target calculations and simulated portfolio positions.

Do not automatically classify a large price change as a stock split, data error, or genuine market movement without supporting evidence.

Do not apply an additional split adjustment to provider-adjusted data unless the existing adjustment convention has been established and the additional transformation is justified.

If a material corporate action creates ambiguity in the approved raw-price target, record the affected observations and resolve the issue before accepting the affected targets for modelling.

### 7.1 Current validation status

The historical `LLOY.L` dataset has been acquired and subjected to basic structural checks. However, the corporate-action history and its effects on the raw and adjusted price series have not yet been fully reconciled.

The historical audit identified three observations with inconsistent OHLC relationships:

* 31 March 2015: `Close` is below `Low`.
* 15 June 2020: `Low` is above `Open`.
* 1 May 2024: `Close` is above `High`.

These observations have been preserved in the source dataset. Their causes have not been established, and they must not be automatically classified as corporate-action effects or corrected without supporting evidence.

The following items remain unresolved:

* Reconciliation of relevant stock splits and other corporate actions.
* Assessment of raw versus adjusted price behaviour around relevant events.
* Investigation of the three documented OHLC anomalies.
* Assessment of the implications for the approved raw-price forecasting targets.

No conclusion is made that the historical price series is free from material corporate-action or price-integrity issues.

## 8. Volume and Liquidity

Volume must be interpreted according to its documented units and adjustment convention.

Before volume is used for liquidity features or execution modelling, the project must assess:

* missing, non-numeric, negative, or otherwise invalid values;
* unusual observations that require investigation;
* split-related changes in share-volume units;
* consistency between volume observations and the selected asset;
* the limitations of daily volume as a proxy for the liquidity available to a particular simulated order.

A volume observation does not prove that an order of a given size could have been executed at a particular price.

Any future execution model must state its liquidity assumptions and justify how order size relates to the available market volume.

The adjustment convention and historical quality of `LLOY.L` volume have not yet been fully validated.

## 9. Data Quality and Anomaly Handling

Before a historical series is approved for modelling, the asset-specific data-quality assessment must cover at least the following checks:

* correct ticker and trading-session dates;
* chronological ordering and duplicate observations;
* missing observations and unexpected gaps;
* numeric, finite, and positive OHLC prices;
* logical OHLC relationships;
* invalid or missing volume values;
* suspicious price jumps and extreme returns;
* possible corporate-action effects;
* dividend and stock-split event consistency;
* consistency between raw and adjusted series;
* historical coverage relative to the configured date range.

### 9.1 Completed Checks and Documented Evidence

The configured historical dataset for `LLOY.L` was acquired for the period from 2 January 2015 to 23 October 2026 and contains 2,985 observations.

The basic structural audit reported:

* required source columns are present;
* dates are valid;
* observations belong to a single ticker;
* no missing values were found in the source columns;
* no duplicate ticker-date pairs were identified;
* `Open`, `High`, `Low`, `Close`, and `Adj Close` are numeric, finite, and positive.

Historical coverage has been measured. Three observations with inconsistent OHLC relationships have been documented:

* 31 March 2015: `Close` is below `Low`;
* 15 June 2020: `Low` is above `Open`;
* 1 May 2024: `Close` is above `High`.

These observations remain unchanged in the source dataset. Their causes have not been established.

The completed structural checks do not establish that the entire price series is free from material errors, that corporate actions have been reconciled, or that raw and adjusted prices are suitable for every intended use.

### 9.2 Outstanding Validation

The following assessments remain outstanding:

* investigation of the three documented OHLC anomalies and any additional suspicious price movements;
* review of volume quality, units, and adjustment conventions;
* reconciliation of relevant dividend and stock-split records;
* assessment of raw and adjusted price behaviour around relevant corporate actions;
* evaluation of potential look-ahead effects from retrospective price adjustments;
* approval of the C1 acceptance criteria and scoring rules;
* completion and review of the overall asset-specific data-quality eligibility assessment.

An anomaly is a reason to investigate, not an automatic reason to delete or correct an observation.

Every exclusion, correction, or transformation must have a documented rationale and be reproducible. Original source data must remain unchanged.

Critical structural or corporate-action issues must not be concealed by a composite quality score or offset by good results in unrelated checks.

The detailed assessment procedure and acceptance criteria are defined in `docs/analysis/c1_data_quality_and_historical_coverage.md`.

**Current status:** Basic structural checks completed; three OHLC anomalies documented; overall C1 data-quality assessment remains `NOT_ASSESSED`.

The historical series must not be considered fully approved for modelling until the outstanding checks have been reviewed, the C1 acceptance criteria have been approved, and the resulting eligibility decision has been recorded.

## 10. Temporal Integrity and Leakage Prevention

Historical features must only use information that would have been available at the relevant forecast timestamp.

For a forecast generated after the close of session \(t\):

* features must not contain observations from sessions after \(t\);
* future target values must not enter feature construction;
* preprocessing parameters must be fitted using the relevant training data only;
* transformations must respect chronological boundaries;
* retrospective price adjustments must be assessed for potential look-ahead effects;
* any rolling calculations must use only information available at their respective timestamps.

The use of adjusted prices does not remove the need for chronological validation or a separate assessment of point-in-time data availability.

The project's temporal validation protocol is documented in `docs/analysis/temporal_validation_strategy.md`. Its final implementation and acceptance decisions remain subject to review and explicit project-owner approval.

## 11. Reproducibility and Data Governance

The acquisition and transformation process must record, where applicable:

* asset ticker and exchange;
* market-data provider;
* configured start and end dates;
* acquisition timestamp;
* data interval;
* requested and returned fields;
* row counts and date coverage;
* missing and duplicate observations;
* corporate-action observations;
* transformations and validation outcomes;
* software and dependency versions;
* relevant configuration values.

Downloaded market data must remain local and must not be committed to or published in the public repository unless the project's data-governance and licensing requirements have been reviewed and explicitly permit it.

Source data, transformed datasets, validation reports, and model artefacts must be distinguishable. Any transformation must be reproducible from recorded inputs and configuration.

## 12. Current Project Decisions

| Item                                 | Current decision or status                                             |
| ------------------------------------ | ---------------------------------------------------------------------- |
| Initial development asset            | Lloyds Banking Group (`LLOY.L`)                                        |
| Initial exchange                     | London Stock Exchange (LSE)                                            |
| Market-data source                   | Yahoo Finance via `yfinance`                                           |
| Configured acquisition window        | 1 January 2015 to 23 October 2026                                      |
| Data interval                        | Daily                                                                  |
| Initial hypothetical portfolio       | GBP 1,000                                                              |
| Forecast horizons                    | 1, 5, and 10 trading sessions                                          |
| Target price convention              | Raw `Open` and `Close`, as defined in `target_definition.md`           |
| Dividend treatment in target         | Excluded                                                               |
| Structural data checks               | Completed; basic structural checks passed                              |
| Historical coverage                  | Measured for the acquired dataset                                      |
| OHLC integrity                       | Review required; three inconsistent OHLC observations documented       |
| Dividend reconciliation              | Pending                                                                |
| Corporate-action reconciliation      | Pending                                                                |
| Raw versus adjusted price assessment | Pending                                                                |
| Point-in-time adjustment assessment  | Pending                                                                |
| Overall C1 data-quality assessment   | `NOT_ASSESSED`; acceptance criteria and scoring rules require approval |
| Model training                       | Not authorised                                                         |
| Backtesting                          | Not authorised                                                         |
| Paper trading                        | Not authorised                                                         |

## 13. Acceptance Conditions

Before the `LLOY.L` price series is accepted for modelling, the project must:

1. Review the completed structural checks and historical-coverage evidence, and document any remaining limitations.
2. Investigate the three documented OHLC anomalies and any additional material price anomalies identified during the review.
3. Assess raw and adjusted price behaviour around relevant corporate actions.
4. Reconcile relevant dividend and stock-split records to the extent required for the intended analyses, documenting unresolved limitations.
5. Establish the suitability of the selected price series for each intended feature and calculation, including the approved forecasting targets.
6. Assess potential look-ahead effects arising from retrospectively adjusted data and document the limitations of the available historical information.
7. Confirm that the approved target convention is implemented without modification.
8. Approve the C1 acceptance criteria and scoring rules, assess the evidence against those criteria, and document the overall data-quality eligibility decision.
9. Obtain explicit project-owner approval before proceeding to model training or backtesting.

A successful data download, completed structural checks, or passing unit tests is not, by itself, evidence that all acceptance conditions have been met.

## 14. Decision Record

This policy establishes the approved price-series conventions for the `LLOY.L` pilot, using Yahoo Finance via `yfinance` as the sole market-data source.

The approved forecasting target remains a gross price return calculated using the next observed trading session's `Open` as the entry reference and the `Close` at the specified forecast horizon as the exit reference. Dividend cash flows remain excluded from the target.

The configured historical dataset has been acquired and subjected to basic structural checks. Historical coverage has been measured, and three observations with inconsistent OHLC relationships have been documented. These observations remain unchanged in the source dataset because their causes have not yet been established.

The following matters remain unresolved:

* Investigation of the documented OHLC anomalies.
* Reconciliation of relevant dividend and corporate-action records.
* Assessment of raw and adjusted price behaviour.
* Assessment of potential look-ahead effects from retrospective price adjustments.
* Approval of the C1 acceptance criteria and scoring rules.
* Completion and review of the overall asset-specific data-quality eligibility assessment.

**Current status:** Price-series policy defined; basic structural checks completed; overall C1 data-quality assessment remains `NOT_ASSESSED`.

**Next step:** Complete the outstanding historical price-integrity and corporate-action investigations, review the evidence against formally approved C1 criteria, and record the resulting eligibility decision.

Model training, backtesting, and paper trading remain unauthorised until the required reviews have been completed and explicit project-owner approval has been granted.
