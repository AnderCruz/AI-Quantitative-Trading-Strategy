# Model Evaluation Protocol

**Project:** AI Quantitative Trading & Decision Intelligence System  
**Pilot asset:** `LLOY.L` (Lloyds Banking Group, London Stock Exchange, GBP)  
**Status:** Revised consolidated draft — five approved review adjustments incorporated  
**Normative relationship:** Detailed evaluation reference under `model_development_and_evaluation_protocol.md`  
**Scope:** Forecast metrics, baselines, paired comparison, uncertainty, sample adequacy and reporting  
**Not authorised by this document:** Model training, confirmatory evaluation execution, backtesting, paper trading or live trading

## 1. Purpose and Scope

This document specifies how return forecasts and, once dataset readiness has been verified, binary positive-return probabilities are evaluated. It defines metric conventions, baseline comparisons, paired samples, statistical uncertainty, multiple-testing controls and reporting requirements.

The approved horizons are 1, 5 and 10 trading sessions. Each horizon must be evaluated separately. Forecasting performance must be distinguished from economic performance: this protocol does not establish that a trading strategy is profitable.

The primary normative development process and approval gates are defined in `model_development_and_evaluation_protocol.md`. The temporal validation strategy and feature/target contracts remain applicable.

## 2. General Evaluation Rules

1. Respect chronological information availability and target maturity.
2. Evaluate only matured realised outcomes; pending labels remain pending.
3. Record forecasts before the corresponding outcomes are evaluated.
4. Compare models on common valid forecast dates and realised targets wherever possible.
5. Report each horizon independently.
6. Record missing, invalid and excluded forecasts; do not silently convert them to zero or compare materially different samples without disclosure.
7. Account for dependence caused by overlapping multi-session targets.
8. Freeze the evaluation rules before examining the relevant confirmatory results.
9. Keep the Final Test isolated from model, feature, preprocessing, hyperparameter, threshold and strategy selection.
10. Do not interpret statistical significance as proof of practical value or trading profitability.

A return must use a consistent numerical representation. For example, `0.01` represents a 1% return.

## 3. Regression Metrics

### 3.1 Primary metrics

The primary regression metrics are Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE).

For realised returns \(y_i\) and predictions \(\hat y_i\):

\[
MAE=\frac{1}{N}\sum_{i=1}^{N}|y_i-\hat y_i|
\]

\[
RMSE=\sqrt{\frac{1}{N}\sum_{i=1}^{N}(y_i-\hat y_i)^2}
\]

MAE measures average absolute error. RMSE gives greater weight to large errors. Lower values indicate smaller errors on the same evaluation sample. MAE and RMSE must be calculated separately by horizon and on the same paired sample for model comparisons.

### 3.2 Complementary metrics

- **Directional Accuracy (DA):** percentage of forecasts whose predicted-return sign agrees with the realised-return sign.
- **Spearman rank correlation:** rank association between predicted and realised returns.
- **Out-of-sample \(R^2\):** diagnostic comparison with the mean of the evaluated outcomes; a negative value is valid and must not be treated as a software error.
- **Mean forecast error:** optional diagnostic for systematic over- or under-prediction.

No single metric establishes overall model quality. Correlation and directional performance do not replace return-error metrics. Undefined or uninformative metrics—for example, because of insufficient variation—must be reported as undefined with a reason, not replaced by an artificial value.

### 3.3 Directional Accuracy: exact convention

For \(N\) paired valid forecasts:

\[
DA=\frac{1}{N}\sum_{i=1}^{N}
\mathbb{1}\left[\operatorname{sign}(\hat R_i)=\operatorname{sign}(R_i)\right]\times100
\]

The following rules are mandatory:

| Predicted return | Realised return | Correct? |
|---|---|---|
| Positive | Positive | Yes |
| Negative | Negative | Yes |
| Positive | Negative | No |
| Negative | Positive | No |
| Zero | Non-zero | No |
| Non-zero | Zero | No |
| Zero | Zero | Yes |

