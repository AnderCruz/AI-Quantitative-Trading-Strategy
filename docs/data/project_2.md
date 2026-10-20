# AI Quantitative Trading & Decision Intelligence System

## Phase 0 Completion Report: Project Definition and Technical Planning

**Document status:** Phase 0 planning completed
**Project status:** Awaiting explicit authorisation for Phase 1
**Version:** 1.0
**Language:** British English
**Initial simulated capital:** USD 10,000
**Initial market:** US equities listed on Nasdaq or NYSE
**Initial strategy:** Long-only swing trading using daily market data

---

## 1. Executive Summary

Phase 0 establishes the research objectives, initial trading scope, forecasting framework, validation principles, preliminary technical architecture, risk-management requirements, and governance rules for the AI Quantitative Trading & Decision Intelligence System.

The project aims to determine whether a properly validated forecasting system can identify trading opportunities that remain economically attractive after realistic transaction costs and risk constraints.

The system will combine financial market data, statistical analysis, machine learning, probabilistic forecasts, decision rules, portfolio risk management, realistic backtesting, and paper trading.

The project will distinguish three separate questions:

1. **Engineering correctness:** Does the system process data, generate forecasts, simulate trades, and calculate results correctly?
2. **Predictive usefulness:** Does the forecasting system demonstrate meaningful and sufficiently reliable out-of-sample predictive performance?
3. **Economic usefulness:** Do the resulting trading decisions produce attractive risk-adjusted outcomes after transaction costs and under realistic execution assumptions?

Success in one area will not be treated as proof of success in the others.

No assumption is made that a machine-learning model will outperform a benchmark or generate profitable trading signals.

## 2. Project Charter

### 2.1 Primary objective

Develop a reproducible quantitative trading decision-support system for US equities, initially focused on long-only swing trading.

The system will provide forecasts and structured trading recommendations while explicitly accounting for uncertainty, transaction costs, portfolio exposure, and risk constraints.

### 2.2 Research question

> Can a properly validated machine learning forecasting system identify statistically robust trading opportunities that remain economically attractive after realistic transaction costs and risk constraints?

### 2.3 Initial scope

The initial project will focus on:

* US-listed equities on Nasdaq or NYSE.
* Daily market data.
* Long-only swing trading.
* A hypothetical starting portfolio of USD 10,000.
* Forecasting future returns and associated probabilities.
* Explicit uncertainty assessment.
* BUY, HOLD, SELL, and WAIT recommendations.
* Portfolio and position-level risk management.
* Chronological validation and walk-forward evaluation.
* Realistic historical backtesting.
* Paper trading after the required validation gates have been satisfied.

### 2.4 Out of scope

The initial scope excludes:

* Live brokerage orders.
* Unauthorised automated execution.
* Short selling.
* Assumptions that fractional shares are available without verification.
* Claims of guaranteed returns.
* Selection of an asset based solely on recent performance.
* Model selection based exclusively on the highest historical backtest return.

Any future expansion beyond the approved scope will require a documented decision.

## 3. Confirmed Project Decisions

| ID    | Decision                                                                                                                        | Status   |
| ----- | ------------------------------------------------------------------------------------------------------------------------------- | -------- |
| D-001 | Focus on US equities listed on Nasdaq or NYSE.                                                                                  | Approved |
| D-002 | Begin with daily-data swing trading.                                                                                            | Approved |
| D-003 | Use USD 10,000 as hypothetical initial capital.                                                                                 | Approved |
| D-004 | Begin with a long-only strategy.                                                                                                | Approved |
| D-005 | Select the initial stock through documented comparative analysis.                                                               | Approved |
| D-006 | Investigate future returns as the primary forecast target, complemented by directional probabilities and uncertainty estimates. | Approved |
| D-007 | Use chronological out-of-sample evaluation and walk-forward testing.                                                            | Approved |
| D-008 | Separate forecasting, trading decisions, risk management, and simulated execution.                                              | Approved |
| D-009 | Document and model realistic transaction costs and execution assumptions.                                                       | Approved |
| D-010 | Require paper trading before considering further automation; live trading requires separate approval.                           | Approved |
| D-015 | Use only information available at the forecast timestamp and define a realistic execution convention.                           | Approved |
| D-016 | Evaluate probability calibration and proper scoring rules.                                                                      | Approved |
| D-017 | Empirically assess uncertainty estimates before using them in trading decisions.                                                | Approved |
| D-018 | Apply chronological separation and walk-forward evaluation.                                                                     | Approved |
| D-019 | Protect the final test period from repeated optimisation.                                                                       | Approved |
| D-020 | Evaluate forecasting and trading performance separately.                                                                        | Approved |
| D-021 | Introduce MLflow when systematic experimentation begins, if proportionate.                                                      | Approved |
| D-022 | Select a backtesting implementation only after comparing it with explicit requirements.                                         | Approved |
| D-023 | Define the method for selecting and approving numerical risk limits before formal strategy evaluation.                          | Approved |
| D-024 | Evaluate engineering correctness, predictive usefulness, and economic usefulness separately.                                    | Approved |
| D-025 | Establish documented validation and operational criteria before paper trading.                                                  | Approved |

