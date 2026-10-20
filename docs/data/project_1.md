# AI Quantitative Trading & Decision Intelligence System

## Phase 0 — Project Definition and Technical Planning

**Document status:** Consolidated planning specification
**Proposed repository:** `AI-Quantitative-Trading-Strategy`
**Version:** 1.0 — Draft for Final Review
**Primary market:** US equities listed on Nasdaq or NYSE
**Initial strategy:** Long-only swing trading using daily market data
**Initial simulated capital:** USD 10,000.00

---

## 1. Project Charter

### 1.1 Objective

Develop a professional, reproducible quantitative trading decision-support system that combines financial market data, statistical analysis, machine learning, probabilistic forecasting, trading decisions, portfolio risk management, historical backtesting and paper trading.

The system must evaluate whether forecasting models provide useful information for trading decisions after realistic transaction costs and risk constraints.

The project must not assume that machine learning can reliably predict stock prices or guarantee profitable trading.

### 1.2 Research question

Can a properly validated machine learning forecasting system identify statistically robust trading opportunities that remain economically attractive after realistic transaction costs and risk constraints?

### 1.3 Scope

The initial system will investigate:

* Historical market-data acquisition and quality assurance.
* Exploratory data analysis.
* Financial feature engineering.
* Future-return forecasting.
* Directional probability estimation.
* Forecast uncertainty.
* BUY, HOLD, SELL and WAIT decisions.
* Position sizing and risk management.
* Historical portfolio simulation.
* Walk-forward validation.
* Benchmark comparisons.
* Experiment tracking and reproducibility.
* Paper trading and operational monitoring.

### 1.4 Exclusions

The initial project will not:

* Place real brokerage orders.
* Use real investment capital.
* Assume fractional-share availability.
* Assume that any particular stock is profitable.
* Introduce complex models without justification.
* Optimise the final test period repeatedly.
* Treat positive historical returns as proof of future profitability.

Any future live-trading integration will require a separate decision and explicit approval.

---

## 2. Confirmed Project Decisions

| ID    | Decision                                                                                                                          | Status   |
| ----- | --------------------------------------------------------------------------------------------------------------------------------- | -------- |
| D-001 | Research US equities listed on Nasdaq or NYSE                                                                                     | Approved |
| D-002 | Begin with daily-data swing trading                                                                                               | Approved |
| D-003 | Use USD 10,000 as hypothetical initial capital                                                                                    | Approved |
| D-004 | Begin with a long-only strategy                                                                                                   | Approved |
| D-005 | Select the initial stock through documented comparative analysis                                                                  | Approved |
| D-006 | Investigate future returns as the primary forecasting target, complemented by directional probabilities and uncertainty estimates | Approved |
| D-007 | Use chronological out-of-sample evaluation and walk-forward testing                                                               | Approved |
| D-008 | Separate forecasting, trading decisions, risk management and simulated execution                                                  | Approved |
| D-009 | Use explicit execution assumptions and account for realistic trading costs                                                        | Approved |
| D-010 | Require paper trading before considering further automation                                                                       | Approved |
| D-015 | Respect information availability and realistic execution timing                                                                   | Approved |
| D-016 | Evaluate directional probabilities using calibration and proper scoring rules                                                     | Approved |
| D-017 | Evaluate uncertainty estimates before using them in trading decisions                                                             | Approved |
| D-021 | Introduce MLflow when systematic experimentation justifies it                                                                     | Approved |
| D-022 | Select the backtesting implementation through documented technical comparison                                                     | Approved |
| D-023 | Establish explicit risk controls and approve numerical limits before formal strategy evaluation                                   | Approved |
| D-024 | Evaluate engineering correctness, predictive usefulness and economic usefulness separately                                        | Approved |
| D-025 | Require documented validation and operational criteria before paper trading                                                       | Approved |

Approval of these decisions establishes the methodological direction. It does not mean that the associated components have been implemented or empirically validated.

---

## 3. Research Questions and Hypotheses

The project will investigate the following hypotheses.

**H-01 — Predictive information**

Historical market features may contain information about future returns beyond simple forecasting baselines.

**H-02 — Incremental machine-learning value**

Some machine-learning models may improve forecasting performance relative to simpler models.

