# Model Evaluation Protocol

## 1. Purpose and Scope

This document defines the evaluation methodology for the AI Quantitative Trading & Decision Intelligence System.

The protocol establishes the primary and complementary forecasting metrics, baseline models, temporal aggregation rules, statistical comparison principles, and model authorisation requirements.

The initial pilot asset is Lloyds Banking Group (`LLOY.L`), listed on the London Stock Exchange and traded in GBP.

The system is intended to forecast returns over 1-, 5- and 10-trading-session horizons. Forecast evaluation must distinguish predictive performance from trading profitability.

This document defines the evaluation methodology. It does not authorise model training, hyperparameter optimisation, backtesting, trading signal generation or paper trading.

## 2. Forecast Evaluation Principles

The following principles govern model evaluation:

1. All evaluation must respect chronological information availability.
2. Training labels must have fully matured by the relevant training cutoff.
3. Forecasts must be recorded before their future outcomes are evaluated.
4. Each forecast horizon must be evaluated independently.
5. Models must be compared against predefined baselines.
6. Comparisons must use common observations wherever possible.
7. Pending targets must not contribute to completed evaluation metrics.
8. Temporal dependence must be considered when estimating statistical uncertainty.
9. Final Test outcomes must not influence model selection, feature selection, hyperparameter optimisation, threshold selection or strategy refinement.
10. Forecasting performance must not be interpreted as evidence of trading profitability.

The evaluation methodology and model-selection rules must be established before the corresponding results are examined.

## 3. Primary and Complementary Metrics

### 3.1. Primary Metrics

The primary metrics are Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE).

For observations with predicted returns `y_hat` and realised returns `y`:

`MAE = mean(abs(y - y_hat))`

`RMSE = sqrt(mean((y - y_hat)^2))`

MAE measures the average absolute forecasting error. RMSE gives greater weight to larger errors.

Both metrics must be calculated separately for each forecast horizon.

The return values must use a consistent numerical representation throughout evaluation. For example, a return of 0.01 represents 1%.

### 3.2. Complementary Metrics

The following metrics provide additional diagnostic information.

**Directional Accuracy**

Measures the proportion of evaluated observations for which the predicted and realised return directions agree.

The treatment of zero predictions and zero realised returns must be defined before implementation.

**Spearman Rank Correlation**

Measures the rank association between predicted and realised returns.

It may be uninformative or undefined when there is insufficient variation or too few valid observations. Such cases must be reported explicitly rather than converted into artificial values.

**Coefficient of Determination (R²)**

Measures predictive performance relative to the mean of the evaluated observations.

R² may be negative for out-of-sample forecasts. A negative value must be reported as a valid diagnostic result rather than treated as a software error.

### 3.3. Metric Interpretation

No individual metric is sufficient to establish overall model quality.

A model may correctly predict the direction of returns while substantially misestimating their magnitude. Conversely, a model may achieve a relatively low return-prediction error without providing a useful directional advantage.

Metric definitions, edge-case handling and aggregation rules must be implemented consistently across models and baselines.

The minimum sample sizes required for reporting each metric remain to be specified.

## 4. Baseline Models

Three initial baselines are proposed.

### 4.1. Zero Return

The predicted return is zero for every forecast.

This baseline establishes whether a forecasting model improves upon a neutral return prediction.

### 4.2. Historical Mean

The predicted return is the mean of eligible historical target values available at the relevant forecast or model-training cutoff.

Only targets whose outcomes have fully matured by that cutoff may contribute to the estimate.

### 4.3. Historical Median

The predicted return is the median of eligible historical target values available at the relevant cutoff.

This provides a complementary reference that is less sensitive than the mean to extreme observations.

### 4.4. Baseline Requirements

All baselines must respect the same information-availability rules as the forecasting models.

In particular:

* Historical statistics must not use future observations.
* Target maturity must be checked independently for each horizon.
* Baseline predictions must be recorded and evaluated using the same outcome definitions as model predictions.
* Comparisons must use common evaluation observations wherever possible.
* The baseline definitions must not be retrospectively changed to favour a particular model.

