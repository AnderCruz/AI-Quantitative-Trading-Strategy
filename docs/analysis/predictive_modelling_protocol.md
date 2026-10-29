# Predictive Modelling Protocol

**Project:** AI Quantitative Trading & Decision Intelligence System  
**Pilot asset:** Lloyds Banking Group (`LLOY.L`)  
**Market:** London Stock Exchange  
**Currency:** GBP  
**Status:** Reconciled draft — submitted for approval  
**Normative relationship:** Supporting modelling roadmap under `model_development_and_evaluation_protocol.md`; detailed metric and inference rules are defined in `model_evaluation_protocol.md`.

## 1. Objective and Scope

This document describes the project's initial predictive-modelling sequence and records future candidate model families and research questions. It must be read alongside the primary Model Development and Evaluation Protocol, the detailed Model Evaluation Protocol, the temporal validation strategy, and the feature/target data contracts.

Forecast accuracy is not evidence of trading profitability. This document does not, by itself, authorise model training, confirmatory evaluation, backtesting, paper trading or live trading. The project's explicit approval gates remain mandatory.

## 2. Approved Forecast Targets

The existing target definition must remain unchanged:

\[
R(t,h)=\frac{Close(t+h)}{Open(t+1)}-1
\]

Approved forecast horizons:
- 1 trading session;
- 5 trading sessions; and
- 10 trading sessions.

Predictions are generated after the close of session \(t\). The target represents a gross price return from the next session's open to the close at the specified horizon. It excludes transaction costs, slippage, taxes and dividend cash flows. These exclusions must remain explicit in all interpretation and reporting.

Target generation, maturity, eligibility and forecast timing are governed by the integrated feature/target pipeline contract and the primary development and evaluation protocol. A target must not be used for fitting or evaluation before it has matured.

## 3. Data and Temporal Splits

Use the approved chronological partitions:

| Partition | Start | End | Purpose |
|---|---|---|---|
| Development | 2016-10-24 | 2023-10-20 | Model development and fitting, after explicit authorisation |
| Validation | 2023-10-23 | 2025-10-22 | Model and configuration selection under the approved protocol |
| Final Test | 2025-10-23 | 2026-10-23 | Final evaluation only, after separate authorisation |

Random train-test splitting is prohibited for the primary evaluation. The Final Test must not influence feature selection, model selection, hyperparameters, preprocessing, thresholds, resampling settings, strategy decisions or other development choices. Only matured outcomes may contribute to completed evaluation metrics; pending outcomes remain pending.

These boundaries do not independently authorise any training or Final Test activity. The primary protocol's gates and the temporal validation strategy remain controlling.

## 4. Walk-Forward Training and Forecasting

The approved temporal approach is chronological walk-forward forecasting with weekly retraining, subject to the applicable project gates.

At each authorised retraining cutoff:

1. Use only information available at that cutoff.
2. Include only training targets that have matured by the cutoff and satisfy the horizon-specific eligibility rules.
3. Fit learned preprocessing and model parameters using eligible training data only.
4. Generate forecasts for the subsequent evaluation period using the frozen model and preprocessing version.
5. Record forecasts, timestamps, asset, horizon, cutoff, model and preprocessing versions, data provenance and experiment identifiers.
6. Evaluate outcomes only after the corresponding targets have matured.
7. Record failures, missing forecasts, exclusions and reasons; do not silently substitute zero forecasts.

An expanding training window is the initial window policy. Any change to the window policy or retraining schedule must be justified, documented and approved before experiments that depend on it. Do not use a later outcome to alter an earlier forecast or training cutoff.

## 5. Leakage Prevention

The following controls are mandatory:

- Calculate features only from information available at the forecast timestamp.
- Fit scalers, imputers, selectors and any other learned preprocessing only on eligible training data within the applicable cutoff.
- Keep target generation separate from feature engineering.
- Prevent target and rolling calculations from crossing asset boundaries.
- Exclude immature targets from training.
- Preserve chronological ordering and apply the approved maturity and eligibility rules.
- Do not use Final Test outcomes for development decisions.
- Consider overlapping targets when specifying statistical inference; do not treat overlapping observations as independent merely because their timestamps differ.
- Any purging, embargo or additional dependence control must be specified and approved before use; do not introduce it retrospectively to favour a result.

## 6. Initial Model Sequence

The initial modelling sequence is deliberately limited and follows the primary development protocol.

### 6.1 Regression baselines