Do not round predictions or realised returns before calculating signs. Missing or invalid predictions and invalid realised targets are excluded from the DA denominator and must be counted and reported under the missing-prediction policy.

DA is computed separately by horizon and on common dates for each model comparison. For the Zero Return baseline, DA equals the proportion of realised returns that are exactly zero under the numerical target representation; this is not evidence of directional skill. The implementation must use a consistent, explicitly documented exact-zero convention and must not introduce an undocumented tolerance.

## 4. Classification Metrics

Classification evaluation is permitted only after the dataset preparation outputs have been verified to include `positive_return_1d`, `positive_return_5d` and `positive_return_10d`, their maturity status and horizon-specific eligibility.

The label is 1 when the realised return is strictly positive and 0 when it is zero or negative. Invalid or unavailable returns produce missing labels. The model must not learn from labels that were not mature at the applicable training cutoff.

Report, as applicable:

- Brier score;
- log loss;
- ROC-AUC;
- balanced accuracy;
- precision and recall;
- confusion matrix; and
- positive-class prevalence.

Probability-based metrics should be prioritised for probability forecasts. Accuracy alone is insufficient where class frequencies are unequal. Metrics that are undefined because only one actual class is present must be reported as undefined, with the sample limitation disclosed. Report metrics separately for each horizon and state the decision threshold for threshold-dependent metrics. Any threshold selection must use permitted Development/Validation data, never Final Test outcomes.

The classification baseline is a constant probability equal to the positive-class prevalence among eligible, matured training labels at the relevant cutoff and horizon. Logistic Regression is the first supervised classification candidate after the baseline and data-readiness gate.

## 5. Required Baselines

### 5.1 Zero Return

Predicts zero return for every observation. This is the neutral regression benchmark.

### 5.2 Historical Mean

Predicts the mean of eligible, matured historical target values available by the relevant training/forecast cutoff, calculated separately by horizon.

### 5.3 Historical Median

Predicts the median of eligible, matured historical target values available by the relevant cutoff and horizon. It provides a robust complementary location benchmark.

### 5.4 First supervised regression model

Ridge Regression is the first supervised trainable regression model in the approved initial sequence. The practical sequence is Zero Return, Historical Mean, then Ridge Regression; Historical Median remains a required comparison baseline.

All baselines must respect the same cutoff, target maturity and observation rules as the candidate model. Baseline forecasts must be recorded and evaluated using the same target definitions. Their definitions must not be changed retrospectively to favour a candidate.

## 6. Temporal and Comparative Aggregation

### 6.1 Global results

For each horizon, report the complete eligible matured out-of-sample evaluation sample, with its date range, number of valid paired observations, pending target count, missing/invalid forecast count and exclusions.

### 6.2 Temporal results

Examine performance across calendar quarters and years where sample sizes permit. Temporal views are diagnostic for instability, degradation and regime dependence; they must not be presented as reliable estimates when the sample is inadequate. Apply the operational sample rules in Section 9 and disclose smaller windows.

### 6.3 Paired comparisons

For a given comparison, use the same forecast dates and realised outcomes for both models wherever possible. Report the paired sample size. If either model lacks a valid forecast, record the missingness and exclude that date from the paired comparison unless a separately justified method is approved. Do not silently compare model metrics calculated on materially different samples.

For regression, compare paired absolute errors and squared errors as appropriate to MAE and RMSE. For directional comparison, compare paired correctness indicators. Classification comparisons must also use common matured observations and compatible probability/label records.

### 6.4 Overlapping horizons

Adjacent 5- and 10-session targets overlap in the underlying future price periods. Do not treat all forecast observations as independent merely because they have distinct timestamps. Preserve valid overlapping forecasts in the primary evaluation; account for dependence in inference. Any supplementary non-overlapping analysis must be clearly labelled and must not replace the principal evaluation without prior approval.

## 7. Statistical Inference and Multiple Comparisons

### 7.1 Significance level and interpretation