The detailed implementation of the baselines remains subject to review before modelling is authorised.

## 5. Temporal Aggregation

Evaluation results must be reported at three levels.

### 5.1. Global Evaluation

Global metrics summarise all eligible, matured out-of-sample forecasts for each horizon.

Each horizon must have its own results, observation count and pending-target count.

### 5.2. Temporal Evaluation

Results should also be examined across calendar quarters and years where sufficient observations are available.

Temporal reporting is intended to identify changes in performance, periods of deterioration and instability that may be obscured by aggregate metrics.

The minimum sample size for publishing temporal metrics remains to be specified.

Periods with insufficient observations must be identified explicitly rather than presented as reliable performance estimates.

### 5.3. Comparative Evaluation

Model comparisons must use the same forecast dates and realised outcomes wherever possible.

If a model fails to produce a valid forecast for a particular observation, the missing forecast must be recorded.

Comparative results must disclose the number of observations used and must not silently compare models on materially different samples.

Global metrics, temporal metrics and pairwise comparisons must be reported separately.

## 6. Statistical Model Comparison

### 6.1. Paired Comparisons

Models must be compared using paired observations and consistent loss definitions.

For example, the absolute forecasting error for each model can be calculated on the same realised target observations. Differences between the resulting losses provide a basis for comparing forecasting performance.

Primary comparisons will examine differences in MAE and RMSE.

Complementary comparisons may examine directional accuracy and Spearman rank correlation where their assumptions and sample sizes permit meaningful interpretation.

### 6.2. Temporal Dependence

Forecast errors may be temporally dependent, particularly for the 5- and 10-session horizons.

Statistical procedures must therefore account for dependence where appropriate.

Two candidate approaches are:

* Heteroskedasticity and Autocorrelation Consistent (HAC) variance estimation, including Newey–West methods where suitable.
* Block bootstrap procedures that resample temporal blocks rather than treating individual observations as independent.

The appropriate implementation, dependence assumptions, block-length selection and other statistical parameters must be specified before confirmatory comparisons are conducted.

Neither method should be applied mechanically without checking its suitability for the evaluation design.

### 6.3. Interpretation of Statistical Evidence

Reports must distinguish:

* The observed difference in forecasting performance.
* The estimated uncertainty of that difference.
* The statistical evidence supporting or contradicting superiority.
* The limitations of the sample and method.

Statistical significance alone does not establish practical importance or trading profitability.

The significance level, any minimum practically meaningful improvement and the treatment of multiple comparisons remain to be specified.

### 6.4. Multiple Comparisons

Comparing several models across multiple horizons and metrics creates a risk of selecting an apparently superior model by chance.

The evaluation protocol must define how multiple comparisons will be handled before the relevant results are examined.

The procedure must not be changed retrospectively to favour a selected candidate.

## 7. Overlapping Forecast Horizons

Forecasts are generated after each observed trading session, while some target horizons span multiple sessions.

Consequently, consecutive 5- and 10-session targets overlap in their underlying future price periods.

These observations must not automatically be treated as statistically independent.

The following rules apply:

1. Preserve all valid forecasts in the forecast record.
2. Evaluate the 1-, 5- and 10-session horizons independently.
3. Identify the overlapping nature of the longer-horizon outcomes in evaluation reports.
4. Do not interpret the number of forecasts as the number of independent observations.
5. Account for temporal dependence in statistical uncertainty estimates and model comparisons where appropriate.
6. Do not remove valid overlapping forecasts solely to create an appearance of independence.

Any supplementary non-overlapping analysis must be documented separately and must not replace the principal evaluation without prior approval.

## 8. Model-Family Approval

Approval of a model family concerns the suitability of its modelling and evaluation methodology.

It is distinct from the operational authorisation of an individual trained model version.

A model family must not be selected solely because it achieves the best result on one metric or during one period.