Evaluate the required baselines separately for each horizon and under the same cutoff, maturity, eligibility and evaluation-sample rules:

1. **Zero Return**;
2. **Historical Mean**; and
3. **Historical Median** as a required complementary comparison baseline.

The Historical Mean and Historical Median must use only eligible, matured historical targets available at the relevant cutoff.

### 6.2 First supervised regression candidate

**Ridge Regression** is the first supervised trainable regression model in the approved initial sequence. It must be compared with the required baselines using the metrics and paired-comparison procedures in `model_evaluation_protocol.md`.

No other supervised regression family is part of the initial approved sequence unless a later, explicit protocol amendment authorises it.

### 6.3 Classification sequence

Classification work may proceed only after the prepared dataset has been verified to contain `positive_return_1d`, `positive_return_5d` and `positive_return_10d`, including the maturity status and horizon-specific eligibility required by the protocol.

The initial classification sequence is:
1. a constant-probability baseline equal to the positive-class prevalence among eligible, matured training labels at the relevant cutoff and horizon; then
2. **Logistic Regression** as the first supervised classification candidate.

The label is 1 for a strictly positive realised return and 0 for a zero or negative realised return. Invalid or unavailable returns produce missing labels. Classification training remains subject to the approved minimum sample and class-count requirements.

## 7. Future Model-Family Roadmap

The following families were recorded as possible future research candidates in the earlier modelling plan. They are **not part of the initial approved modelling sequence and are not authorised for implementation or training by this document**. Introducing any of them requires a documented rationale, an assessment of incremental value and complexity, consistency with the primary protocol, and explicit approval before the relevant experiment.

### Statistical candidates
- Linear Regression as an additional reference, if a distinct purpose from the required baselines and Ridge Regression is established;
- ARIMA using Statsmodels;
- SARIMA only if exploratory evidence supports a seasonal hypothesis;
- GARCH for conditional-volatility or risk analysis, recognising that this is not directly interchangeable with a conditional-mean return forecast;
- Prophet as an optional secondary experiment, subject to justification.

### Machine-learning candidates
- Random Forest;
- XGBoost;
- LightGBM; and
- Support Vector Regression.

### Deep-learning candidates
- Multi-Layer Perceptron (MLP);
- Long Short-Term Memory (LSTM);
- Gated Recurrent Unit (GRU);
- Temporal Convolutional Network (TCN); and
- Transformer models only if earlier results justify the additional complexity.

The inclusion of a family in this roadmap is not a claim of suitability or superiority. Candidates must not be added merely to increase the number of experiments. The Final Test must remain isolated from model-family selection.

## 8. Features and Exploratory Analysis

Reuse the approved feature-engineering specification and its seven derived features as the starting point:

- `close_return_1d`;
- `close_return_5d`;
- `close_return_10d`;
- `close_return_20d`;
- `close_volatility_5d`;
- `close_volatility_10d`; and
- `close_volatility_20d`.

Do not add, remove or redefine features without following the project's feature-change and approval process.

The earlier research plan identified the following topics for EDA review where not already addressed by the approved evidence:
- return distributions and extreme observations;
- stationarity and autocorrelation;
- volatility clustering;
- feature-target relationships;
- temporal stability; and
- feature redundancy.

These are review topics, not evidence that any additional analysis has been executed or that any unresolved question has been answered. Any new feature or analysis must have a documented rationale, respect information availability at the forecast timestamp and avoid use of Final Test outcomes for development decisions. Before training, the project must confirm which outstanding EDA items are prerequisites under the primary protocol and record their status.

## 9. Evaluation Metrics and Statistical Comparison

The detailed rules in `model_evaluation_protocol.md` are normative. This section is a concise index, not a replacement for that protocol.

Primary regression metrics:
- Mean Absolute Error (MAE);
- Root Mean Squared Error (RMSE).

Complementary regression diagnostics:
- Directional Accuracy (DA);
- Spearman rank correlation;
- out-of-sample \(R^2\); and
- mean forecast error where useful.

Evaluate each horizon separately. Compare models on common valid forecast dates and realised outcomes wherever possible. Use the approved exact-zero convention for DA and the approved missingness policy. Report sample sizes, exclusions, uncertainty and limitations.

Overlapping 5-session and 10-session targets induce temporal dependence. Use the approved HAC/Newey–West lag rules and Moving Block Bootstrap procedure, including the documented sensitivity settings, paired resampling, temporal-gap handling, seed and replication counts. Apply the predeclared multiple-testing procedure for confirmatory comparisons. Do not select a method, lag, block length or hypothesis-family boundary because it produces a more favourable result.