**H-03 — Probability reliability**

Probabilistic forecasts may provide useful, sufficiently calibrated estimates of future return direction.

**H-04 — Economic usefulness**

Forecast-informed trading decisions may improve portfolio outcomes relative to predefined reference strategies.

**H-05 — Transaction-cost resilience**

Any apparent trading advantage may or may not survive realistic transaction costs and execution assumptions.

**H-06 — Temporal robustness**

Any genuine predictive or economic advantage should be investigated across multiple chronological evaluation periods.

**H-07 — Risk-management effectiveness**

Explicit portfolio constraints may improve risk characteristics, although they may also reduce returns.

**H-08 — Operational readiness**

A validated strategy may become suitable for paper trading if its data, forecasts, decisions, accounting and monitoring are reproducible and reliable.

These are hypotheses to be tested, not conclusions about market behaviour.

Negative or inconclusive results will be documented.

---

## 4. Initial Asset-Selection Methodology

### 4.1 Candidate universe

The initial candidates are:

* MSFT — Microsoft.
* AAPL — Apple.
* NVDA — NVIDIA.
* TSLA — Tesla.

Additional candidates may be considered if justified by the predefined selection methodology.

No candidate has been selected.

### 4.2 Comparative criteria

The candidates will be assessed using:

| Criterion                                    | Proposed weight |
| -------------------------------------------- | --------------: |
| Data quality and historical coverage         |             25% |
| Liquidity and transaction-cost feasibility   |             25% |
| Suitability for the proposed trading horizon |             20% |
| Risk characteristics                         |             20% |
| Reproducibility and data-source suitability  |             10% |
| **Total**                                    |        **100%** |

These weights are approved as a preliminary proposal only if explicitly confirmed by the user; they have not yet been empirically evaluated.

Eligibility requirements will prevent an unsuitable candidate from qualifying solely through a high aggregate score.

The final comparison will document the available evidence, missing information, limitations and reasons for selecting the initial asset.

The scoring methodology measures suitability for research, not expected profitability.

### 4.3 Selection principle

The asset must be selected because it supports a defensible research process, not because it is assumed to offer the highest returns.

The actual selection belongs to Phase 1.

---

## 5. Forecasting Specification

### 5.1 Candidate horizons

The initial candidate horizons are:

* One trading session.
* Five trading sessions.
* Ten trading sessions.

Their suitability will be evaluated before deciding which horizons to retain.

### 5.2 Primary target

The preliminary primary target is future return:

$$
R_{t,h}=\frac{P_{t+h}}{P_t}-1
$$

where \(P_t\) is the reference price at time \(t\), and \(h\) is the forecast horizon.

The final specification must distinguish between the price used to define the forecasting target and the prices used to simulate actual trading.

### 5.3 Complementary outputs

The forecasting system will investigate:

1. Expected future return.
2. Probability of a positive future return.
3. Predictive uncertainty, potentially through predictive intervals or return quantiles.

Probability estimates will be evaluated using appropriate calibration analysis, Brier score and log loss.

Uncertainty estimates will be assessed empirically before being used to influence trading decisions.

### 5.4 Execution convention

Forecasts must use only information available at the forecast timestamp.

The initial proposed convention is to generate forecasts after the relevant session has closed and simulate execution at the next eligible trading opportunity.

The precise execution assumptions, reference prices, dividend treatment and transaction-cost model must be documented before formal backtesting.

---

## 6. Trading-Decision Framework

The system will generate four possible decisions.

| Decision | Definition                                                                           |
| -------- | ------------------------------------------------------------------------------------ |
| BUY      | Open or increase a permitted long position                                           |
| HOLD     | Maintain an existing position when continuation criteria remain satisfied            |
| SELL     | Reduce or close an existing long position                                            |
| WAIT     | Do not open a new position because the opportunity fails the strategy's requirements |

The decision engine will consider:

* Expected return.
* Directional probability.
* Forecast uncertainty.
* Estimated transaction costs.
* Existing positions.
* Available cash.
* Portfolio exposure.
* Position-sizing rules.
* Risk constraints.

Forecasts will not automatically become trading signals.

The system must be able to abstain from trading when evidence is insufficient or the estimated risk is unacceptable.