The initial significance level is \(\alpha=0.05\). Reports must distinguish the observed effect, uncertainty interval, statistical evidence and practical relevance. Statistical significance alone does not establish meaningful improvement or profitability.

For every paired comparison, define the difference direction before examining confirmatory results. Unless a comparison-specific definition is predeclared, use Model A minus Model B for reported metric differences. For error metrics, a negative difference then favours Model A; for Directional Accuracy and metrics where higher values are better, a positive difference favours Model A. State the convention beside each reported estimate and interval. Interpret an interval in relation to the statistic it actually estimates: an interval excluding zero may support evidence of a difference under the applicable valid procedure, but does not by itself establish that the difference favours the candidate, is practically meaningful, or implies economic value. Apply the predeclared multiple-testing procedure where relevant. Do not infer equivalence from a non-significant result.

### 7.2 HAC/Newey–West inference

Heteroskedasticity and Autocorrelation Consistent (HAC) inference using Newey–West variance estimation is the principal analytical method for appropriate paired comparisons.

The initial lag rule is:

\[
L_h=h-1
\]

| Horizon | Primary HAC lag |
|---|---:|
| 1 session | 0 |
| 5 sessions | 4 |
| 10 sessions | 9 |

Use the same principal lag within the same horizon and confirmatory test family. Sensitivity analyses use lags 5 and 9 for the 5-session horizon, and 14 and 19 for the 10-session horizon. For the 1-session horizon, higher lags may be examined only with a prior documented justification.

Where suitable, conduct inference on paired loss differences, including absolute-error and squared-error differences. For DA, define each model’s correctness indicator on each common valid date as 1 when the predicted and realised signs match under the exact-zero convention in Section 3.3, and 0 otherwise. The paired DA difference is the mean of the date-level differences between the two models’ correctness indicators, expressed in percentage points when reported as a percentage difference. Use a method suitable for paired binary outcomes and temporal dependence, such as HAC/Newey–West inference on the paired correctness-indicator differences and/or the paired temporal block bootstrap specified below. Report the estimated difference, its direction, uncertainty interval and applicable test results. Do not apply a regression-loss test mechanically to a different outcome.

For regression comparisons, define the loss difference consistently before inference—for example, Model A loss minus Model B loss—so that the sign’s meaning is unambiguous. For MAE, analyse paired absolute-error differences; for MSE/RMSE-related comparisons, analyse paired squared-error differences where appropriate, while clearly identifying whether the inferential target is MSE or RMSE. The lag rule is an initial operational specification, not a guarantee that dependence is fully captured. If evidence or the evaluation design suggests longer dependence, report sensitivity analyses and/or use the block-bootstrap procedure below. If the assumptions required for valid inference are not credible, label the result inconclusive.

### 7.3 Moving Block Bootstrap (MBB)

Moving Block Bootstrap is the principal bootstrap procedure and complements, rather than replaces, HAC/Newey–West analysis.

Primary block length is \(b_h=h\):

| Horizon | Primary block length | Sensitivity block lengths |
|---|---:|---|
| 1 session | 1 session | 2 and 5, only where justified |
| 5 sessions | 5 sessions | 10 and 15 |
| 10 sessions | 10 sessions | 20 and 30 |

Planned resampling counts are:

- 2,000 replications for initial procedural development and tests;
- 5,000 replications for exploratory evaluation; and
- 10,000 replications for confirmatory evaluation.

Use two-sided 95% percentile confidence intervals for the predeclared statistic or paired difference being estimated. Set an explicit random-number-generator seed. The proposed global baseline seed is `20261028`; derive each run’s seed deterministically from that global seed and a stable run identifier. These settings must be recorded and not changed in response to which configuration gives the most favourable result.

The bootstrap estimands must be named explicitly in the report. They may include MAE and RMSE for an individual model, paired differences in MAE, paired differences in mean squared error (MSE), differences in Directional Accuracy, and applicable classification metrics or paired metric differences. For RMSE comparisons, distinguish the reported RMSE difference from inference conducted on paired squared-error differences: an interval or test for a mean squared-error difference is not automatically an interval or test for the RMSE difference. If an interval for a difference in RMSE is reported, calculate that statistic within each paired bootstrap replicate and report it as such. For every interval, state the statistic, the comparison direction and the sign convention.