The operational sample thresholds in the primary and detailed evaluation protocols are eligibility rules, not guarantees of statistical power or evidence of practical significance. Practical-improvement thresholds and confirmatory hypothesis-family membership remain open until explicitly specified and approved.

## 10. Experiment Reproducibility

For every authorised experiment, record at least:
- asset, horizon and target definition;
- data version, source and coverage;
- feature definitions and order;
- training cutoff, split boundaries, maturity and eligibility rules;
- preprocessing configuration and fitted-artifact version;
- model family, configuration and version;
- forecast timestamps and predictions;
- experiment identifier and code revision;
- random-number-generator seed where applicable;
- software and dependency versions;
- metrics, paired sample definitions and statistical comparisons;
- missingness, exclusions, warnings and failures; and
- the applicable gate/authorisation status.

Documentation of a planned procedure is not evidence that it has been implemented or executed. No model fitting, bootstrap, statistical test or backtest is claimed by this document.

## 11. Future Strategy-Evaluation Stage

The earlier project plan records a hypothetical portfolio value of **GBP 1,000** for a later strategy-evaluation stage. This is a future planning assumption only. Portfolio accounting, position sizing, execution timing, transaction costs, slippage, taxes, dividend treatment, liquidity constraints and order-fill assumptions require a separate strategy specification and explicit approval.

This document does not authorise strategy backtesting, paper trading or live trading. Forecast performance and economic performance must remain distinct. The target defined in Section 2 is a gross price-return target and does not include dividend cash flows or trading costs.

## 12. Approval Gates and Restrictions

The project's gates remain controlling:

- **Gate A — Methodology approval:** approval of the complete consolidated methodology, not merely isolated decisions.
- **Gate B — Technical validation:** evidence that implementation and controls behave as specified; this does not establish predictive superiority or economic usefulness.
- **Gate C — Training authorisation:** explicit approval before fitting learned preprocessing, fitting any model or conducting model experiments.
- **Gate D — Backtesting authorisation:** separate explicit approval before backtesting.
- Paper trading and live trading require separate explicit approval.

Approval of this supporting document, or of an individual methodological decision, does not by itself mean that all gates have passed. Training authorisation does not authorise forecasts or trading signals to be made operational. Operational authorisation applies to a specific model version, asset and horizon after the applicable requirements have been met.

The Final Test remains isolated until the authorised final evaluation stage. Any change prompted by Final Test results constitutes a new research iteration; the same period must not be represented as an untouched test set for a revised design.

## 13. Related Normative Documents

Apply these documents together, in the following order of authority:

1. `docs/analysis/model_development_and_evaluation_protocol.md` — primary methodology, development sequence and approval gates.
2. `docs/analysis/model_evaluation_protocol.md` — detailed metrics, baselines, inference, bootstrap, sample adequacy and reporting.
3. `docs/analysis/temporal_validation_strategy.md` — temporal cutoffs, weekly retraining, maturity and failure handling.
4. `docs/analysis/temporal_validation_audit.md` — evidence and audit record for temporal validation.
5. `docs/analysis/feature_engineering_specification.md` — approved feature definitions and preprocessing rules.
6. `docs/data/integrated_feature_target_pipeline_contract.md` — technical data, feature, target, maturity and eligibility contract.
7. `docs/data/model_dataset_preparation_contract.md`, `docs/data/target_definition.md`, `docs/data/price_series_policy.md`, `docs/data/asset_and_data_source_selection.md`, `docs/analysis/c1_data_quality_and_historical_coverage.md` and `docs/analysis/drawdown_methodology.md` — applicable supporting data, target, quality and future risk-analysis references.

If a discrepancy is found, do not silently resolve it in code or choose whichever document is more convenient. Record the discrepancy and reconcile the documents under the approved hierarchy before the affected activity proceeds.

## Conclusion

This document preserves the project's modelling roadmap while limiting the initial sequence to the approved baselines, Ridge Regression, and—after dataset readiness verification—the classification prevalence baseline followed by Logistic Regression. It preserves the existing target, temporal partitions, weekly walk-forward approach, feature starting point, outstanding EDA review topics and future GBP 1,000 strategy-evaluation assumption. All training and evaluation activities remain subject to the project's explicit gates.
