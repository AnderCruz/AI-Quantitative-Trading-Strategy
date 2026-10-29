# Model Development and Evaluation Protocol

**Project:** AI Quantitative Trading & Decision Intelligence System  
**Pilot asset:** `LLOY.L` (Lloyds Banking Group, London Stock Exchange, GBP)  
**Status:** Consolidated draft — approved methodological decisions incorporated; implementation and model-training gates remain in force  
**Document role:** Primary normative protocol for model development, validation, evaluation and authorisation  
**Related protocol:** [`model_evaluation_protocol.md`](model_evaluation_protocol.md)  
**Market-data source:** Yahoo Finance, accessed through `yfinance`  
**Excluded unless separately authorised:** Model fitting and experiments, confirmatory evaluation, trading backtests, paper trading and live trading

## 1. Purpose and Scope

This protocol defines the controlled process for developing, validating, comparing and authorising predictive models in the AI Quantitative Trading & Decision Intelligence System.

The initial pilot uses `LLOY.L`. Results from this asset must not be assumed to generalise to other equities, exchanges, currencies or market regimes. The intended system must ultimately allow a user to select any supported eligible equity listed on the NYSE, Nasdaq or London Stock Exchange. Before forecasts or trading signals are made available for a selected equity, the system must prepare the applicable data and train and validate a model specific to that equity under this protocol.

The protocol governs predictive research. It does not establish that a forecast is economically useful or that a trading strategy is profitable.

The objectives are to:

1. define reproducible targets, features, baselines and evaluation procedures;
2. prevent look-ahead bias, temporal leakage and the use of immature labels;
3. enforce chronological development, validation and Final Test isolation;
4. assess regression and, after dataset readiness is verified, classification models;
5. compare candidate models on common observations and against predefined baselines;
6. quantify uncertainty while accounting for temporal dependence and multiple comparisons;
7. make model-family selection distinct from authorisation of an individual trained-model version; and
8. preserve traceability of decisions, runs, forecasts, failures and artefacts.

## 2. Normative Language and Document Precedence

“Must” and “must not” express mandatory requirements. “Should” expresses a strong recommendation that may be departed from only with documented justification. “May” identifies a permitted option.

This document is the primary normative protocol for model development and approval gates. The dedicated `model_evaluation_protocol.md` provides the detailed evaluation definitions and statistical procedures. The approved temporal-validation strategy governs the chronological cutoffs, retraining schedule and maturity rules. The feature specification and integrated feature-target pipeline contract govern the contracted feature and target construction.

Where a technical implementation detail is not defined in this document or its approved supporting contracts, it must be documented and reviewed before it affects model results. Supporting documents must not silently contradict this protocol.

## 3. Forecast Targets and Timing

### 3.1 Regression target

For observation session \(t\) and horizon \(h\), the target is the forward gross price return:

\[
R(t,h)=\frac{Close(t+h)}{Open(t+1)}-1
\]

The forecast is assumed to be produced after the close of session \(t\), with entry at the next observed trading session’s open and exit at the close of the session \(h\) trading sessions after \(t\), as defined by the project’s target-generation contract.

The approved horizons are \(h \in \{1,5,10\}\) trading sessions. Each horizon is a separate modelling and evaluation problem.

The target is a gross price return. It excludes dividends, transaction costs, slippage and taxes. Predictive results must not be described as net investment returns.

### 3.2 Classification target

Classification is complementary to regression and must not be implemented until the prepared dataset is verified to contain the relevant classification labels, their maturity status and the required eligibility information.

For each horizon:

\[
Y(t,h)=\mathbb{1}[R(t,h)>0]
\]

The label names are `positive_return_1d`, `positive_return_5d` and `positive_return_10d`. A strictly positive realised return maps to 1; a zero or negative realised return maps to 0; an invalid or unavailable target maps to missing, not to class 0. A label is eligible only after its underlying return target has matured.

### 3.3 Information availability

A prediction for session \(t\) may use only information available by the approved forecast cutoff after the close of \(t\). Predictors must not contain target columns, future-derived information or any feature that would not have been available at that time.

## 4. Chronological Dataset Design

The initial dataset uses the following observed-session boundaries:

| Split | Start | End | Permitted use |
|---|---|---|---|
| Development | 2016-10-24 | 2023-10-20 | Initial fitting, baseline development and permitted development-stage decisions |
| Validation | 2023-10-23 | 2025-10-22 | Chronological walk-forward evaluation and permitted model selection |
| Final Test | 2025-10-23 | 2026-10-23 | Final evaluation only after the model and evaluation specification are frozen |

