# AI Quantitative Trading & Decision Intelligence System

## Phase 1 --- Asset and Data-Source Selection

**Document version:** 1.0\
**Project stage:** Phase 1 --- approved initial configuration\
**Status:** Approved decisions recorded; implementation and evaluation
remain subject to the project approval gates\
**Initial asset:** Lloyds Banking Group (`LLOY.L`)\
**Initial data source:** Yahoo Finance, accessed through `yfinance`\
**Initial simulated capital:** GBP 1,000\
**Initial strategy:** Daily-data swing trading\
**Document language:** British English

------------------------------------------------------------------------

## 1. Purpose and Scope

This document records the approved initial asset, market scope,
historical market-data source and operating assumptions for the AI
Quantitative Trading & Decision Intelligence System. It replaces the
earlier preliminary asset/provider comparison and must be read alongside
the project's target-definition, price-series and model-evaluation
documents.

The initial implementation is a research and decision-support system.
Its purpose is to investigate whether historical market information can
support useful, calibrated forecasts and disciplined trading decisions.
It is not a promise of returns, an automated investment service or
evidence that any forecast will be profitable after costs.

The first implementation will use one asset to make the data pipeline,
target construction, validation rules and audit trail easier to inspect.
The architecture should nevertheless avoid hard-coding the pilot asset
into reusable components: supported assets must be configurable, and an
asset must pass data-quality and history checks before it can be used.

This document records decisions rather than reporting model results. No
forecasting model, trading strategy or portfolio allocation is approved
merely because the asset and data source have been selected.

### 1.1 Objectives

The initial asset and data configuration must support:

-   reproducible retrieval of daily historical market data;
-   a documented history of data coverage and quality checks;
-   consistent handling of dates, trading sessions and ticker
    identifiers;
-   target generation without look-ahead leakage;
-   chronological development, walk-forward validation and isolated
    final testing;
-   evaluation against simple forecasting baselines;
-   realistic future assessment of transaction costs and trading
    constraints; and
-   clear records of data limitations, failed checks and decisions
    requiring approval.

### 1.2 Out of scope

This document does not authorise live trading, broker integration,
real-money deployment, leverage, short selling, automated order
execution or claims of expected profitability. It also does not
authorise changing the approved target formula, removing historical
observations solely because they appear unusual, or selecting models and
thresholds using final-test results.

------------------------------------------------------------------------

## 2. Approved Initial Asset

### 2.1 Pilot instrument

The approved pilot instrument is **Lloyds Banking Group ordinary
shares**, using the Yahoo Finance symbol **`LLOY.L`**, listed on the
**London Stock Exchange (LSE)** and quoted in **pounds sterling (GBP)**.

The choice is the project's initial implementation decision, not a claim
that the instrument is optimal, low-risk or profitable to trade. The
pilot provides a concrete instrument for validating the data and
modelling workflow before the system is generalised to other eligible
equities.

### 2.2 Reusable asset support

The system is intended to support eligible equities listed on:

-   the London Stock Exchange (LSE);
-   the New York Stock Exchange (NYSE); and
-   Nasdaq.

The pilot must not cause the implementation to assume that every
instrument is denominated in GBP, uses the same exchange calendar or has
the same trading hours. Currency, exchange, ticker, session calendar and
applicable market conventions must be associated with each asset.

Before a new instrument is admitted, the system must verify that its
identifier resolves to the intended instrument, the returned history is
adequate for the planned analysis, required price fields are available,
timestamps can be interpreted consistently, and the observations pass
documented integrity checks. Unsupported or ambiguous instruments must
fail validation rather than silently proceed.

### 2.3 Asset identity and configuration

The ticker is a data-provider identifier, not a globally unique security
identifier. The asset configuration should therefore record, where
available:

  Field                 Initial configuration
  --------------------- --------------------------------------------
  Instrument            Lloyds Banking Group ordinary shares
  Provider symbol       `LLOY.L`
  Exchange              London Stock Exchange
  Trading currency      GBP
  Bar frequency         Daily
  Pilot status          Approved for research pipeline development
  Trading eligibility   Subject to data and operational checks
  Live execution        Not authorised

