# Feature Engineering and Preprocessing Specification

## 1. Purpose

This document defines the initial feature engineering and preprocessing methodology for the AI Quantitative Trading & Decision Intelligence System.

Its purpose is to establish a reproducible framework for constructing historical return and volatility features while preventing data leakage and preserving the integrity of the original market data.

The initial implementation will focus on Lloyds Banking Group (`LLOY.L`), listed on the London Stock Exchange.

The approved data source is Yahoo Finance, accessed through the `yfinance` library.

This specification defines the approved initial feature set. It does not authorise model training, hyperparameter optimisation, backtesting or paper trading.

## 2. Forecasting Context

### 2.1 Forecast Timing

Forecasts will be generated after the close of an observed trading session \(t\).

All features must use information available no later than the forecast cutoff at session \(t\).

### 2.2 Approved Forecast Horizons

The system will forecast returns over the following horizons:

* 1 trading session;
* 5 trading sessions;
* 10 trading sessions.

### 2.3 Approved Target Definition

The target return is defined as:

$$
R(t,h)=\frac{Close(t+h)}{Open(t+1)}-1
$$

Where:

* \(t\) is the forecast session;
* \(h\) is the forecast horizon in trading sessions;
* \(Open(t+1)\) is the opening price of the next trading session;
* \(Close(t+h)\) is the closing price at the specified future horizon.

This target definition has been explicitly approved and must not be changed without further approval.

The target represents a gross execution-price return before transaction costs, slippage, taxes and dividend cash flows.

## 3. Initial Feature Set

The initial feature set consists of seven candidate variables derived from historical closing prices.

### 3.1 Historical Returns

Historical returns measure the cumulative price change over a specified number of trading sessions.

For a lookback window of \(k\) sessions:

$$
r_{t,k}=\frac{Close_t}{Close_{t-k}}-1
$$

The following features are approved:

| Feature            | Lookback window | Definition                 |
| ------------------ | --------------: | -------------------------- |
| `close_return_1d`  |       1 session | \(Close_t/Close_{t-1}-1\)  |
| `close_return_5d`  |      5 sessions | \(Close_t/Close_{t-5}-1\)  |
| `close_return_10d` |     10 sessions | \(Close_t/Close_{t-10}-1\) |
| `close_return_20d` |     20 sessions | \(Close_t/Close_{t-20}-1\) |

Returns will be expressed as decimal proportions rather than percentages.

For example, a return of 0.05 represents a 5% price increase.

These features must be calculated using historical observations only.

### 3.2 Historical Volatility

Historical volatility measures the variability of recent one-session returns.

First, the one-session return is calculated as:

$$
r_t=\frac{Close_t}{Close_{t-1}}-1
$$

For a rolling window containing \(k\) valid daily returns, historical volatility is defined as the sample standard deviation:

$$
\sigma_{t,k}=
\sqrt{
\frac{1}{k-1}
\sum_{i=0}^{k-1}
(r_{t-i}-\bar{r}_{t,k})^2
}
$$

Where:

* \(k\) is the number of daily returns in the window;
* \(r_{t-i}\) is a one-session return;
* \(\bar{r}_{t,k}\) is the arithmetic mean of the returns within the window.

The following features are approved:

| Feature                |   Rolling window | Definition                                                   |
| ---------------------- | ---------------: | ------------------------------------------------------------ |
| `close_volatility_5d`  |  5 daily returns | Sample standard deviation of the latest five daily returns   |
| `close_volatility_10d` | 10 daily returns | Sample standard deviation of the latest ten daily returns    |
| `close_volatility_20d` | 20 daily returns | Sample standard deviation of the latest twenty daily returns |

The calculation will use a sample standard deviation with `ddof=1`.

Volatility will not be annualised in the initial implementation.

A window must contain the full number of valid daily returns required by its definition. Missing historical observations must not be silently replaced.

## 4. Momentum Feature Policy

No separate momentum feature family will be included in the initial feature set.

The proposed cumulative momentum measures would be mathematically identical to the approved historical return features.

Creating additional variables with identical definitions would introduce unnecessary duplication without adding information.

Any future momentum indicators must have a distinct mathematical definition and require a separate methodological justification.

## 5. Source Data Policy

The source dataset contains the following fields:

* `date`
* `Open`
* `High`
* `Low`
* `Close`
* `Adj Close`
* `Volume`
* `Dividends`
* `Stock Splits`
* `ticker`

The initial features will be derived exclusively from `Close`.

The remaining fields will not be included in the initial feature set.

### 5.1 Closing Prices

The original `Close` values will be retained for the approved target definition and initial historical return calculations.

No automatic adjustment, interpolation or replacement of closing prices is authorised by this specification.

### 5.2 Adjusted Closing Prices

`Adj Close` will not be used directly as an initial model feature.

Its methodology, historical revision behaviour and suitability for retrospective feature construction must be reviewed before any future use is approved.

### 5.3 Other OHLC Fields and Volume

`Open`, `High`, `Low` and `Volume` are excluded from the initial feature set.

Their potential inclusion may be evaluated separately after the initial price-based features and preprocessing rules have been reviewed.

### 5.4 Corporate Actions

`Dividends` and `Stock Splits` are excluded from the initial feature set.

Any future use must account for the information actually available at the forecast cutoff and the treatment of corporate actions in historical data.