The resampling unit must preserve the paired temporal observations required by the comparison: realised target, forecasts from each compared model, relevant errors/losses and directional-correctness indicators. Resample temporal blocks while preserving the order within each block. Do not bootstrap each model’s errors independently. Define temporal continuity using the trading-session index, not merely adjacent rows in a filtered table. Do not construct blocks across missing sessions, gaps or excluded segments as though they were consecutive. Where gaps exist, apply a documented segmentation or other predeclared handling rule, and report the resulting eligible segments and exclusions. Do not silently bridge gaps or treat missing observations as adjacent.

Record at least: algorithm and implementation/library versions, seed, block length, replication count, confidence level, horizon, compared models, evaluation date range, valid paired sample count, exclusions/missingness, temporal segments used, data and code versions, Python/library versions, the estimand/statistic and comparison sign convention, outputs and warnings.

### 7.4 Bootstrap adequacy and inconclusive results

- Fewer than 100 valid paired observations: no confirmatory inference; if explored, label the evidence highly limited.
- 100–199 valid paired observations: exploratory inference only.
- At least 200 valid paired observations: eligible for consideration as confirmatory, subject to all other requirements.

A nominal sample threshold does not guarantee an adequate effective number of temporal blocks, statistical power or regime coverage. Results must be treated as inconclusive when block coverage is inadequate, gaps or missingness undermine resampling, only a few regimes are represented, confidence intervals are too wide, results are unstable across justified block lengths, or the conclusion is excessively sensitive to assumptions. Do not choose a block length retrospectively because it produces a favourable p-value or interval. Final Test results must never be used to tune the resampling design.

### 7.5 Multiple testing

Holm is the primary family-wise error control procedure for confirmatory hypothesis families. Benjamini–Hochberg may be used for suitable exploratory families. Bonferroni is a supplementary reference method.

The precise membership of each hypothesis family—including model-to-model and model-to-baseline comparisons across horizons and metrics—must be documented before confirmatory results are examined. Do not choose family boundaries or corrections retrospectively to favour a candidate.

## 8. Sample Adequacy

The following operational minimums apply separately by horizon and by the relevant eligible or paired sample. They are not guarantees of statistical power.

| Activity | Minimum |
|---|---:|
| Regression training | 500 eligible observations |
| Classification training | 500 eligible observations and at least 100 observations in each class |
| Exploratory regression evaluation | 100 paired valid forecasts |
| Confirmatory regression evaluation | 200 paired valid forecasts |
| Exploratory classification evaluation | 100 paired forecasts and at least 20 observations in each actual class |
| Confirmatory classification evaluation | 200 paired forecasts and at least 50 observations in each actual class |

If the applicable threshold is not met, block training or restrict the evaluation claim as appropriate and log the reason. Statistical power and effective independent information must also be considered. A nominally adequate sample may still be insufficient because of temporal dependence, missingness, unstable performance or narrow market-regime coverage.

## 9. Missing Forecasts, Pending Outcomes and Reporting

Pending labels must not be treated as realised outcomes. A forecast enters completed evaluation only when the corresponding target has matured and the outcome is available and valid.

Each horizon’s report must include:

- evaluation start and end dates;
- number of matured target observations;
- number of pending outcomes excluded;
- number of missing and invalid forecasts;
- number of paired valid observations used for each comparison;
- baseline and candidate metrics;
- model, data and code version identifiers;
- applicable confidence intervals, test statistics and adjusted p-values;
- statistical method, lags/block length, replication count and seed where relevant;
- temporal-window results and sample limitations; and
- warnings, exclusions and reasons for inconclusive results.

A metric that cannot be validly calculated must be marked undefined/not available with its reason, not filled with a convenient numeric value. Results from different horizons must not be combined without a predeclared and documented aggregation method.