The initial stock, data provider, numerical risk limits, and backtesting implementation have not been selected.

## 4. Asset-Selection Methodology

### 4.1 Initial candidate universe

The initial candidates for comparative assessment are:

* Microsoft (MSFT)
* Apple (AAPL)
* NVIDIA (NVDA)
* Tesla (TSLA)

These are candidates for research, not approved selections. The final universe may be adjusted if the documented eligibility criteria justify doing so.

### 4.2 Provisional scoring framework

The following weights are retained as **provisional, unvalidated planning weights**.

| Criterion                                    | Provisional weight |
| -------------------------------------------- | -----------------: |
| Data quality and historical coverage         |                25% |
| Liquidity and transaction-cost feasibility   |                25% |
| Suitability for the intended trading horizon |                20% |
| Risk characteristics                         |                20% |
| Reproducibility and data-source suitability  |                10% |
| **Total**                                    |           **100%** |

These weights have not been empirically validated. They are not evidence that the criteria have the stated relative importance.

### 4.3 Phase 1 sensitivity analysis

Phase 1 will include a documented sensitivity analysis to investigate whether the preferred candidate changes under reasonable alternative weighting schemes.

The analysis will:

1. Establish consistent scoring definitions before ranking candidates.
2. Assess eligibility separately from weighted ranking.
3. Record the evidence supporting each score.
4. Evaluate alternative weights without choosing them retrospectively to favour a preferred stock.
5. Document ranking stability, limitations, and unresolved uncertainties.
6. Separate suitability for the research project from expected trading profitability.

No candidate will be selected merely because it achieves the highest score under one arbitrary weighting configuration.

**Phase 0 outcome:** The selection method is defined provisionally. Actual stock selection is deferred to Phase 1.

## 5. Forecasting Framework

### 5.1 Forecasting horizons

The initial evaluation will assess all three horizons:

* One trading session.
* Five trading sessions.
* Ten trading sessions.

There is no commitment to retain all three horizons in the final system.

The comparative evaluation will consider predictive performance, calibration, uncertainty, economic usefulness, trading frequency, transaction costs, and robustness.

### 5.2 Primary target: future return

The preliminary target definition is:

$$
R_{t,h}=\frac{P_{t+h}}{P_t}-1
$$

where:

* \(t\) is the forecast reference time.
* \(h\) is the forecast horizon, initially 1, 5, or 10 trading sessions.
* \(P_t\) is the reference price at time \(t\).
* \(P_{t+h}\) is the reference price at the end of the forecast horizon.

This formula is a preliminary definition. Before formal backtesting, the implementation must specify the price convention, corporate-action treatment, dividend treatment, and relationship between forecast reference prices and actual simulated entry and exit prices.

### 5.3 Complementary target: probability of a positive return

The system will investigate:

$$
p_{t,h}=P(R_{t,h}>0\mid X_t)
$$

where \(X_t\) contains information available at the forecast timestamp.

The resulting probability must be evaluated empirically. A predicted probability of 70%, for example, must not be interpreted as a reliable 70% event probability unless calibration evidence supports that interpretation.

### 5.4 Forecast uncertainty

Predictive intervals or conditional quantiles may be considered.

Before uncertainty estimates influence trading decisions, their empirical properties must be assessed, including interval coverage, interval width, stability, and behaviour under changing market conditions where sufficient evidence is available.

Uncertainty estimates will not be treated as guarantees.