The system should keep asset-specific settings in configuration rather
than scattering ticker and market assumptions across source code.
Reusable functions should accept the ticker or asset configuration as
input.

------------------------------------------------------------------------

## 3. Approved Historical Data Source

### 3.1 Provider and access method

The sole approved market-data source for the current project workflow is
**Yahoo Finance**, accessed through the Python library **`yfinance`**.

The project must not maintain parallel acquisition paths for other
market-data vendors. Active documentation, configuration, scripts and
tests should consistently describe Yahoo Finance/`yfinance` as the
approved source. Historical backups may be retained for audit or
recovery, but they are not part of the active acquisition workflow.

The acquisition layer should isolate provider-specific behaviour so that
data retrieval, validation, feature engineering and target generation
remain separable. A future change of provider would require a documented
decision and explicit approval; it must not happen silently as a
fallback.

### 3.2 Retrieval configuration

The current pilot history is configured from **1 January 2015 through 23
October 2026**, inclusive of available observations. The actual
downloaded history must always be inspected rather than assumed to cover
the full requested interval.

For the current pilot dataset, the audited file is:

`data/raw/yahoo/configured/LLOY.L.csv`

The audited snapshot contained 2,985 daily observations from 2 January
2015 through 23 October 2026. These counts describe that snapshot only.
They are not permanent expectations for future downloads, since
data-provider history, corrections and trading calendars may change.

The acquisition process must record the requested interval, retrieval
time, ticker, provider/library version where available, returned date
range, row count, field names and validation outcome. A successful
library call alone is not sufficient evidence that the returned dataset
is complete or suitable.

### 3.3 Provider limitations and reproducibility

Yahoo Finance data retrieved through `yfinance` is an external
dependency. Historical values may be revised, fields may be unavailable
for some instruments, and retrieval behaviour may change with provider
or library updates. The project should therefore retain an auditable
copy of each dataset used for a formal experiment and record enough
metadata to identify that snapshot.

The project must not imply that an externally retrieved dataset is
immutable or that a repeated request will necessarily return
byte-for-byte identical data. Reproducibility requires recording the
data snapshot actually used, not just the retrieval code.

The acquisition layer must handle network failures, empty responses,
missing required fields and malformed data explicitly. A failed or
incomplete retrieval must be reported as a failure; it must not silently
produce a valid-looking dataset or switch to another provider.

------------------------------------------------------------------------

## 4. Historical Data Requirements and Quality Controls

### 4.1 Required fields

The current daily source data includes the following fields:

-   `date`
-   `Open`
-   `High`
-   `Low`
-   `Close`
-   `Adj Close`
-   `Volume`
-   `Dividends`
-   `Stock Splits`
-   `ticker`

The initial feature set uses historical `Close` values only. `Open` and
`Close` are used for the approved forward-return target. The other raw
fields are retained for auditing and future approved analysis but are
not automatically included as model features.

### 4.2 Structural checks

Each acquired dataset must be checked for:

1.  presence of required columns;
2.  valid, parseable dates;
3.  non-missing ticker and date values;
4.  duplicate ticker-date observations;
5.  numeric and finite price values;
6.  positive values for required price fields;
7.  sensible row ordering and date coverage;
8.  missing values and unexpected data types; and
9.  unexplained changes in the returned date range or row count.

Checks must be logged with counts and affected dates where appropriate.
A validation report should distinguish a detected anomaly from a
confirmed provider error. Data should not be changed merely to make a
check pass.

### 4.3 OHLC consistency and known anomalies

The historical pilot audit identified three OHLC consistency anomalies:

  Date            Observed anomaly
  --------------- -------------------------
  31 March 2015   `Close` is below `Low`
  15 June 2020    `Low` is above `Open`
  1 May 2024      `Close` is above `High`

These observations have been preserved in the source history. They must
not be automatically corrected, deleted or winsorised without
investigation and explicit approval. The 15 June 2020 anomaly is
especially relevant for review because the approved target uses the next
session's `Open` as its entry reference. Any later treatment must be
documented, justified and applied consistently without using future
information.

The presence of an anomaly does not establish its cause. It could
reflect a source issue, adjustment convention, historical market-data
behaviour or another factor requiring investigation. Until that
investigation is completed and a treatment is approved, the original
observed values must remain traceable.

