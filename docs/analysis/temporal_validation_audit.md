# Temporal Validation and Target Maturity Audit

## 1. Purpose

This document records the temporal validation checks performed for the initial quantitative trading pilot using Lloyds Banking Group (`LLOY.L`).

The purpose of the audit is to verify the implementation of the approved temporal boundaries, forward-return targets, target maturity rules and walk-forward training eligibility.

The audit does not establish that the complete future modelling pipeline is free from data leakage. Feature engineering, preprocessing, model fitting, forecasting and performance evaluation require separate verification.

## 2. Asset and Historical Data

| Attribute                         | Value                        |
| --------------------------------- | ---------------------------- |
| Pilot asset                       | Lloyds Banking Group         |
| Ticker                            | `LLOY.L`                     |
| Exchange                          | London Stock Exchange        |
| Trading currency                  | GBP                          |
| Data provider                     | Yahoo Finance                |
| First historical session          | 2 January 2015               |
| Latest historical session audited | 23 October 2026              |
| Historical observations           | 2,985                        |
| Forecast horizons                 | 1, 5 and 10 trading sessions |

The historical dataset is stored at:

`data/raw/yahoo/configured/LLOY.L.csv`

Two previously identified OHLC inconsistencies remain preserved in the source data, in accordance with the existing project decision:

* 31 March 2015: Close is 78.279999, below Low at 78.300003.
* 1 May 2024: Close is 52.200001, above High at 52.139999.

These anomalies must remain documented. Their treatment and potential impact must be considered separately before the affected observations are used in modelling or simulated execution.

## 3. Approved Forecast Targets

The approved target formula for horizon \(h\) is:

$$
R(t,h)=\frac{Close(t+h)}{Open(t+1)}-1
$$

The prediction is made after the close of session \(t\). The reference entry price is the Open of the next trading session, and the reference exit price is the Close of session \(t+h\).

The approved horizons are:

* 1 trading session;
* 5 trading sessions;
* 10 trading sessions.

The targets represent gross price returns before transaction costs, slippage, taxes and dividend cash flows.

The target formula must not be changed without explicit approval.

## 4. Temporal Validation Windows

The approved temporal structure uses seven years for Development, two years for Walk-forward Validation and one year for the Final Test.

The windows are derived dynamically from the latest available historical session and aligned to observed trading sessions.

| Period      | Start           | End             | Observations |
| ----------- | --------------- | --------------- | -----------: |
| Development | 24 October 2016 | 20 October 2023 |        1,766 |
| Validation  | 23 October 2023 | 22 October 2025 |          507 |
| Final Test  | 23 October 2025 | 23 October 2026 |          254 |

The periods are consecutive in trading-session order. Their boundaries do not overlap, and there are no gaps between the final session of one period and the first session of the next.

Historical observations before the Development window are outside the approved 7/2/1-year evaluation structure.

## 5. Target Maturity Rules

A target is eligible for training only when its outcome is fully observable by the relevant training cutoff.

Target maturity is calculated separately for each forecast horizon using actual observed trading sessions rather than calendar-day approximations.

The following rules apply:

1. Development training may only use observations within Development whose targets have matured by the Development cutoff.
2. Walk-forward training may use eligible observations from Development and earlier Validation observations, provided their targets were known by the actual retraining cutoff.
3. Observations dated after the retraining cutoff must never enter that training set.
4. Targets that have not matured must remain ineligible for training and must not be scored as completed outcomes.
5. Final Test predictions whose outcomes have not matured must remain pending until the relevant future prices become available.

The approved temporal periods must remain unchanged when applying these eligibility rules.

## 6. Development Eligibility Results

The Development period contains 1,766 observations.

| Horizon     | Eligible observations | Excluded observations |
| ----------- | --------------------: | --------------------: |
| 1 session   |                 1,765 |                     1 |
| 5 sessions  |                 1,761 |                     5 |
| 10 sessions |                 1,756 |                    10 |

The exclusions correspond to targets that had not matured by the Development period end.

