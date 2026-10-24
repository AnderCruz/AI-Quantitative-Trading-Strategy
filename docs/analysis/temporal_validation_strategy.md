# Temporal Validation and Walk-Forward Modelling Strategy

## 1. Purpose and Scope

This document defines the temporal modelling protocol for the AI Quantitative Trading & Decision Intelligence System.

The initial pilot asset is Lloyds Banking Group (`LLOY.L`), listed on the London Stock Exchange and traded in GBP.

The purpose is to establish a reproducible forecasting process that respects information availability, target maturity, chronological validation and the separation of model development from final evaluation.

This document specifies the methodology. It does not constitute authorisation to train models, generate trading signals, conduct backtesting or begin paper trading.

## 2. Forecast Timestamp and Information Availability

Forecasts are intended to be generated after the close of each observed trading session.

For a forecast made after session `t` closes:

- Features must use only information available by that forecast timestamp.
- No future price, future-derived indicator or subsequently revised information may be used as a predictor.
- The reference entry price remains the Open of session `t+1`.
- The forecast must be stored before its future outcome is evaluated.
- The model version and the information cutoff must be recorded.

The availability of each proposed feature must be reviewed before it is approved for modelling.

## 3. Approved Forecast Targets

The approved gross price-return target for horizon `h` is:

`R(t, h) = Close(t+h) / Open(t+1) - 1`

The approved horizons are:

- 1 trading session;
- 5 trading sessions;
- 10 trading sessions.

The prediction is made after the close of session `t`. The reference entry price is the Open of the next observed trading session, and the reference exit price is the Close of session `t+h`.

These targets exclude transaction costs, slippage, taxes and dividend cash flows.

The target formula and its interpretation must not be changed without explicit approval.

A target is considered mature only when the required future prices are available. Maturity must be calculated using the actual observed trading-session sequence, separately for each horizon.

## 4. Temporal Validation Windows

The approved temporal structure is:

- Development: 7 years;
- Walk-forward Validation: 2 years;
- Final Test: 1 year.

The windows must be derived dynamically from the latest available historical session and aligned to observed trading sessions.

The windows must remain consecutive, without overlap or gaps in observed trading-session order.

The implementation must preserve the approved window durations. Target maturity rules must not be used to shorten or redefine these periods.

Observations outside the approved windows must not be silently added to the evaluation periods.

## 5. Target Maturity and Training Eligibility

Training eligibility must be determined using the actual training cutoff and the maturity date of each target.

The following rules apply:

1. Development training may use observations within the Development period only when their targets have matured by the Development cutoff.
2. During walk-forward validation, training may use eligible observations from Development and earlier Validation observations when their outcomes were known by the relevant retraining cutoff.
3. No observation dated after the training cutoff may enter that training run.
4. No target whose outcome was unknown at the training cutoff may be used as a training label.
5. Eligibility must be evaluated separately for the 1-, 5- and 10-session horizons.
6. Final Test outcomes that have not matured must remain pending rather than being treated as completed results.

The training data available at a retraining date may grow as additional targets mature. It must never include information that became available only after that date.

## 6. Feature Engineering and Preprocessing

Every feature must be reviewed for temporal availability and leakage risk before use.

Feature construction must follow these principles:

- Features for a forecast must be computable using information available at its forecast timestamp.
- Rolling statistics must not include future observations.
- Target columns and future-derived information must never be used as predictors.
- Missing-value handling, scaling, feature selection and other fitted transformations must be fitted using eligible training data only.
- Validation data must not influence fitted preprocessing parameters for the training run being evaluated.
- Any feature-selection or hyperparameter-selection procedure must respect chronological boundaries.

The specific feature set and preprocessing pipeline remain subject to separate design and approval.

## 7. Walk-Forward Training and Forecast Procedure

Forecasts are generated after the close of each observed trading session. The procedure must use only information available by the forecast timestamp.

For each forecast session:

1. Confirm that the session has closed and that the required market data are available.
2. Validate the data required for feature construction and forecasting.
3. Determine whether the session is a scheduled weekly retraining date.
4. If retraining is scheduled, calculate the training eligibility cutoff using information available after that session's close.
5. Include only training observations whose target outcomes have fully matured by the cutoff.
6. Fit preprocessing and the model using the eligible training observations.
7. Verify that training and model validation checks have completed successfully.
8. Record the model version, training cutoff, configuration and relevant data provenance.
9. Generate the forecast for the current session using the successfully trained model.
10. Store the forecast as an immutable record.
11. Evaluate the forecast only after its target has matured.

On a scheduled retraining date, the new model must finish training and pass the required checks before it generates that session's forecast. If retraining fails, the system must not label a forecast as having been produced by the new model. Any fallback to the previous model must follow an explicitly documented and approved failure policy.

On other sessions, the most recently approved model remains in use. The system must not silently change the model between scheduled retraining dates.