---

## 7. Preliminary Technical Architecture

The proposed architecture separates the following components:

* Data acquisition and quality assurance.
* Feature generation.
* Target construction.
* Model training and inference.
* Chronological validation.
* Forecasting and uncertainty estimation.
* Trading decisions.
* Risk management.
* Backtesting and portfolio accounting.
* Performance evaluation.
* Reporting and monitoring.

This separation is intended to make the system testable, interpretable and reproducible.

### Preliminary technology stack

| Technology                            | Proposed role                                   |
| ------------------------------------- | ----------------------------------------------- |
| Python                                | Main programming language                       |
| Pandas and NumPy                      | Data processing and numerical computation       |
| Scikit-learn                          | Baseline models and evaluation                  |
| Matplotlib                            | Statistical visualisation                       |
| Pytest                                | Automated testing                               |
| Git and GitHub                        | Version control and repository management       |
| XGBoost or LightGBM                   | Candidate advanced tabular models               |
| PyTorch                               | Deep learning, if justified                     |
| MLflow                                | Experiment tracking when justified              |
| Existing or custom backtesting engine | Portfolio simulation, selected after comparison |

The final technology choices must be based on demonstrated requirements.

### Backtesting implementation

The choice between an existing framework and a custom implementation remains open.

The evaluation will consider execution timing, transaction costs, cash accounting, corporate actions, portfolio valuation, testing support and reproducibility.

---

## 8. Validation Protocol

### 8.1 Chronological evaluation

The research will distinguish between training, validation and final-test observations.

Training data will be used for fitting models and learned preprocessing.

Validation data will support permitted model selection and hyperparameter decisions.

The final test period will be reserved for the final evaluation and will not be repeatedly reused for optimisation.

### 8.2 Walk-forward evaluation

The project will use walk-forward evaluation to assess temporal robustness.

Expanding and rolling training windows may be compared where justified.

The final design must consider:

* Historical data coverage.
* Forecast horizons.
* Overlapping targets.
* Appropriate purging or embargo procedures.
* Dependence between observations.
* The number of independent evaluation periods.

### 8.3 Leakage prevention

The validation protocol will address:

* Future information entering features.
* Preprocessing fitted outside the permitted training data.
* Incorrect target construction.
* Hyperparameter-selection leakage.
* Probability-calibration leakage.
* Unrealistic execution timing.
* Corporate-action errors.
* Repeated experimentation against the final test period.
* Dependence caused by overlapping forecast horizons.

Automated tests will cover the identified risks wherever practical.

---

## 9. Evaluation Framework

### 9.1 Forecasting metrics

Candidate metrics include:

* Mean Absolute Error.
* Root Mean Squared Error.
* Directional accuracy.
* Brier score.
* Log loss.
* Probability calibration.
* Predictive-interval coverage and width, where applicable.

The selected metrics must match the forecasting task.

### 9.2 Trading metrics

Candidate metrics include:

* Cumulative return.
* CAGR, where appropriate.
* Maximum drawdown.
* Sharpe ratio.
* Sortino ratio.
* Win rate.
* Profit factor.
* Turnover.
* Market exposure.
* Number of trades.

The strategy will be compared against appropriate benchmarks, including buy-and-hold of the selected asset and a cash benchmark.

### 9.3 Acceptance principles

The project will distinguish three forms of success.

**Engineering correctness:** The pipeline, accounting, execution assumptions and risk controls behave as specified.

**Predictive usefulness:** Forecasts demonstrate credible out-of-sample performance relative to appropriate baselines.

**Economic usefulness:** Trading decisions demonstrate sufficiently robust performance after realistic costs and risk constraints.

No single forecasting or trading metric will determine success.

Numerical acceptance thresholds must be justified and approved before formal strategy evaluation.

---

## 10. Risk Register

The initial risk register covers:

| ID    | Risk                             | Principal mitigation                                      |
| ----- | -------------------------------- | --------------------------------------------------------- |
| R-001 | Lookahead bias                   | Explicit information and execution timestamps             |
| R-002 | Data leakage                     | Chronological separation and automated checks             |
| R-003 | Survivorship bias                | Document the research universe and historical limitations |
| R-004 | Corporate-action errors          | Consistent price-adjustment and accounting conventions    |
| R-005 | Unrealistic execution            | Explicit execution assumptions                            |
| R-006 | Underestimated transaction costs | Cost sensitivity analysis                                 |
| R-007 | Model overfitting                | Baselines and walk-forward evaluation                     |
| R-008 | Multiple-testing bias            | Experiment records and restricted final-test reuse        |
| R-009 | Market regime changes            | Evaluation across time                                    |
| R-010 | Probability miscalibration       | Calibration analysis                                      |
| R-011 | Excessive trading                | Turnover and cost monitoring                              |
| R-012 | Data-source limitations          | Document coverage, terms and quality                      |
| R-013 | Model degradation                | Monitor forecasts and realised outcomes                   |
| R-014 | Forecast overconfidence          | Uncertainty-aware decisions and risk limits               |
| R-015 | Premature live automation        | Separate approval gate for live integration               |

Each risk will ultimately include its potential impact, mitigation, verification method and residual uncertainty.

---

## 11. Portfolio and Risk-Management Requirements

The initial simulation will begin with USD 10,000.

The portfolio simulator must track:

* Available cash.
* Shares held.
* Position market value.
* Portfolio equity.
* Realised and unrealised profit or loss.
* Transaction costs.
* Trade timestamps and execution prices.
* Portfolio exposure.
* Drawdown.

The system must enforce approved position-sizing and exposure limits.

Fractional shares will not be assumed available without verification.

Numerical risk limits remain to be specified and approved before formal strategy evaluation. They must not be selected merely to maximise historical performance.

---

## 12. Data-Source Evaluation Criteria

Phase 1 will assess candidate data providers using:

* Historical coverage.
* Availability of OHLCV data.
* Corporate-action treatment.
* Timestamp semantics.
* Data quality and revisions.
* Reliability and access limits.
* Cost and licensing restrictions.
* Reproducibility.
* Limitations affecting execution modelling.

The provider must be evaluated against the actual research requirements.

No provider has yet been selected, and no historical data availability has been verified.

---

## 13. Technology and Governance Decisions

MLflow will be considered when systematic experimentation begins.

The backtesting implementation will be selected through a documented comparison.

Risk controls will be specified before strategy implementation, and numerical limits will be approved before formal evaluation.

Engineering correctness, predictive usefulness and economic usefulness will be evaluated separately.

Paper trading will require documented technical, validation and operational readiness.

These requirements are approved project principles; their implementation and empirical verification remain future work.

---

## 14. Phase 0 Deliverables

The final Phase 0 package will contain:

1. Project Charter.
2. Research Protocol and Hypotheses.
3. Asset-Selection Methodology.
4. Forecasting Specification.
5. Validation and Evaluation Protocol.
6. System Architecture.
7. Technology Assessment.
8. Risk Register.
9. Decision Log.
10. Phase 0 Completion Report.

The proposed repository documentation will be written in professional British English.

The corresponding files have not yet been created in the repository.

---

## 15. Phase 0 Completion Criteria

Phase 0 will be ready for final approval when:

* The project scope and research question are documented.
* Approved decisions are recorded.
* The stock-selection methodology is defined.
* Forecasting targets and execution timing are specified.
* The validation methodology and leakage controls are documented.
* Evaluation metrics and acceptance principles are established.
* The technical architecture and technology alternatives are documented.
* The risk register is complete.
* Outstanding decisions and limitations are explicit.
* The Phase 0 completion report is prepared.

Completing these requirements will not automatically authorise Phase 1. Explicit user approval will remain mandatory.

---

## 16. Current Status and Next Authorised Action

**Current phase:** Phase 0 — Project Definition and Technical Planning.

**Completed in principle:** Project scope, foundational decisions, preliminary forecasting design, validation principles, technology assessment and initial risk framework.

**Still outstanding:** Final review of the consolidated specifications, completion of the decision log and risk register, and resolution of any material planning questions.

**Not started:** Stock selection, data acquisition, repository implementation, model training, trading signals, backtesting and paper trading.

**Next authorised action:** Finalise and review the Phase 0 specifications.

**Phase 1 remains unauthorised until the user explicitly approves completion of Phase 0.**