The model-family evaluation must address:

* Compliance with the approved target definitions.
* Feature availability and data-leakage controls.
* Correct temporal eligibility and preprocessing.
* Comparison against the predefined baselines.
* Primary and complementary forecasting metrics.
* Performance across the approved forecast horizons.
* Temporal stability and uncertainty.
* The limitations and reproducibility of the results.

Model selection must use Development and Walk-forward Validation according to the approved temporal protocol.

The Final Test must remain isolated from model-family selection and related design decisions.

Quantitative selection thresholds and the precise model-family approval procedure remain to be specified and approved before modelling begins.

## 9. Trained-Model Operational Authorisation

Operational authorisation applies to an individual trained model version.

Successful completion of training does not, by itself, authorise a model for forecasting.

Before authorisation, the candidate must pass all required controls.

### 9.1. Data Integrity

The required data must be available and must pass the applicable quality checks.

Unresolved data-quality failures must be handled according to a documented policy.

### 9.2. Temporal Eligibility

Training observations must satisfy the approved chronological boundaries and target-maturity rules.

No target whose outcome was unknown at the training cutoff may be used as a training label.

Eligibility must be calculated separately for each forecast horizon.

### 9.3. Feature and Preprocessing Integrity

Features must respect the approved information-availability rules.

Fitted preprocessing transformations must use eligible training data only.

Target columns and future-derived information must not be used as predictors.

### 9.4. Training and Prediction Integrity

The training process must complete successfully.

The candidate must produce outputs that satisfy the defined prediction contract, including finite numerical values and valid output structure.

The complete prediction contract and any additional domain-specific checks remain to be specified.

### 9.5. Artefact and Provenance Integrity

The model artefacts and associated configuration must be saved and verified.

The system must record the model identifier, version, training cutoff, relevant data provenance and applicable configuration.

### 9.6. Authorisation Decision

A candidate that fails any mandatory operational control must not be authorised.

The authorisation decision must be explicit and traceable.

The previously approved retraining-failure policy remains in force: preserve the last successfully authorised model and its artefacts, do not activate it automatically for new forecasts after a retraining failure, record the failed attempt and missing forecast, and resume forecasting only after a model has passed the required checks and has been authorised.

Operational checks must not be represented as proof of predictive superiority.

## 10. Underperformance and Inconclusive Results

Evaluation results must distinguish three broad outcomes.

### 10.1. Evidence of Superiority

The model demonstrates sufficiently robust improvement against the predefined baseline or baselines under the approved comparison procedure.

Such evidence supports consideration of the model but does not, by itself, authorise deployment or establish trading profitability.

### 10.2. Inconclusive Evidence

The observed results do not establish sufficiently robust superiority or inferiority.

The report must document the uncertainty and limitations. An inconclusive result must not be described as proof that the model is equivalent to the baseline.

### 10.3. Evidence of Inferiority

The model performs worse than the relevant baseline under the predefined evaluation criteria.

It must not be selected as superior on the basis of those results.

The applicable decision rules, quantitative thresholds and handling of conflicting metrics remain to be specified before model evaluation begins.

Baselines, metrics and decision rules must not be changed retrospectively to favour a candidate.

## 11. Final Test Isolation

The Final Test period is reserved for final evaluation under the approved protocol.

Final Test outcomes must not be used for:

* Feature selection.
* Preprocessing design based on observed outcomes.
* Hyperparameter optimisation.
* Model-family selection.
* Threshold selection.
* Strategy selection or iterative refinement.
* Selection of evaluation rules intended to improve reported results.

Predictions must be recorded according to the approved forecasting procedure.

Targets that have not matured must remain pending. Only matured outcomes may contribute to completed evaluation metrics.

Any proposal to use Final Test results to revise the system requires a separately documented evaluation design and explicit approval.

## 12. Outstanding Decisions and Approval Gate

### 12.1 Approved Methodological Decisions

The following methodological decisions have been approved:

1. Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE) are the primary forecast evaluation metrics.
2. Directional Accuracy, Spearman rank correlation and R-squared are complementary metrics.
3. Zero Return, Historical Mean and Historical Median are the approved baseline forecasting methods.
4. Forecast horizons of 1, 5 and 10 trading sessions must be evaluated independently.
5. Comparisons between models must use common evaluation observations wherever a fair comparison is possible.
6. The initial statistical significance level is 5% (\(\alpha = 0.05\)).
7. HAC/Newey–West inference and block bootstrap procedures will be considered complementary approaches to temporal dependence and statistical uncertainty.
8. The Holm procedure is the primary method for controlling multiple comparisons in confirmatory analyses.
9. The Benjamini–Hochberg procedure may be used for appropriate exploratory analyses involving multiple hypotheses. Bonferroni remains a supplementary reference method.
10. Sample adequacy will be assessed through a combination of a minimum operational sample requirement and statistical power considerations.
11. Temporal stability will be assessed through a combination of aggregate performance, performance across temporal windows, baseline comparisons, statistical uncertainty and evidence of performance degradation.
12. Model-family approval and the operational authorisation of individual trained-model versions remain separate decisions.
13. Final Test observations must remain isolated from feature selection, model selection, hyperparameter optimisation, threshold selection and strategy refinement.

### 12.2 Outstanding Quantitative and Statistical Parameters

The following parameters remain to be specified and documented before confirmatory model evaluation:

1. Minimum operational sample sizes for global and temporal metrics.
2. The treatment of zero predictions and zero realised returns in Directional Accuracy.
3. The minimum practically meaningful improvement over baselines, where applicable.
4. HAC estimation choices, including lag selection and the assumptions required for valid inference.
5. Block bootstrap design, including block-length selection and the number of resamples.
6. The precise definition of confirmatory and exploratory hypothesis families.
7. The allocation of comparisons to multiple-testing families, including model-to-model and model-to-baseline comparisons across the three forecast horizons.
8. Quantitative temporal-stability criteria and the minimum evidence required to support a stability assessment.
9. Model-family selection criteria and approval thresholds.
10. Exact implementation and reporting requirements for each evaluation metric.
11. The treatment and reporting of missing forecasts in comparative evaluation.
12. The statistical power analysis methodology and the assumptions used to assess sample adequacy.

These parameters must be defined without using Final Test results to select or tune the evaluation procedure.

### 12.3 Operational and Implementation Requirements

The following requirements must also be specified before the relevant evaluation activities are authorised:

1. The detailed prediction contract and additional operational checks.
2. The rules for recording predictions, model versions, forecast cut-offs and training eligibility.
3. The handling of forecasts whose target outcomes have not yet matured.
4. The procedures for ensuring that compared models are evaluated on common observations.
5. The reporting of inconclusive results and insufficient sample sizes.
6. The documentation required to authorise a trained-model version for operational use.

Any operational authorisation must remain distinct from methodological approval of a model family.

### 12.4 Approval Gate

Approval of this protocol establishes the methodological framework but does not, by itself, authorise model training, confirmatory model evaluation, backtesting or paper trading.

Before confirmatory evaluation begins, the outstanding statistical parameters, hypothesis families, sample adequacy requirements and quantitative decision criteria must be documented and reviewed.

The approved temporal validation design must be preserved. The Final Test must not be used to select models, tune parameters, establish thresholds or revise the evaluation criteria.

Any proposed change to these requirements must be documented, justified and explicitly approved before implementation.

## Conclusion

This protocol establishes the approved methodological framework for evaluating return forecasts, comparing models with predefined baselines, accounting for temporal dependence, controlling multiple comparisons and assessing sample adequacy and temporal stability.

The methodological approaches have been approved, but several quantitative parameters and operational requirements remain open.

The next step is to finalise the outstanding statistical and operational specifications, followed by the feature-availability and preprocessing specifications.

No model training, hyperparameter optimisation, backtesting or paper trading is authorised by this document alone.