The boundaries are specific to the current pilot dataset and must be recalculated and documented if the data coverage or asset changes. Dates must be anchored to actual observed market sessions.

The Final Test must not be used for feature selection, preprocessing design, hyperparameter optimisation, model-family selection, classification-threshold selection, model-selection decisions, evaluation-rule tuning or strategy refinement. Only matured outcomes may contribute to completed metrics. Pending targets must be reported separately.

A period used to revise the system in response to its results cannot continue to be represented as an untouched Final Test for that revised system. Such work constitutes a new research iteration and requires a documented evaluation design.

## 5. Walk-Forward Training and Retraining

### 5.1 Retraining schedule

The initial retraining schedule is weekly, after the close of the final observed trading session of each week. If Friday is not a trading session, use the final observed session of that week.

At a scheduled cutoff, the workflow must:

1. verify required data availability and applicable data-quality controls;
2. establish and record the information cutoff;
3. calculate target maturity and training eligibility separately for each horizon;
4. exclude observations whose target was not fully observable by that cutoff;
5. fit any learned preprocessing using eligible training data only;
6. fit the approved candidate model using the eligible training subset;
7. run the required implementation, prediction and integrity checks;
8. record the run, model version, configuration, data provenance and eligible sample count; and
9. obtain the required explicit authorisation before using the model to generate forecasts.

The weekly schedule must not be changed silently. Any change to retraining frequency requires a documented proposal and approval.

The preparation and integrity checks that do not fit learned transformations or model parameters may be performed before Gate C. Fitting learned preprocessing and fitting any model are training activities and must not begin until the explicit Gate C authorisation has been granted. Authorisation to train does not authorise forecasts to be made available.

### 5.2 Expanding training window and eligibility

The initial policy is an expanding training window. At each cutoff, use all observations within the permitted training period that satisfy the relevant horizon-specific eligibility rules.

For a target observation \(t\), horizon \(h\) and cutoff \(C\):

\[
Eligible(t,h,C) =
(t \in P) \land (t \leq C) \land (M(t,h) \leq C)
\]

where \(P\) is the permitted training period and \(M(t,h)\) is the target maturity date. A missing maturity date makes the observation ineligible.

The same eligibility principles apply to historical-mean and historical-median baselines. A historical target statistic must use only target values that have matured by the relevant cutoff.

### 5.3 Overlapping targets

The 5- and 10-session targets overlap across adjacent forecast dates. Maturity-based eligibility prevents use of unknown outcomes but does not make overlapping outcomes statistically independent.

Valid overlapping forecasts must not be discarded solely to create apparent independence. Statistical uncertainty and paired comparisons must account for temporal dependence using the approved procedures in `model_evaluation_protocol.md`. Any supplementary non-overlapping analysis must be documented separately and must not replace the primary analysis without approval.

### 5.4 Retraining failure

A failed retraining attempt must be logged. It must not produce an unauthorised forecast or silently overwrite previously authorised artefacts or immutable forecast records. Preserve the last successfully authorised model and its artefacts, but do not activate it automatically for new forecasts after a retraining failure. Record the failed attempt and the missing forecast; resume forecasting only after a model has passed required checks and has been explicitly authorised.

## 6. Features and Preprocessing

The initial contracted feature set contains seven historical-price features:

- `close_return_1d`
- `close_return_5d`
- `close_return_10d`
- `close_return_20d`
- `close_volatility_5d`
- `close_volatility_10d`
- `close_volatility_20d`

Feature definitions, calculation conventions and availability requirements are specified in `feature_engineering_specification.md` and the integrated feature-target pipeline contract. The implementation must conform to those specifications rather than introduce undocumented variants.

Rows containing missing or non-finite contracted features must not be silently imputed. They must be excluded from model matrices and recorded. Any imputation or additional learned transformation requires separate specification and approval.

Any fitted preprocessing—including scaling, approved imputation, feature selection or dimensionality reduction—must be fitted exclusively on the eligible training subset for the relevant cutoff and horizon. Validation and test rows may be transformed using the fitted training pipeline; their outcomes must not be used to fit preprocessing. Preprocessing must be refitted when required by each scheduled training run.

## 7. Model Development Sequence

### 7.1 Regression baselines and first trainable model

The regression comparison set must include:

1. **Zero Return baseline:** predicts 0 for every observation.
2. **Historical Mean baseline:** predicts the mean of eligible, matured historical target values for the relevant horizon and cutoff.
3. **Historical Median baseline:** predicts the median of eligible, matured historical target values for the relevant horizon and cutoff.
4. **Ridge Regression:** the first supervised trainable model in the initial development sequence.

The practical comparison sequence is Zero Return, Historical Mean, then Ridge Regression; Historical Median remains a required comparison baseline. Ridge regularisation selection must use a documented chronological procedure confined to permitted Development/Validation data. No baseline may use information unavailable at the forecast cutoff.

### 7.2 Classification sequence

Only after dataset readiness is verified, classification comparisons may include:

1. a constant-probability baseline based on the positive-return prevalence among eligible, matured training labels; and
2. regularised Logistic Regression.

The prevalence baseline must be estimated independently at each relevant cutoff and horizon using eligible training labels only. Probability forecasts must be evaluated as probabilities. Any decision threshold other than a predeclared default must be selected without Final Test outcomes.

### 7.3 Model complexity

More complex model families may be considered only after the initial baselines have been implemented and evaluated under the approved protocol. Complexity must be justified by evidence from permitted out-of-sample evaluation, temporal stability or operational requirements. Deep learning is outside the initial baseline stage.

## 8. Operational Minimum Sample Requirements

The following are approved operational minimums. They are guardrails, not guarantees of statistical power or sufficient evidence of generalisability. Requirements apply independently by horizon and to the relevant eligible or paired sample.

| Activity | Minimum requirement |
|---|---:|
| Regression model training | At least 500 eligible training observations |
| Classification model training | At least 500 eligible observations and at least 100 observations in each class |
| Exploratory regression evaluation | At least 100 paired valid forecasts |
| Confirmatory regression evaluation | At least 200 paired valid forecasts |
| Exploratory classification evaluation | At least 100 paired forecasts and at least 20 observations in each actual class |
| Confirmatory classification evaluation | At least 200 paired forecasts and at least 50 observations in each actual class |

If a requirement is not met, training or the intended strength of the evaluation must be blocked or restricted as appropriate. The run must log the unmet requirement and reason. An evaluation below the exploratory minimum must not be presented as reliable evidence of comparative performance. A sample meeting a numerical threshold may still be inadequate because of dependence, missingness, instability, low power or limited regime coverage.

## 9. Evaluation and Statistical Comparison

The detailed metric definitions, edge cases, comparison methods and reporting rules are specified in `model_evaluation_protocol.md` and are normative for evaluation.

At minimum:

- MAE and RMSE are the primary regression metrics.
- Directional Accuracy, Spearman rank correlation and out-of-sample \(R^2\) are complementary diagnostics.
- Classification evaluation prioritises probability quality and includes Brier score, log loss and ROC-AUC where defined, alongside threshold-dependent metrics and class prevalence.
- Each horizon is reported independently.
- Paired comparisons use common valid dates and matured outcomes.
- Missing or invalid forecasts are recorded, never silently treated as zero.
- Statistical uncertainty accounts for temporal dependence.
- The significance level is \(\alpha=0.05\); Holm is the primary multiple-comparison correction for confirmatory families. Benjamini–Hochberg may be used for suitable exploratory families; Bonferroni is a supplementary reference.
- Statistical significance is not equivalent to practical importance, predictive usefulness or profitability.

Any minimum practically meaningful improvement and quantitative model-family selection thresholds remain open and must be specified and approved before confirmatory results are examined. They must not be reverse-engineered from Final Test outcomes.

## 10. Forecast Records, Label Maturity and Missing Predictions

Forecasts must be recorded before their future outcomes are evaluated. A forecast record should include, at minimum:

- asset ticker and forecast timestamp;
- forecast horizon;
- predicted return or predicted probability;
- model identifier and version;
- training cutoff and eligible training count;
- reference entry session and expected target maturity session;
- feature/data version and experiment identifier;
- realised target when it becomes available;
- evaluation status, including pending, valid, invalid or missing; and
- warnings, exclusions or failure reason.

Original forecasts are immutable. A later model version must not overwrite a previously recorded prediction. Pending targets must remain pending; they must not be converted into zero returns, failed predictions or completed evaluation observations.

Comparative metrics must use the same matured dates for all models in a comparison wherever possible. Any exclusions and differences in coverage must be disclosed.