### 4.4 Missing values and lookback requirements

The seven approved candidate features require historical lookback
windows. Consequently, the first observations do not have every feature
available. In the audited pilot snapshot, the first 20 rows contain
lookback-related missing feature values; all later rows have all seven
features available.

These missing values are expected consequences of the feature
definitions, not evidence that future values should be used to fill
them. The initial feature pipeline must preserve missing values caused
by insufficient history. Observations requiring all seven features
should be excluded from a modelling operation until those features are
available at the forecast cutoff. Any exclusion must be recorded with a
reason.

Target values that cannot yet be calculated because the required future
session has not occurred are different from invalid data. Such targets
must remain pending/unmatured, not be treated as zero returns or as
failed observations.

### 4.5 Data changes and auditability

Raw data should be preserved separately from derived datasets.
Validation, feature engineering and target generation should operate on
copies or produce new outputs rather than silently rewriting the source
file.

For each formal dataset snapshot, retain:

-   the source ticker and retrieval configuration;
-   the acquisition timestamp and relevant software versions;
-   the observed start and end dates and row count;
-   the validation report and anomaly counts;
-   the definitions and versions of derived features and targets; and
-   a reference to the code revision used to produce the derived
    dataset.

Any change in source data or data-handling rules must be distinguishable
from a change in model performance.

------------------------------------------------------------------------

## 5. Initial Trading and Portfolio Configuration

### 5.1 Strategy scope

The initial research scope is **swing trading using daily
observations**. Forecasts are produced after the close of an observed
trading session. The system is intended to support decisions over short
forward horizons rather than intraday execution.

The system should distinguish a statistical forecast from a trading
action. A forecast may be positive while the expected edge after costs
is insufficient, the uncertainty is too high, or risk controls prohibit
a trade. Therefore, forecast direction alone must not determine a BUY or
SELL decision.

### 5.2 Hypothetical portfolio

The approved starting capital for simulation is **GBP 1,000**. This is a
hypothetical research portfolio, not a deposit or authorisation to trade
real funds.

Any future portfolio simulation must make explicit its assumptions about
position sizing, available cash, fractional or whole-share constraints,
trading fees, bid-ask spread, slippage, taxes where applicable,
corporate-action cash flows and the timing of order execution.
Assumptions must be realistic for the selected market and must be
recorded before performance results are interpreted.

The portfolio balance must not be used to imply that a strategy is
suitable for an individual's circumstances. The project is for research
and decision support.

### 5.3 Decision outputs

The planned decision-support layer may produce **BUY, HOLD, SELL or
WAIT** recommendations, together with forecast estimates, probabilities
or uncertainty measures, relevant risk information and reasons for the
proposed action. These labels require a separately documented decision
policy; they are not direct synonyms for a positive or negative point
forecast.

A signal must be traceable to the data cutoff, model version, forecast
horizon, model authorisation status, decision-policy version and risk
checks in force at the time. If the required model or data checks fail,
the system must not invent a new forecast or silently reuse an
unauthorised model.

### 5.4 Retraining cadence

The approved initial operational design is to generate forecasts after
each observed trading-session close and retrain weekly, after the final
observed trading session of each week. Friday is the usual weekly cutoff
when the exchange is open; if Friday is not a trading session, use the
last observed session of that week.

Between scheduled retraining events, the authorised model remains fixed.
Retraining frequency is a methodological choice to be evaluated later;
it is not evidence that weekly retraining will outperform other
schedules.

If retraining fails, preserve the last successfully authorised model and
its artefacts, but do not automatically activate it to produce new
forecasts. Record the failed attempt, cutoff, affected session and
failure reason. No new forecast should be issued until a model has
passed the required checks and is explicitly authorised. Previously
recorded forecasts must never be overwritten.

------------------------------------------------------------------------

## 6. Forecast Horizons and Target Definition

### 6.1 Approved horizons

The initial forecasting horizons are **1, 5 and 10 trading sessions**.
These horizons are measured using observed sessions in the relevant
instrument's historical series, not by adding calendar days.

### 6.2 Approved target formula

For forecast origin session (t) and horizon (h), the approved gross
forward return is:

\[ R(t,h) = `\frac{Close(t+h)}{Open(t+1)}`{=tex} - 1 \]

The forecast is generated after the close of session (t). The reference
entry price is the `Open` of the next observed trading session, (t+1),
and the reference exit price is the `Close` of session (t+h).

For (h=1), both reference prices relate to the next trading session:
entry at its open and exit at its close. For longer horizons, the
reference exit is the close of the session (h) sessions after the
forecast origin.

This is a gross execution-price return before transaction costs,
slippage, taxes and dividend cash flows. Those items must be considered
separately in a realistic trading simulation.

**The formula is an approved project decision and must not be changed
without explicit approval.** Any proposed alternative target must be
documented as a separate proposal, not silently substituted into the
current target columns.

### 6.3 Target maturity

A target is eligible for supervised training or evaluation only when its
outcome has become observable. Maturity must be calculated separately
for the 1-, 5- and 10-session horizons using actual historical sessions.

-   Development observations are eligible only when their targets have
    fully matured by the Development period end.
-   At each walk-forward training cutoff, only observations whose target
    outcomes were known by that cutoff may be used.
-   Final Test forecasts may be retained while their outcomes are
    pending. Their results must remain pending until the relevant
    horizon matures.
-   A missing future target must not be interpreted as a zero return.
-   No feature, label, threshold or model-selection decision may use
    information from after its relevant cutoff.

The system must preserve the difference between forecast origin, target
maturity date and evaluation period. This is essential to prevent
leakage in chronological modelling.

------------------------------------------------------------------------

## 7. Historical Periods and Evaluation Boundaries

The approved temporal design uses consecutive windows relative to the
latest available observed session in the selected asset history:

-   **Development:** 7 years;
-   **Walk-forward Validation:** 2 years; and
-   **Final Test:** 1 year.

Period boundaries are aligned to actual observed sessions. The windows
must be consecutive, non-overlapping and free of gaps within the defined
evaluation periods. Earlier history may remain available for feature
lookback where appropriate, but it must not be misrepresented as part of
the formal evaluation windows.

The current pilot audit produced these periods:

  Period                    Start             End                 Observations
  ------------------------- ----------------- ----------------- --------------
  Development               24 October 2016   20 October 2023            1,766
  Walk-forward Validation   23 October 2023   22 October 2025              507
  Final Test                23 October 2025   23 October 2026              254

These dates and counts describe the audited snapshot and should be
recalculated from the latest available session when data is refreshed.
They must not be hard-coded as permanent boundaries.

Final Test is isolated from model-family selection, feature selection,
hyperparameter tuning, threshold selection and strategy design. It is
used for final evaluation only under the approved protocol. A result
observed on Final Test must not be used to revise the system and then
reported as an unbiased final result for that revised system.

------------------------------------------------------------------------

## 8. Initial Feature Scope

The approved initial candidate features are derived from historical
`Close` prices:

  -----------------------------------------------------------------------
  Feature                             Definition
  ----------------------------------- -----------------------------------
  `close_return_1d`                   `Close(t) / Close(t-1) - 1`

  `close_return_5d`                   `Close(t) / Close(t-5) - 1`

  `close_return_10d`                  `Close(t) / Close(t-10) - 1`

  `close_return_20d`                  `Close(t) / Close(t-20) - 1`

  `close_volatility_5d`               Sample standard deviation
                                      (`ddof=1`) of the latest 5
                                      one-session returns

  `close_volatility_10d`              Sample standard deviation
                                      (`ddof=1`) of the latest 10
                                      one-session returns

  `close_volatility_20d`              Sample standard deviation
                                      (`ddof=1`) of the latest 20
                                      one-session returns
  -----------------------------------------------------------------------

The initial feature set deliberately excludes raw OHLC values,
`Adj Close`, `Volume`, `Dividends` and `Stock Splits` as model inputs.
The target calculation still uses `Open` and `Close` as specified.
Expanding the feature set requires a documented rationale and approval.

Feature values for forecast origin (t) may use only information
available at or before the close of (t). Calculations must be performed
independently for each ticker, ordered by date, and must not mix
observations from different instruments. Rolling volatility uses
complete windows and the sample standard deviation. No initial missing
feature value may be filled with future information.