### 5.5 Decision outputs

The decision layer will produce one of four recommendations:

| Signal | Intended interpretation                                                                                  |
| ------ | -------------------------------------------------------------------------------------------------------- |
| BUY    | Open or increase a position when the approved decision and risk rules permit.                            |
| HOLD   | Maintain an existing position when the evidence and portfolio constraints support doing so.              |
| SELL   | Reduce or close an existing position.                                                                    |
| WAIT   | Do not open a new position when evidence is insufficient or the opportunity fails the approved criteria. |

The decision engine will consider forecasts, probabilities, uncertainty, estimated transaction costs, current positions, available cash, portfolio exposure, and risk constraints.

Thresholds and decision rules will be established and validated through a documented procedure. They will not be selected simply to maximise historical returns.

## 6. Forecast Timing and Execution Assumptions

The system must not use information that would have been unavailable when a forecast was generated.

The preliminary convention is:

1. Observe market data available at the end of a trading session.
2. Generate the forecast and trading recommendation after that session has closed.
3. Simulate execution at the next eligible opportunity, according to a documented execution rule.
4. Account for transaction costs and applicable execution constraints.
5. Record the forecast timestamp, decision timestamp, order simulation, and execution price separately.

The exact entry and exit conventions remain to be formalised before backtesting.

The system must not assume that a signal generated after a closing price can also be executed at that same closing price unless a realistic, explicitly justified execution mechanism supports that assumption.

## 7. Validation and Experimental Design

### 7.1 Chronological separation

Training, validation, and final testing must respect time order.

The exact boundaries will be established after the available historical data has been verified. They will not be chosen to produce favourable results.

### 7.2 Walk-forward evaluation

The system will use walk-forward evaluation to assess how forecasts and strategies behave across successive historical periods.

The choice between expanding and rolling training windows will be documented and justified. It will not be based solely on which configuration produces the highest returns.

### 7.3 Overlapping targets: purging and embargo

The one-, five-, and ten-session targets will be assessed initially.

Because five- and ten-session target windows can overlap, observations near evaluation boundaries may share future information or outcome periods. This can undermine the independence of training and evaluation observations if not handled appropriately.

The validation design must therefore:

* Identify each observation's target start and end times.
* Prevent training labels from overlapping evaluation periods where this would cause leakage.
* Apply purging where necessary.
* Evaluate an appropriate embargo between relevant training and evaluation observations.
* Document the precise implementation and its rationale.
* Verify that all features are available at the relevant forecast timestamp.
* Consider dependence between overlapping outcomes when interpreting statistical uncertainty.

The length and implementation of any purge or embargo must be justified by the target construction and validation design. They will not be treated as arbitrary fixed settings.

### 7.4 Leakage prevention

The research protocol will explicitly address:

* Look-ahead bias.
* Target leakage.
* Preprocessing leakage.
* Feature leakage.
* Hyperparameter-selection leakage.
* Probability-calibration leakage.
* Corporate-action and price-adjustment errors.
* Unrealistic execution timing.
* Repeated use of the final test period.
* Survivorship and historical-universe limitations.

The final test period must remain protected from repeated model and strategy optimisation.

### 7.5 Separate evaluation layers

**Forecast evaluation** will assess the quality of predicted returns, directional probabilities, and uncertainty estimates.

**Strategy evaluation** will assess the decisions and trades generated from those forecasts under realistic execution assumptions.

A forecast may be statistically informative without generating an economically attractive strategy. Conversely, a profitable historical backtest does not by itself establish that a model has genuine predictive value.

## 8. Evaluation Metrics and Benchmarks

### 8.1 Forecasting metrics

Candidate metrics include:

* Mean Absolute Error (MAE).
* Root Mean Squared Error (RMSE).
* Directional accuracy.
* Brier score.
* Log loss.
* Probability calibration diagnostics.
* Predictive-interval coverage and width, where applicable.

Metric selection must reflect the target and intended use. No single metric will determine model acceptance.

### 8.2 Trading metrics

Candidate strategy metrics include:

* Cumulative return.
* Compound Annual Growth Rate (CAGR), where appropriate.
* Maximum drawdown.
* Sharpe ratio.
* Sortino ratio.
* Win rate.
* Profit factor.
* Turnover.
* Market exposure.
* Number of trades.
* Transaction costs.
* Portfolio equity and cash utilisation.