## 11. Reproducibility and Experiment Tracking

Every run must record, at minimum:

- unique experiment/run identifier;
- asset, market-data source and data version or snapshot;
- dataset split boundaries and forecast horizon;
- target and feature specifications;
- preprocessing configuration;
- model family, parameters and selection procedure;
- random seed where applicable;
- cutoff, eligible training count and evaluation dates;
- paired valid sample count, pending targets and excluded/missing forecasts;
- metrics, baselines and statistical procedures;
- code revision and software/library versions; and
- warnings, failures and deviations from the protocol.

Failed runs remain traceable. Results must not be selectively omitted because they are unfavourable. Any deviation must be recorded with its rationale and approval status.

## 12. Predictive Evaluation Versus Economic Evaluation

This protocol governs predictive forecasting. It does not establish that a strategy is profitable.

A separate, explicitly authorised backtesting design must address execution timing, transaction costs, slippage, applicable taxes, dividends and corporate actions, position sizing, exposure constraints, portfolio accounting, turnover, market exposure, drawdown and suitable asset/cash benchmarks. Forecast accuracy alone is not evidence of economic usefulness.

## 13. Approval Gates and Authorisation

The following gates are separate and sequential.

**Gate A — Protocol approval**  
Approve the consolidated methodology, temporal design, targets, baseline sequence and evaluation rules. Approval of individual methodological decisions does not, by itself, establish that this complete consolidated document has passed Gate A. Approval of this document does not waive later gates.

**Gate B — Implementation review**  
Review implementation of baselines, feature/preprocessing controls, forecast recording, prediction contracts, target maturity, temporal eligibility and leakage tests. Verify classification-label readiness before classification implementation. Technical validation establishes implementation and control correctness; it does not establish predictive superiority or economic usefulness.

**Gate C — Model-training authorisation**  
Obtain explicit approval before fitting any learned preprocessing, fitting any model or running model experiments. This consolidated document does not itself grant Gate C approval. Authorisation to train is not authorisation to make forecasts or trading signals available.

**Gate D — Backtesting authorisation**  
Obtain separate explicit approval before running trading backtests.

Paper trading and live trading each require their own explicit authorisation. Successful training or passing engineering checks does not itself authorise forecasting, deployment or trading.

## 14. Model-Family Selection and Trained-Model Authorisation

Model-family selection evaluates the suitability of the modelling approach using permitted Development and Walk-forward Validation evidence. It must consider target and feature integrity, leakage controls, baseline comparisons, primary and complementary metrics, performance across horizons, temporal stability, uncertainty, sample adequacy and reproducibility.

Operational authorisation applies to a specific trained-model version for a specified asset and forecast horizon. Before forecasts or trading signals from that version are made available, the model must have been trained and validated specifically for the selected asset, pass data-integrity, temporal-eligibility, preprocessing, training-completion, prediction-output, artefact and provenance checks, and receive the required explicit operational authorisation. The prediction contract must enforce valid structure and finite outputs.

Technical validation establishes that implementation and controls behave as specified. Predictive validation assesses performance against the approved baselines and evaluation rules. Operational authorisation permits a specific model version to be used for the authorised purpose; it does not automatically authorise future versions or establish economic profitability. These are separate dimensions, and no single metric, training success or engineering check is sufficient to establish overall success.

## 15. Current Implementation Status and Limitations

The project has an executed model-dataset preparation workflow and implementations for feature generation, target generation, target maturity and temporal eligibility. The reported dataset preparation produced horizon-specific eligible/mature counts; those counts do not demonstrate that models have been trained or evaluated.

No claim is made here that baseline models, forecast storage, model training, confirmatory inference, backtesting, paper trading or live trading have been executed. The three recorded OHLC anomalies have not been corrected or deleted, and corporate-action reconciliation remains not assessed; the historical price series must not be described as fully certified.

Before implementation of classification, verify that the prepared outputs contain all three classification labels, maturity information and horizon-specific eligibility. Before confirmatory evaluation, document hypothesis families, practically meaningful improvement criteria, temporal-stability criteria and any required power analysis assumptions.

## 16. Change Control

Any change to targets, features, split boundaries, retraining cadence, minimum samples, metric definitions, statistical parameters, hypothesis families or acceptance rules must be documented, justified and approved before implementation. Changes must not be selected to improve already-observed Final Test results. Preserve prior protocol versions and experiment records so that results remain reproducible.
