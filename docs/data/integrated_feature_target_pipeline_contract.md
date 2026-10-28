# Integrated Feature and Target Pipeline Contract

**Project:** AI Quantitative Trading & Decision Intelligence System
**Pilot asset:** Lloyds Banking Group (`LLOY.L`)
**Status:** Proposed contract — pending implementation verification
**Scope:** Historical feature generation, forward-target generation, target maturity and downstream modelling eligibility

## 1. Purpose

This document defines the data contract connecting historical market data, feature engineering, target generation and temporal eligibility.

Its purpose is to establish consistent column definitions, temporal alignment rules, missing-value behaviour and interface requirements before the pipeline is used by predictive models.

This contract documents the intended integrated behaviour. It does not, by itself, certify that every requirement is already satisfied by the integrated implementation.

## 2. Pipeline Architecture

The pipeline is logically divided into five stages:

1. **Historical input:** load and validate the historical market-data observations.
2. **Feature generation:** calculate historical features using information available at the prediction time.
3. **Target generation:** calculate forward-return and return-direction labels using future prices.
4. **Maturity assignment:** identify the future session at which each target becomes fully observable.
5. **Eligibility filtering:** determine whether each observation can be used for a particular training or evaluation operation.

The expected logical flow is:

`Historical Data → Features → Targets → Target Maturity → Temporal Eligibility`

The feature and target calculations must preserve a common observation identity based on `ticker` and `date`.

The architecture must not assume that generating a target makes the observation immediately eligible for model training.

## 3. Input Data Contract

### 3.1 Required columns

The minimum historical input required by the combined pipeline is:

| Column   | Expected meaning     | Validation requirement                |
| -------- | -------------------- | ------------------------------------- |
| `date`   | Trading-session date | Present and parseable                 |
| `ticker` | Asset identifier     | Present and non-missing               |
| `Open`   | Raw opening price    | Numeric, finite and strictly positive |
| `Close`  | Raw closing price    | Numeric, finite and strictly positive |

Additional market-data columns may be retained, including `High`, `Low`, `Adj Close`, `Volume`, `Dividends` and `Stock Splits`.

Their presence must not silently change the approved feature or target definitions.

### 3.2 Observation identity

The logical key is:

`(ticker, date)`

Duplicate observations for the same ticker and date must be rejected.

Calculations must be performed chronologically and independently for each ticker. No feature, target or maturity calculation may cross asset boundaries.

The pipeline must preserve the original input data and must not modify the caller's DataFrame in place.

### 3.3 Row order and index

Intermediate calculations may require chronological sorting.

The externally returned result must preserve the input row order and index unless a separately documented interface explicitly specifies otherwise.

The original `ticker` and `date` values must remain available for downstream alignment and auditing.

## 4. Feature Contract

### 4.1 Required feature columns

The feature-generation stage must provide the following seven columns:

| Feature                | Definition                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| `close_return_1d`      | `Close(t) / Close(t-1) - 1`                                                               |
| `close_return_5d`      | `Close(t) / Close(t-5) - 1`                                                               |
| `close_return_10d`     | `Close(t) / Close(t-10) - 1`                                                              |
| `close_return_20d`     | `Close(t) / Close(t-20) - 1`                                                              |
| `close_volatility_5d`  | Rolling sample standard deviation of daily closing-price returns over five observations   |
| `close_volatility_10d` | Rolling sample standard deviation of daily closing-price returns over ten observations    |
| `close_volatility_20d` | Rolling sample standard deviation of daily closing-price returns over twenty observations |

Here, `t-k` denotes the observation `k` trading sessions earlier for the same ticker, rather than a calendar-day offset.

### 4.2 Calculation rules

Historical returns must use closing prices available on or before the prediction time.

Volatility must use historical one-session closing-price returns and the existing sample-standard-deviation convention, `ddof=1`.

The configured rolling windows require complete observations. Insufficient history must produce missing feature values rather than fabricated values.

The feature stage must not use forward prices, target labels or future-derived statistics.

### 4.3 Feature output

The feature stage must return the original input columns together with the seven feature columns.

Temporary calculation columns must not be exposed as permanent features unless explicitly added to the contract.

## 5. Target Contract

### 5.1 Approved definition

For decision session `t` and forecast horizon `h`, the approved forward-return target is:

$$
R(t,h)=\frac{Close(t+h)}{Open(t+1)}-1
$$

where:

$$
h \in \{1,5,10\}
$$

The prediction is assumed to be generated after the close of session `t`.

The next session's opening price is the reference entry price, and the closing price at the selected horizon is the reference exit price.

This definition must not be replaced by a close-to-close return or an adjusted-close return without explicit project-owner approval.

The target represents a gross price return. It excludes dividends, transaction costs, slippage, taxes and other portfolio-level cash flows.

### 5.2 Required regression targets

| Column               | Definition                    |
| -------------------- | ----------------------------- |
| `forward_return_1d`  | `Close(t+1) / Open(t+1) - 1`  |
| `forward_return_5d`  | `Close(t+5) / Open(t+1) - 1`  |
| `forward_return_10d` | `Close(t+10) / Open(t+1) - 1` |

### 5.3 Required classification targets