Results must be interpreted in the context of the evaluation period, trade frequency, risk exposure, and statistical uncertainty.

### 8.3 Benchmarks

The evaluation will consider:

* Buy-and-hold performance for the selected asset.
* A cash benchmark.
* A non-ML strategy baseline, where meaningful and feasible.

The precise benchmark definitions will be documented before formal strategy evaluation.

### 8.4 Acceptance principle

No universal numerical performance threshold is established by this report.

Acceptance criteria must be documented and justified before formal strategy evaluation. They must not be adjusted retrospectively merely to make an unsuccessful strategy appear successful.

## 9. Numerical Risk-Limit Selection and Approval Method

The method for selecting and approving risk limits is now defined at the planning level. **The numerical values remain deliberately unset.**

### 9.1 Required process

Before formal strategy evaluation, the project will follow these steps:

**Step 1 — Define risk dimensions.**

Identify the risks that require explicit controls, including:

* Maximum exposure to an individual position.
* Total portfolio exposure.
* Minimum cash reserve, if required.
* Position-sizing constraints.
* Maximum portfolio drawdown or other loss-related intervention rules.
* Trade-level risk controls, where supported by the intended execution design.
* Restrictions related to liquidity and transaction costs.

This list is a starting framework. The relevance and exact definitions of individual controls must be documented.

**Step 2 — Define the purpose of each limit.**

For each proposed limit, document the risk it is intended to control, the calculation method, the measurement frequency, the action triggered by a breach, and any operational exceptions.

**Step 3 — Analyse the implications.**

Use the USD 10,000 hypothetical portfolio and clearly identified scenarios to investigate the implications of alternative limits.

Historical data may inform this analysis, but historical performance alone must not determine the limits. The analysis should consider capital preservation, portfolio concentration, liquidity, execution feasibility, and the consequences of adverse market movements.

**Step 4 — Establish the selection rationale.**

Document why each proposed value is defensible, what trade-offs it introduces, and what uncertainties remain.

Risk limits must not be selected simply because they improve the historical backtest.

**Step 5 — Approve and freeze the limits.**

Record the final numerical values, definitions, rationale, approval status, and effective version in the project decision log before formal strategy evaluation begins.

**Step 6 — Apply consistently.**

Once approved, apply the limits consistently to the relevant evaluation runs. Any subsequent change must be recorded and justified. Results produced under different risk-limit versions must not be presented as though they came from an identical strategy configuration.

### 9.2 Phase 0 conclusion

The risk-limit selection and approval procedure is established.

The actual numerical limits remain unresolved by design and must be fixed before formal strategy evaluation. No risk limit is represented as approved merely because it appears in this report.

## 10. Portfolio Accounting Requirements

The portfolio simulation must account for:

* Initial capital of USD 10,000.
* Available cash.
* Number of shares held.
* Position market value.
* Portfolio equity.
* Realised and unrealised profit and loss.
* Transaction costs.
* Trade timestamps and simulated execution prices.
* Total and position-level exposure.
* Drawdown and applicable risk-control breaches.

The implementation must document how corporate actions, dividends, cash movements, rounding, and order sizing are treated.

Fractional-share support must be verified rather than assumed.

## 11. Preliminary Technical Architecture

The system will separate the following components:

1. **Data layer:** ingestion, validation, storage, and provenance.
2. **Feature layer:** creation of features using only information available at the relevant timestamp.
3. **Target layer:** construction of return targets and directional labels.
4. **Forecasting layer:** baseline statistical models and candidate machine-learning models.
5. **Validation layer:** chronological splits, walk-forward evaluation, purging, embargo, and experiment controls.
6. **Decision layer:** conversion of forecasts into BUY, HOLD, SELL, or WAIT recommendations.
7. **Risk layer:** position sizing, exposure controls, and portfolio constraints.
8. **Backtesting layer:** simulated orders, execution assumptions, transaction costs, and portfolio accounting.
9. **Evaluation layer:** forecasting metrics, trading metrics, benchmarks, and robustness analysis.
10. **Reporting layer:** reproducible reports, charts, experiment summaries, and documented limitations.

The architecture separates model output from trading decisions so that forecasting logic, decision rules, risk controls, and simulated execution can be evaluated independently.