Feature engineering, preprocessing and any scaling or imputation must be
fitted within the relevant training data only. Validation and Final Test
information must not leak into fitted transformations.

------------------------------------------------------------------------

## 9. Data-Source and Asset Change Control

The following changes require documented review and explicit approval
before they enter the active workflow:

-   replacing Yahoo Finance/`yfinance` with another provider;
-   adding a second provider as a silent fallback;
-   changing the pilot asset or its provider symbol;
-   changing the target formula or forecast horizons;
-   adding or removing candidate features;
-   altering the temporal window design or target-maturity rules;
-   changing the retraining cadence or failure policy; and
-   changing the treatment of known OHLC anomalies.

A change proposal should explain the reason, expected benefit, risks,
affected artefacts and tests required. The project should preserve the
previous approved behaviour until the change has been reviewed.
Data-provider changes require renewed coverage, quality, consistency and
reproducibility checks.

The active documentation, source code, tests and configuration must
agree on the approved decisions. Searches of active project files should
not reveal stale provider or pilot-asset recommendations. Historical
backup material may contain prior decisions for recovery purposes, but
must remain clearly separated from active specifications.

------------------------------------------------------------------------

## 10. Readiness Criteria Before Modelling

Selection of an asset and provider does not itself authorise model
training. Before modelling begins, the project must demonstrate that:

1.  the acquired data has a documented snapshot and passes the required
    structural checks;
2.  known anomalies are recorded and have an explicit handling status;
3.  feature definitions are implemented and tested against the
    specification;
4.  targets match the approved formula at every horizon;
5.  target maturity is calculated without using future observations
    prematurely;
6.  temporal windows are chronological, consecutive and non-overlapping;
7.  walk-forward training eligibility is verified at each relevant
    cutoff;
8.  Final Test is excluded from model selection and training;
9.  baseline definitions and evaluation metrics are documented; and
10. the user has reviewed the relevant data, target and
    temporal-validation evidence and explicitly approved progression.

Until those gates are met, the work should remain focused on data
integrity, target construction, temporal eligibility and
reproducibility. No model result should be fabricated or assumed from
code that has not been executed and verified.

------------------------------------------------------------------------

## 11. Approved Decisions Summary

  -----------------------------------------------------------------------
  Area                                Approved decision
  ----------------------------------- -----------------------------------
  Pilot asset                         Lloyds Banking Group ordinary
                                      shares

  Provider symbol                     `LLOY.L`

  Exchange                            London Stock Exchange

  Pilot currency                      GBP

  Supported exchanges                 LSE, NYSE and Nasdaq, subject to
                                      eligibility checks

  Historical data source              Yahoo Finance

  Python access library               `yfinance`

  Pilot history configuration         1 January 2015 to 23 October 2026;
                                      actual available sessions must be
                                      audited

  Initial simulated capital           GBP 1,000

  Strategy scope                      Daily-data swing-trading research

  Forecast horizons                   1, 5 and 10 trading sessions

  Approved return target              `Close(t+h) / Open(t+1) - 1`

  Candidate features                  Four historical close returns and
                                      three rolling close-return
                                      volatilities

  Temporal windows                    7-year Development, 2-year
                                      Walk-forward Validation, 1-year
                                      Final Test

  Forecast cadence                    After each observed session close

  Initial retraining cadence          Weekly, after the final observed
                                      session of the week

  Final Test use                      Isolated final evaluation

  Model training authorisation        Requires separate explicit approval
                                      after reviewing data, targets and
                                      temporal validation
  -----------------------------------------------------------------------

## Conclusion

The current approved pilot is Lloyds Banking Group (`LLOY.L`) using
daily historical data retrieved from Yahoo Finance through `yfinance`,
with a hypothetical portfolio of GBP 1,000 and 1-, 5- and 10-session
forecast horizons. The system is designed to support research and
disciplined decision-making, with strict chronological validation,
explicit target maturity, documented data quality controls and
separation between forecasts and trading actions.

The pilot choice is a starting point for controlled evaluation, not a
conclusion about profitability. The next stages must establish that the
data pipeline, feature definitions, targets and temporal eligibility
rules are correct and reproducible. Model training and strategy
evaluation remain gated by review and explicit approval.