## 10. Model-Family Selection and Interpretation

Model-family selection must be based on Development and walk-forward Validation evidence, not on Final Test outcomes. Consider engineering correctness, performance relative to the predefined baselines, primary metrics, complementary diagnostics, uncertainty, temporal stability, sample adequacy and reproducibility.

Results must be classified appropriately:

- **Evidence supporting superiority:** robust improvement under the predeclared comparison procedure; supports further consideration but does not authorise deployment or prove profitability.
- **Inconclusive evidence:** neither sufficiently robust superiority nor inferiority is established. This is not proof of equivalence.
- **Evidence of inferiority:** the candidate performs worse under the predeclared criteria and must not be described as superior on those results.

Quantitative minimum practically meaningful improvement and model-family acceptance thresholds remain to be specified and approved before confirmatory evaluation. They must not be set retrospectively after reviewing Final Test outcomes.

Model-family approval is separate from authorisation of an individual trained model version. Engineering checks are not evidence of predictive superiority.

## 11. Final Test Procedure and Isolation

Before Final Test evaluation, freeze and record:

1. feature specification;
2. preprocessing pipeline;
3. model family and configuration;
4. forecast and evaluation metrics;
5. aggregation and missingness rules;
6. statistical tests, lag/block rules, hypothesis families and multiple-testing procedure;
7. training/evaluation boundaries and target-maturity rules; and
8. experiment identifier, data provenance, code version and random seeds.

Final Test outcomes must not be used for feature selection, preprocessing design, hyperparameter optimisation, model-family selection, threshold selection, strategy refinement or evaluation-rule tuning. Only matured outcomes contribute to completed metrics; pending outcomes remain separate.

Any revision prompted by Final Test results is a new research iteration. The same period must not be presented as an untouched test set for a revised model or evaluation design.

## 12. Reproducibility and Implementation Readiness

The evaluation implementation must produce deterministic, auditable records for forecasts, realised outcomes, paired comparison samples, metric calculations, statistical tests and exclusions. Record experiment identifiers, asset/data versions, target horizon, split boundaries, feature/preprocessing configuration, model version, cutoff, eligible and evaluated sample counts, random seed, software environment, code revision, warnings and failures.

Before classification implementation, verify that the dataset preparation outputs include the three classification labels, their maturity state and eligibility. This protocol is a specification; it is not evidence that HAC, bootstrap, classification or confirmatory evaluation code has been implemented or executed.

## 13. Authorisation Boundary

This protocol does not itself authorise model training, confirmatory evaluation execution, backtesting, paper trading or live trading. The project’s separate gates remain in force:

- **Gate A:** protocol approval;
- **Gate B:** implementation review;
- **Gate C:** explicit model-training authorisation;
- **Gate D:** separate explicit backtesting authorisation.

Paper trading and live trading require separate explicit approval. No model should be made operational merely because it has completed training or produced favourable evaluation metrics.

## 14. Open Items Before Confirmatory Evaluation

The following items remain open and must be resolved before confirmatory evaluation is authorised:

1. the precise confirmatory hypothesis-family membership and comparison inventory;
2. the minimum practically meaningful improvement for relevant primary comparisons;
3. quantitative temporal-stability criteria and minimum evidence requirements;
4. the power-analysis approach and assumptions, where used;
5. implementation-level validation of the defined metric and inference procedures; and
6. verification that the prediction-record contract and classification dataset outputs satisfy this protocol.

These open items do not invalidate the approved methodological decisions above; they limit the claims and activities that may proceed until resolved.

## Conclusion

This protocol defines the metric conventions, baselines, paired comparisons, operational sample minimums, HAC/Newey–West lag rules, Moving Block Bootstrap settings, multiple-testing controls and reporting requirements for the project’s forecast evaluation. It preserves the separation between predictive evidence, model-family selection, operational authorisation and economic evaluation. No model training or trading activity is authorised by this document alone.