## 12. Preliminary Technology Choices

| Technology                             | Intended role                                               | Status                   |
| -------------------------------------- | ----------------------------------------------------------- | ------------------------ |
| Python                                 | Primary programming language.                               | Proposed baseline        |
| pandas                                 | Tabular data processing.                                    | Proposed baseline        |
| NumPy                                  | Numerical computation.                                      | Proposed baseline        |
| scikit-learn                           | Baselines, preprocessing, and conventional ML.              | Proposed baseline        |
| Matplotlib                             | Reproducible analytical visualisations.                     | Proposed baseline        |
| pytest                                 | Automated testing.                                          | Proposed baseline        |
| Git and GitHub                         | Version control and project collaboration.                  | Proposed baseline        |
| XGBoost / LightGBM                     | Potential tree-based models.                                | To be evaluated          |
| PyTorch                                | Potential deep-learning implementation.                     | Deferred until justified |
| MLflow                                 | Experiment tracking when systematic experimentation begins. | Approved in principle    |
| Backtesting framework or custom engine | Historical strategy simulation.                             | Selection deferred       |
| Plotly                                 | Optional interactive visualisation.                         | Optional                 |

These are preliminary technical choices, not evidence that the software has been installed, configured, or tested.

The backtesting implementation will be selected only after explicit requirements for order timing, portfolio accounting, costs, risk controls, and reproducibility have been documented.

## 13. Data-Source Evaluation Criteria

The project has not selected a data provider.

The eventual assessment must consider:

* Historical coverage and data availability.
* Daily OHLCV data availability.
* Price-adjustment and corporate-action treatment.
* Timestamp conventions and trading-calendar handling.
* Data quality, missing observations, and revisions.
* Liquidity-related information and limitations.
* Licensing and permitted use.
* Reliability and reproducibility.
* Access costs and operational constraints.
* Suitability for realistic backtesting.

The choice of provider must be based on documented evidence and the project's requirements, not convenience alone.

## 14. Initial Risk Register

| Risk                       | Potential impact                               | Planned mitigation                                                                     |
| -------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------- |
| Look-ahead bias            | Artificially inflated performance.             | Enforce timestamp-aware feature and execution rules.                                   |
| Data leakage               | Invalid validation results.                    | Chronological separation, pipeline controls, purging, and embargo where appropriate.   |
| Survivorship bias          | Misleading historical conclusions.             | Document universe construction and historical-availability limitations.                |
| Corporate-action errors    | Incorrect returns and portfolio accounting.    | Verify adjustment methodology and accounting conventions.                              |
| Unrealistic execution      | Overstated trading performance.                | Explicit execution timing, costs, and constraints.                                     |
| Underestimated costs       | Unprofitable strategies may appear attractive. | Model relevant transaction costs and test assumptions.                                 |
| Overfitting                | Weak out-of-sample performance.                | Walk-forward evaluation and protected final testing.                                   |
| Multiple-testing bias      | False discoveries from repeated experiments.   | Record experiments and interpret results in the context of the search process.         |
| Market-regime changes      | Forecast and strategy degradation.             | Evaluate performance across time periods and market conditions where evidence permits. |
| Probability miscalibration | Misleading confidence in signals.              | Calibration diagnostics and proper scoring rules.                                      |
| Excessive trading          | Costs erode returns.                           | Evaluate turnover and net-of-cost performance.                                         |
| Data-source limitations    | Invalid or irreproducible conclusions.         | Document provenance, limitations, and source-selection rationale.                      |
| Forecast overconfidence    | Inappropriate risk-taking.                     | Evaluate uncertainty and enforce risk controls.                                        |
| Model degradation          | Deteriorating future performance.              | Define monitoring and reassessment requirements before paper trading.                  |
| Premature live automation  | Uncontrolled financial exposure.               | No live trading without separate explicit approval.                                    |

This is an initial register. Risks must be refined as the system and its data sources are specified.

## 15. Proposed Repository Structure

The following structure is a proposal for later implementation. No repository files have been created as part of this report.