## 6. Data Validation

Before feature construction, the preprocessing pipeline must validate the source dataset.

The required checks are:

1. Convert `date` into an appropriate datetime representation.
2. Sort observations chronologically.
3. Check uniqueness of each `ticker` and `date` combination.
4. Check that required closing prices are finite and positive.
5. Identify missing values in the required source fields.
6. Identify duplicate observations.
7. Record data-quality anomalies without silently modifying the original data.

The original source data must remain traceable.

Validation failures and excluded observations must be documented.

## 7. Known OHLC Anomalies

Two observations have previously been identified as inconsistent with the expected OHLC relationships:

* 31 March 2015: `Close < Low`.
* 1 May 2024: `Close > High`.

These observations must remain documented.

The original source values must not be automatically corrected or deleted.

The initial features depend on `Close` rather than `High` or `Low`. Therefore, an OHLC inconsistency alone does not automatically invalidate every feature calculated from the affected observation.

The closing prices and adjacent observations must be investigated separately if evidence suggests that the values may be incorrect.

Any subsequent exclusion or correction requires a documented rule and an explicit justification.

## 8. Missing Values Generated by Feature Engineering

Historical rolling calculations naturally produce missing values at the beginning of the dataset.

Examples include:

* `close_return_1d` requires one previous closing price.
* `close_return_5d` requires five previous closing prices.
* `close_return_10d` requires ten previous closing prices.
* `close_return_20d` requires twenty previous closing prices.
* `close_volatility_20d` requires twenty valid one-session returns, which in turn require sufficient preceding closing-price observations.

These missing values represent insufficient historical information rather than necessarily indicating a source-data defect.

The initial policy is:

1. Do not artificially fill unavailable historical features.
2. Do not use future observations to impute missing values.
3. Preserve the reason for each missing feature where practical.
4. Exclude observations that do not satisfy the feature requirements of the relevant model.
5. Record exclusions and their reasons.

Any future imputation method must be specified separately and must respect the temporal information boundary.

## 9. Prevention of Data Leakage

The maximum information date used by a feature must not exceed its forecast cutoff:

$$
\boxed{\text{Maximum information date}\leq t}
$$

All approved features must satisfy this condition.

The following controls are mandatory:

* Historical calculations must use observations available no later than session \(t\).
* Future closing prices must not enter feature calculations.
* Target values must not be used to construct features.
* Feature transformations must not use information from validation or final-test periods to estimate parameters.
* Any scaling or learned preprocessing must be fitted exclusively on the eligible training data available at the relevant cutoff.
* Feature construction must preserve chronological ordering.
* The training pipeline must respect the previously approved target-maturity and temporal-eligibility rules.

The weekly retraining policy remains unchanged. Forecasts will be generated after each observed trading session close, while the model is retrained after the close of the last observed session of each week.

## 10. Relationship with Temporal Validation

Feature construction must remain compatible with the approved temporal framework:

* Development period: seven years.
* Walk-forward validation period: two years.
* Final-test period: one year.

The periods are consecutive, non-overlapping and dynamically determined from the latest available session in the selected asset's historical data.

For every training cutoff, the training dataset must contain only observations whose relevant target outcomes have matured by that cutoff.

Feature availability and target maturity are separate requirements. An observation with valid features is not automatically eligible for training if its target outcome is not yet known.

The final-test period must remain isolated from feature selection, model selection, hyperparameter selection and threshold selection.

## 11. Approved Initial Feature Register

The following seven features constitute the approved initial feature specification.

| Feature                | Family                |      Window | Approved method           |
| ---------------------- | --------------------- | ----------: | ------------------------- |
| `close_return_1d`      | Historical return     |   1 session | Cumulative price return   |
| `close_return_5d`      | Historical return     |  5 sessions | Cumulative price return   |
| `close_return_10d`     | Historical return     | 10 sessions | Cumulative price return   |
| `close_return_20d`     | Historical return     | 20 sessions | Cumulative price return   |
| `close_volatility_5d`  | Historical volatility |   5 returns | Sample standard deviation |
| `close_volatility_10d` | Historical volatility |  10 returns | Sample standard deviation |
| `close_volatility_20d` | Historical volatility |  20 returns | Sample standard deviation |

The register defines the initial feature set, not a claim that all seven features will necessarily improve forecasting performance.

Their practical contribution must be assessed only within the approved evaluation framework.

## 12. Implementation and Approval Boundaries

This document records the approved initial feature engineering and preprocessing methodology.

The next implementation stage must:

1. Translate the approved formulas into reproducible code.
2. Add automated tests for the feature calculations.
3. Verify chronological alignment and information availability.
4. Test missing-value behaviour and data-quality controls.
5. Confirm compatibility with the existing target-generation and temporal-eligibility components.
6. Review implementation results before authorising subsequent modelling work.

No model training, hyperparameter optimisation, backtesting or paper trading is authorised by this specification alone.

## Conclusion

The initial feature engineering approach prioritises transparent mathematical definitions, reproducibility and strict temporal information boundaries.

The first implementation will contain four historical return features and three historical volatility features derived from closing prices.

The source data will remain traceable, known anomalies will be documented, and unavailable historical features will not be filled using future information.

Any expansion of the feature set or change to the approved target definition requires further methodological review and explicit approval.