The procedure must be tested for temporal correctness before it is used for performance evaluation.

## 8. Retraining Frequency

The approved initial retraining frequency is weekly.

Retraining takes place after the close of the final observed trading session of each week. If Friday is not a trading session, the final observed session of that week is used.

The operational sequence on a retraining date is:

1. Confirm the session close and data availability.
2. Establish the information cutoff for that session.
3. Recalculate training eligibility separately for each forecast horizon.
4. Exclude observations whose target outcomes have not matured by the cutoff.
5. Fit preprocessing and train the model using eligible observations only.
6. Run the required training and model checks.
7. Record the model version, training cutoff, configuration and data provenance.
8. Authorise the new model only after all required checks have passed.
9. Generate and record the forecast for that session only after successful training and authorisation.

On sessions that are not scheduled retraining dates, generate the forecast after the close using the most recently authorised model. Do not retrain the model on those sessions.

### Retraining Failure Policy

If scheduled retraining fails, the system must:

- Preserve the last successfully authorised model and its artefacts.
- Not activate the previous model automatically for new forecasts.
- Not issue a new forecast until a model has been explicitly authorised for use.
- Record the failed retraining attempt, its cutoff, the affected forecast session and the failure reason.
- Record that no forecast was issued for the affected session.
- Resume forecasting only after a model has passed the required checks and has been authorised.

A retraining failure must not overwrite or alter previously recorded forecasts. Missing forecasts must remain explicitly identifiable and must not be represented as successful predictions.

The implementation must test this failure policy, including the preservation of the previous model and the prevention of unauthorised forecasts.

The weekly frequency and this failure policy are the approved initial protocol. Any change must be documented and approved before implementation.

## 9. Forecast Recording and Traceability

Each forecast record should retain, at minimum:

- Asset ticker;
- Forecast timestamp;
- Forecast horizon;
- Predicted return;
- Model identifier and version;
- Training cutoff;
- Forecast reference entry session;
- Expected target maturity session;
- Target value, once available;
- Evaluation status, such as pending or matured.

Forecast records must be immutable with respect to the original prediction. Later model versions must not overwrite earlier forecasts.

The storage format and implementation remain to be designed and tested.

## 10. Evaluation Protocol

Evaluation must be chronological and must distinguish model forecasting performance from trading performance.

Forecasts must be evaluated separately for the 1-, 5- and 10-session horizons.

Only matured targets may contribute to completed forecast metrics. Pending targets must be reported separately.

The evaluation design must specify suitable metrics, baselines, aggregation rules and treatment of overlapping forecast horizons before model evaluation begins.

Forecast accuracy alone must not be interpreted as evidence of trading profitability.

Any future trading simulation must separately address transaction costs, slippage, applicable taxes, dividends where relevant, and realistic execution assumptions.

## 11. Final Test Isolation

The Final Test period is reserved for final evaluation.

Its outcomes must not be used for:

- Feature selection;
- Preprocessing design based on observed outcomes;
- Hyperparameter optimisation;
- Model selection;
- Threshold selection;
- Strategy selection or iterative strategy refinement.

The Final Test must not influence decisions that are subsequently presented as out-of-sample evaluation.

Predictions must be recorded according to the approved forecasting procedure. Outcomes must remain pending until their targets mature.

Any proposal to use Final Test results to revise the system requires a clearly documented new evaluation design and explicit approval.

## 12. Outstanding Risks and Limitations

The following items require further review before modelling is authorised:

1. Feature definitions and their point-in-time availability.
2. Preprocessing and model-fitting implementation.
3. Model families, baselines and hyperparameter-selection procedure.
4. Evaluation metrics and forecast aggregation rules.
5. Forecast storage and model-version traceability.
6. The treatment of the two previously documented OHLC inconsistencies.
7. Corporate actions, dividends and the limitations of the selected price series.
8. Transaction costs and execution assumptions for any future backtest.
9. Integration tests demonstrating that the complete pipeline respects temporal boundaries.

Passing target-maturity tests does not prove that the entire future modelling pipeline is free from data leakage.

## 13. Approval Gate

Before model training is authorised, the project must complete and review:

- The feature availability specification;
- The preprocessing design;
- The walk-forward training and forecasting implementation;
- Forecast storage and traceability requirements;
- The evaluation protocol;
- Tests covering temporal eligibility and leakage controls.

The weekly retraining frequency is approved as the initial methodological choice. The remaining design and implementation requirements still require review.

No model training, hyperparameter optimisation, trading backtest or paper trading is authorised by this document alone.

Explicit approval is required before proceeding to model training.

## 14. Conclusion

This protocol establishes the intended temporal framework for producing daily forecasts with weekly model retraining.

Its purpose is to ensure that training labels are mature at each retraining cutoff, features respect information availability, historical forecasts remain traceable and the Final Test remains isolated from model selection.

The protocol must be implemented, tested and reviewed before model training or backtesting begins.