```text
AI-Quantitative-Trading-Strategy/
├── README.md
├── pyproject.toml
├── .gitignore
├── configs/
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── notebooks/
├── src/
│   └── quant_trading/
│       ├── data/
│       ├── features/
│       ├── targets/
│       ├── models/
│       ├── validation/
│       ├── forecasting/
│       ├── strategy/
│       ├── risk/
│       ├── backtesting/
│       ├── evaluation/
│       └── reporting/
├── tests/
├── reports/
├── artifacts/
└── docs/
    ├── architecture.md
    ├── decision_log.md
    ├── risk_register.md
    └── research_protocol.md
```

The eventual implementation should include automated tests for data handling, target construction, validation boundaries, execution timing, portfolio accounting, risk controls, and evaluation metrics.

## 16. Governance and Reproducibility

The project will maintain a decision log covering:

* Decision identifier.
* Decision description.
* Status.
* Rationale.
* Evidence considered.
* Known limitations.
* Approval date or project milestone.
* Consequences for subsequent phases.

Experiments must record their data scope, target definition, features, validation design, model configuration, execution assumptions, cost assumptions, risk-limit version, and results.

Where MLflow is used, its tracking and artifact-storage configuration must be documented and verified.

The project must distinguish planned work from completed work, and proposed settings from approved settings. No code execution, data acquisition, experiment, or validation result will be reported as completed without evidence.

## 17. Phase 0 Deliverables and Completion Assessment

| Deliverable                               | Phase 0 status                          |
| ----------------------------------------- | --------------------------------------- |
| Project charter and scope                 | Defined                                 |
| Research question and hypotheses          | Defined                                 |
| Initial market and strategy scope         | Approved                                |
| Initial stock-selection methodology       | Defined provisionally                   |
| Asset-selection weights                   | Retained as provisional and unvalidated |
| Sensitivity-analysis requirement          | Defined for Phase 1                     |
| Forecast targets and horizons             | Defined for initial assessment          |
| Overlapping-target validation requirement | Defined                                 |
| Decision framework                        | Defined conceptually                    |
| Preliminary architecture                  | Defined                                 |
| Preliminary technology assessment         | Documented                              |
| Validation and evaluation principles      | Defined                                 |
| Numerical risk-limit selection method     | Defined                                 |
| Numerical risk-limit values               | Intentionally deferred                  |
| Initial risk register                     | Documented                              |
| Data-provider evaluation criteria         | Defined                                 |
| Proposed repository structure             | Documented                              |
| Decision-log framework                    | Defined                                 |
| Implementation and testing                | Not undertaken in Phase 0               |
| Stock selection                           | Deferred to Phase 1                     |
| Data-provider selection                   | Deferred to Phase 1                     |

Phase 0 is complete at the project-definition and technical-planning level. This does not mean that the system has been implemented, that its assumptions have been empirically validated, or that a trading strategy has been shown to be profitable.

## 18. Outstanding Items for Later Phases

The following remain open and must be addressed at the appropriate stage:

1. Selection of the initial stock using verified comparative evidence.
2. Selection of a suitable data provider.
3. Verification of historical data coverage and quality.
4. Finalisation of price, return, dividend, and corporate-action conventions.
5. Finalisation of chronological validation boundaries.
6. Detailed purging and embargo implementation.
7. Selection of the forecasting models to evaluate.
8. Selection of the backtesting implementation.
9. Definition and approval of numerical risk limits before formal strategy evaluation.
10. Definition of formal acceptance criteria before evaluating strategy performance.
11. Implementation, automated testing, and evidence-based verification.
12. Definition of paper-trading entry criteria and monitoring requirements.

These items do not invalidate Phase 0 completion. They are dependencies for subsequent work.

## 19. Phase 1 Authorisation Gate

**Phase 1 is not authorised.**

No stock has been selected, no data provider has been selected, and no Phase 1 research or implementation is represented as completed.

The next phase, once explicitly authorised, will undertake the documented comparative assessment of candidate assets and data sources, including the required sensitivity analysis of the provisional asset-selection weights.

Work will not proceed to Phase 1 until the user provides explicit authorisation.

## 20. Final Phase 0 Status

**Phase 0: Project Definition and Technical Planning — COMPLETE at the planning level.**

The project now has an approved working baseline, a documented research and validation framework, a provisional asset-selection methodology, an initial technical architecture, a risk-limit approval procedure, and explicit governance requirements.

The next action is to obtain explicit authorisation for Phase 1.

No claim is made that the strategy is profitable, that the proposed asset-selection weights are validated, or that the system has been implemented or tested.