These results are consistent with the requirement to exclude unavailable future outcomes from training.

## 7. Final Test Target Maturity

The Final Test period contains 254 observations.

The audit reported the following target maturity results:

| Horizon     | Valid targets | Matured by latest available session | Pending at latest session |
| ----------- | ------------: | ----------------------------------: | ------------------------: |
| 1 session   |           253 |                                 253 |                         1 |
| 5 sessions  |           249 |                                 249 |                         5 |
| 10 sessions |           244 |                                 244 |                        10 |

The pending observations must not be treated as completed outcomes when evaluating forecast accuracy or trading performance.

The Final Test must remain isolated from model selection and parameter tuning.

## 8. Exhaustive Walk-forward Eligibility Audit

The walk-forward audit examined every observed Validation session as a retraining cutoff.

| Audit measure              | Result |
| -------------------------- | -----: |
| Validation cutoffs checked |    507 |
| Forecast horizons          |      3 |
| Successful horizon checks  |  1,521 |
| Audit outcome              |   PASS |

At each cutoff, the audit checked that:

* No observation dated after the cutoff was eligible.
* Every eligible target had a non-missing maturity date.
* Every eligible target had matured by the cutoff.
* Previously eligible observations remained eligible as the cutoff advanced.

All 1,521 horizon checks passed.

This confirms the tested behaviour of the target maturity and training eligibility functions across the observed Validation cutoffs.

It does not demonstrate that model features, preprocessing, hyperparameter selection or forecast generation are independently free from data leakage.

## 9. Automated Test Results

The complete automated test suite was executed using:

`PYTHONPATH=. pytest -q`

Recorded result:

`66 passed in 1.24s`

The exhaustive temporal audit was executed using:

`PYTHONPATH=. python scripts/audit_lloy_temporal_eligibility.py`

Recorded result:

`EXHAUSTIVE WALK-FORWARD AUDIT PASSED.`

These results record the outcomes of the executed tests and audit. They do not replace future integration tests or an independent review of the modelling pipeline.

## 10. Outstanding Risks and Limitations

Before model training is authorised, the project must address the following areas:

1. **Feature availability:** Every feature must be constructed using information available at the relevant prediction timestamp.
2. **Preprocessing leakage:** Imputation, scaling, feature selection and other fitted transformations must be estimated using eligible training data only.
3. **Walk-forward protocol:** The retraining frequency, forecast timestamps and evaluation procedure must be specified precisely.
4. **Model selection:** Hyperparameter tuning and model selection must not use Final Test outcomes.
5. **Pending outcomes:** Predictions must remain unevaluated until their targets mature.
6. **Execution realism:** Future backtesting must account for transaction costs, slippage, applicable taxes and the limitations of execution-price assumptions.
7. **OHLC anomalies:** The two documented historical inconsistencies require explicit treatment before affected prices are relied upon for execution simulation.
8. **Data updates:** The period boundaries and maturity calculations must remain dynamic when newer historical sessions become available.

Forecast accuracy must not be interpreted as evidence of trading profitability.

## 11. Project Status and Approval Gate

The temporal eligibility implementation has passed the recorded unit tests and exhaustive Validation-cutoff audit.

The following activities have not been performed as part of this audit:

* Model training;
* Hyperparameter optimisation;
* Forecast generation for a trading strategy;
* Backtesting;
* Paper trading;
* Live trading.

The next stage is to specify and review the walk-forward modelling protocol, including feature construction, preprocessing, retraining frequency, forecast storage and evaluation timing.

Model training must not begin until the relevant design and data-leakage controls have been reviewed and explicitly approved.

## 12. Audit Conclusion

The recorded results support the conclusion that the implemented target maturity and temporal eligibility checks passed for the tested LLOY.L historical data and all 507 observed Validation cutoffs.

This is a necessary foundation for the modelling workflow, not a guarantee of future predictive performance, trading profitability or complete pipeline integrity.

Further review and explicit approval are required before model training and backtesting.