| Column                | Definition                                 |
| --------------------- | ------------------------------------------ |
| `positive_return_1d`  | 1 if `forward_return_1d > 0`, otherwise 0  |
| `positive_return_5d`  | 1 if `forward_return_5d > 0`, otherwise 0  |
| `positive_return_10d` | 1 if `forward_return_10d > 0`, otherwise 0 |

A return equal to zero is classified as `0`.

A missing or invalid regression target must result in a missing classification target. It must not be converted into a negative-return label.

These classification targets describe the sign of the defined forward return. They are not trading signals.

### 5.4 Target alignment

Each target must remain attached to the observation representing the decision session `t`, not the future entry or exit session.

Future prices may be used to construct targets, but they must never be added to the feature matrix for the corresponding decision observation.

Target calculations must remain independent for each ticker.

### 5.5 Missing future prices

A target must be missing when the required future entry or exit price is unavailable or invalid.

The pipeline must not fill missing targets with zero, reuse an earlier price or manufacture a future observation.

For a complete series with no irregular gaps, the final one, five and ten decision observations will respectively lack sufficient future prices for their corresponding horizons.

The actual missing-target count must be determined from the available observations rather than assumed.

## 6. Target Maturity Contract

The maturity stage identifies the future closing session that completes each forward-return target.

The expected maturity columns are:

| Column                     | Meaning                                                        |
| -------------------------- | -------------------------------------------------------------- |
| `target_maturity_date_1d`  | Date of the closing session completing the one-session target  |
| `target_maturity_date_5d`  | Date of the closing session completing the five-session target |
| `target_maturity_date_10d` | Date of the closing session completing the ten-session target  |

For a decision observation at `t`, the maturity date for horizon `h` is the observed trading-session date at position `t+h` for the same ticker.

If the required future session is unavailable, the maturity date must be missing.

The maturity date represents target completion. It does not represent the entry date, the prediction timestamp or the date on which a target first becomes eligible for every possible modelling operation.

The target-generation and maturity-generation stages must use consistent ticker grouping, chronological ordering and horizon definitions.

## 7. Integrated Output Contract

The integrated dataset is expected to retain:

* Original input columns.
* Seven historical feature columns.
* Six target columns.
* Three target maturity columns.

The resulting dataset therefore contains ten newly defined feature and temporal-metadata columns and six target columns, in addition to the original input fields.

The contract does not require a particular physical column order. Column names and meanings must remain stable.

The integration layer must not silently overwrite source prices, duplicate feature or target columns, or misalign generated values with their decision observations.

If a required output column already exists in the input, the implementation must follow an explicit collision policy. It must not silently overwrite existing values.

## 8. Temporal Eligibility and Leakage Prevention

Feature generation, target generation, maturity assignment and temporal eligibility are separate responsibilities.

For a training cutoff `C`, a target is mature only when its required future prices have been observed and its target maturity date is no later than `C`.

Formally, the basic maturity condition is:

$$
\text{target\_maturity\_date}_{h} \leq C
$$

This condition is necessary but may not be sufficient for inclusion in a particular training or evaluation window.

The complete eligibility decision must also respect the approved chronological split, the prediction and training cutoffs, and any purging rules required to prevent overlapping target intervals from contaminating evaluation.

The final test period must not be used for model fitting, feature selection, preprocessing decisions or hyperparameter selection.

Missing feature values caused by insufficient historical lookback must remain distinguishable from missing targets caused by insufficient future observations.

Preprocessing, imputation, scaling and feature selection must be fitted using only the information permitted by the applicable training window.

## 9. Data-Quality Limitations

Correct software behaviour does not establish that the underlying historical price series is economically reliable.

The current `LLOY.L` dataset contains three documented OHLC inconsistencies:

| Date       | Inconsistency    |
| ---------- | ---------------- |
| 2015-03-31 | Close below Low  |
| 2020-06-15 | Open below Low   |
| 2024-05-01 | Close above High |

The project has accepted these anomalies as documented limitations for continued research. The original observations are to be preserved without automatic correction or deletion.

This decision does not certify the entire historical price series or complete corporate-action reconciliation.

The target remains a raw-price return under the approved formula. Any future change to the price basis requires explicit approval.

## 10. Integration Acceptance Criteria

The integrated pipeline may be considered compliant with this contract only after the following criteria have been verified:

1. The existing feature and target functions can be composed without incompatible interfaces.
2. All required feature, target and maturity columns are present.
3. Features use only historical information available at the decision timestamp.
4. Targets follow the approved entry and exit price convention.
5. Target maturity dates correspond to the correct future closing sessions.
6. Calculations do not cross ticker boundaries.
7. Missing features, targets and maturity dates retain their intended meanings.
8. Original input data and row alignment are preserved.
9. Existing columns are not silently overwritten.
10. Training eligibility respects target maturity and the approved temporal validation design.
11. Existing unit tests continue to pass, and any remaining integration gaps are covered by targeted tests.

No model training, backtesting, paper trading or live trading is authorised by this contract.

## 11. Implementation Status

The feature-generation, target-generation and target-maturity components already exist in the project.

Their individual implementations and associated tests must be reused rather than duplicated.

The integrated pipeline is not declared complete solely because its component functions exist. Integration compliance must be established through focused verification against the acceptance criteria above.

**Current status:** Contract proposed; integrated implementation verification pending.
