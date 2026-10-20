# AI Quantitative Trading & Decision Intelligence System

## Phase 1 — Asset and Data-Source Selection

**Document version:** 0.1 — Preliminary research report
**Project stage:** Phase 1
**Initial capital:** USD 10,000
**Market:** US equities listed on Nasdaq or NYSE
**Strategy:** Long-only swing trading using daily data
**Status:** Preliminary recommendations awaiting approval

---

## 1. Executive Summary

Phase 1 evaluates four candidate stocks:

* Microsoft (MSFT)
* Apple (AAPL)
* NVIDIA (NVDA)
* Tesla (TSLA)

It also examines three historical market-data providers:

* Tiingo
* Polygon.io
* Alpha Vantage

The evaluation follows the provisional asset-selection framework established in Phase 0:

| Criterion                                    |   Weight |
| -------------------------------------------- | -------: |
| Data quality and historical coverage         |      25% |
| Liquidity and transaction-cost feasibility   |      25% |
| Suitability for the intended trading horizon |      20% |
| Risk characteristics                         |      20% |
| Reproducibility and data-source suitability  |      10% |
| **Total**                                    | **100%** |

These weights remain provisional and unvalidated.

The research supports the following preliminary recommendations:

1. **Initial asset: AAPL**, subject to historical-data validation and the planned sensitivity analysis.
2. **Initial data provider: Tiingo**, subject to confirming actual account access, historical coverage, applicable terms, and data quality.
3. **Alternative asset: MSFT**, providing a useful comparison against AAPL.
4. **Alternative provider: Polygon.io**, particularly if a longer historical dataset becomes necessary and its subscription cost is justified.

No claim is made that AAPL will produce the highest returns or that any candidate is inherently profitable to trade.

## 2. Candidate Asset Comparison

### 2.1 Microsoft (MSFT)

Microsoft is a large, established company listed on Nasdaq.

The available market statistics indicate a five-year beta of approximately 1.10 and average trading volume of approximately 21.2 million shares over 20 sessions in the source snapshot. These figures suggest substantial trading activity and market sensitivity relatively close to that of the broader market.

**Advantages**

* Substantial trading activity.
* A relatively moderate beta among the four candidates.
* A long public trading history.
* Suitable for testing whether a model can identify opportunities in a highly liquid, widely followed stock.

**Limitations**

* The share price affects how many whole shares can be purchased with USD 10,000.
* Earnings announcements and other company-specific events can affect short-horizon returns.
* Large-company status does not guarantee low transaction costs or stable predictive relationships.

**Preliminary assessment:** A strong candidate and the leading alternative to AAPL.

### 2.2 Apple (AAPL)

Apple is a large, established company listed on Nasdaq.

The available market statistics indicate a five-year beta of approximately 1.07 and average trading volume of approximately 36.9 million shares over 20 sessions in the source snapshot. These figures support its suitability for further evaluation as a liquid, relatively market-aligned candidate.

**Advantages**

* Substantial trading activity.
* A relatively moderate beta among the candidates.
* A long public trading history.
* Suitable for studying daily price movements without beginning with the most volatile candidate.
* A useful comparison with MSFT because both are large technology companies but have different business and market drivers.

**Limitations**

* Its technology-sector exposure may cause some risks to be shared with MSFT and NVDA.
* Company announcements and broader market conditions can still produce abrupt price movements.
* Liquidity and beta alone cannot establish forecasting suitability.

**Preliminary assessment:** Recommended as the initial research asset, subject to a consistent historical comparison.

### 2.3 NVIDIA (NVDA)

NVIDIA is a Nasdaq-listed semiconductor and AI-infrastructure company.

The available statistics indicate a five-year beta of approximately 2.22. A separate historical-market-data source reports average daily trading volume of tens of millions of shares, indicating substantial trading activity.

**Advantages**

* Substantial trading activity.
* Potentially informative price movements for investigating short-horizon forecasting.
* Suitable for later assessing whether the system can handle higher-volatility assets.

**Limitations**

* Higher market sensitivity can increase portfolio risk.
* Semiconductor and AI-related market developments may produce concentrated, regime-dependent behaviour.
* Large price movements do not necessarily translate into profitable opportunities after costs and risk constraints.

**Preliminary assessment:** A strong candidate for a later comparative experiment, but not the default first asset.

### 2.4 Tesla (TSLA)

Tesla is listed on Nasdaq and operates in electric vehicles, energy generation, and storage.

The available statistics indicate a five-year beta of approximately 1.92, suggesting higher market sensitivity than AAPL or MSFT. Its historical statistics also show substantial trading activity.

**Advantages**

* Substantial trading activity.
* A useful candidate for studying volatile price behaviour.
* Suitable for testing whether forecasting performance changes significantly under more challenging market conditions.

**Limitations**

* Higher market sensitivity.
* Potentially pronounced company-specific and event-driven movements.
* A more challenging starting point for separating genuine predictive value from volatility and market-regime effects.

**Preliminary assessment:** Retain as a comparison candidate, but do not prioritise it as the first asset.

## 3. Preliminary Asset Comparison

| Criterion                        | MSFT               | AAPL                    | NVDA                         | TSLA                         |
| -------------------------------- | ------------------ | ----------------------- | ---------------------------- | ---------------------------- |
| Market and listing               | Nasdaq             | Nasdaq                  | Nasdaq                       | Nasdaq                       |
| Trading activity                 | High               | High                    | High                         | High                         |
| Relative market sensitivity      | Moderate           | Moderate                | Higher                       | Higher                       |
| Potential short-horizon movement | To be measured     | To be measured          | To be measured               | To be measured               |
| Historical-data suitability      | To be verified     | To be verified          | To be verified               | To be verified               |
| Transaction-cost feasibility     | To be measured     | To be measured          | To be measured               | To be measured               |
| Initial recommendation           | Strong alternative | **Preferred candidate** | Secondary research candidate | Secondary research candidate |

The qualitative assessment supports prioritising AAPL and MSFT for the next stage of comparison.

However, the current evidence does not constitute a complete quantitative ranking. The reported beta and volume figures are provider snapshots, and their observation dates and calculation conventions are not fully harmonised. They must not be combined as if they came from one consistently processed dataset.

## 4. Asset-Selection Sensitivity Analysis

### 4.1 Why sensitivity analysis is necessary

The Phase 0 weights are planning assumptions, not validated parameters.

A candidate that ranks first under one weighting scheme may rank lower when the relative importance of risk, liquidity, or historical coverage changes.

The project must therefore test whether the preferred candidate is robust to reasonable alternatives.

### 4.2 Proposed weighting scenarios

The following scenarios are proposed for the quantitative sensitivity analysis.

| Criterion                                    | Baseline | Risk emphasis | Data and liquidity emphasis |
| -------------------------------------------- | -------: | ------------: | --------------------------: |
| Data quality and historical coverage         |      25% |           20% |                         35% |
| Liquidity and transaction-cost feasibility   |      25% |           20% |                         30% |
| Suitability for the intended trading horizon |      20% |           15% |                         15% |
| Risk characteristics                         |      20% |           35% |                         10% |
| Reproducibility and data-source suitability  |      10% |           10% |                         10% |
| **Total**                                    | **100%** |      **100%** |                    **100%** |

The baseline preserves the approved Phase 0 weights. The other two scenarios are proposed sensitivity cases, not additional approved decision rules.

### 4.3 Required quantitative procedure

Once the historical dataset has been obtained and validated, the analysis will:

1. Apply common eligibility criteria to all four stocks.
2. Calculate comparable liquidity, volatility, and historical-coverage measures over the same observation period.
3. Define a documented scoring scale for every criterion.
4. Separate eligibility failures from weighted scores.
5. Score each candidate under each weighting scenario.
6. Examine ranking stability and identify which criteria drive any changes.
7. Record all source limitations and scoring assumptions.

The scoring scale must be established before reviewing the final rankings.

**Current status:** The sensitivity-analysis design is proposed, but the numerical sensitivity analysis has not been executed. Assigning final numerical scores without a consistently collected and validated dataset would create false precision.

## 5. Historical Data-Provider Comparison

### 5.1 Tiingo

Official documentation: [Tiingo End-of-Day API Documentation](https://www.tiingo.com/documentation/end-of-day?utm_source=chatgpt.com)

Tiingo documents historical daily prices through a REST API and provides both raw and adjusted OHLCV fields. Its documentation also describes dividend and split information and a price-adjustment methodology based on CRSP calculations.

Its product page reports coverage of more than 80,000 tickers, including US equities, and historical data extending back to 1962 for supported coverage. The page lists a free individual plan with 50 hourly requests and 1,000 daily requests, subject to its stated terms and entitlements.

**Advantages**

* Daily historical OHLCV data.
* Raw and adjusted price fields.
* Documented dividend and split adjustments.
* REST API access suitable for a Python-based workflow.
* A free individual plan that may be sufficient for initial research, subject to entitlement and terms.

**Limitations and checks**

* Coverage and start dates must be verified for each candidate ticker.
* The exact adjustment conventions must be tested against the project's target definitions.
* The plan's licence must be checked for the intended use.
* Data completeness, revisions, missing observations, and reproducibility must be assessed.
* Historical depth advertised at product level does not guarantee equivalent history for every ticker.

**Preliminary assessment:** Preferred provider for initial evaluation because its documented adjusted and raw daily price fields align well with the project's requirements.

### 5.2 Polygon.io

Official product page: [Polygon Stocks Data and Pricing](https://polygon.io/stocks?gad_source=1&hsa_acc=4299129556&hsa_ad=592050131160&hsa_cam=13075782420&hsa_grp=133850773166&hsa_kw=stock+data&hsa_mt=p&hsa_net=adwords&hsa_src=g&hsa_tgt=kwd-298368892789&hsa_ver=3&utm_source=chatgpt.com)

Polygon documents historical daily aggregates covering open, high, low, close, and volume. Its published product information lists the following individual-use plans in the retrieved snapshot:

* Basic: USD 0 per month, two years of historical data and five API calls per minute.
* Starter: USD 29 per month, five years of historical data.
* Developer: USD 79 per month, ten years of historical data.
* Advanced: USD 199 per month, more than 20 years of historical data and real-time access.

These prices and entitlements should be rechecked before subscription because product plans may change.

**Advantages**

* Documented daily aggregate data.
* Reference data and corporate-action features.
* A clear upgrade path as historical-depth requirements increase.
* Potential suitability for more advanced market-data requirements later.

**Limitations and checks**

* The free tier's two-year history may be insufficient for the project's full regime and walk-forward evaluation requirements.
* The cost of obtaining a longer history must be justified against the project budget.
* Exact adjustment behaviour, ticker coverage, and applicable licensing terms must be verified for the selected plan.

**Preliminary assessment:** Strong alternative, especially if the project later needs a broader or longer historical dataset.

### 5.3 Alpha Vantage

Official documentation: [Alpha Vantage API Documentation](https://www.alphavantage.co/documentation/?utm_source=chatgpt.com)

Alpha Vantage documents daily equity time series and an adjusted daily endpoint that includes adjusted closing prices and historical split and dividend events. Its documentation states that full-length daily history of more than 25 years is available through the premium-access route for the relevant endpoint.

**Advantages**

* Straightforward REST API.
* Documented daily equity history.
* Adjusted daily endpoint with corporate-action information.
* Potentially suitable for research and data-provider comparison.

**Limitations and checks**

* Full historical access requires appropriate premium access for the documented endpoint.
* The project's OHLCV and adjustment requirements must be verified against the exact endpoint and plan.
* API limits, costs, licence terms, and historical completeness must be assessed before selection.

**Preliminary assessment:** A viable alternative, but Tiingo currently appears better aligned with the initial evaluation requirements based on the documentation reviewed.

## 6. Data-Provider Comparison

| Requirement                       | Tiingo                                                                | Polygon.io                                             | Alpha Vantage                                                  |
| --------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------------- |
| Daily historical prices           | Documented                                                            | Documented                                             | Documented                                                     |
| OHLCV fields                      | Documented                                                            | Documented                                             | Documented                                                     |
| Adjusted price information        | Raw and adjusted OHLCV                                                | Adjustment behaviour to verify for the chosen endpoint | Adjusted endpoint documented                                   |
| Corporate-action information      | Documented dividend and split fields                                  | Corporate-action features documented                   | Split and dividend events documented                           |
| Long historical coverage          | Product advertises extensive history; ticker coverage must be checked | Depends on plan                                        | Full history requires premium access for the relevant endpoint |
| Python integration                | REST API                                                              | REST API                                               | REST API                                                       |
| Initial research suitability      | **Preferred for evaluation**                                          | Strong alternative                                     | Viable alternative                                             |
| Account access verified           | No                                                                    | No                                                     | No                                                             |
| Actual data downloaded and tested | No                                                                    | No                                                     | No                                                             |

This comparison is based on provider documentation, not a completed technical test. It does not establish that any provider's data is error-free.

## 7. Preliminary Recommendations

### 7.1 Initial asset: AAPL

AAPL is the preferred candidate for initial research because the available evidence supports substantial trading activity and relatively moderate market sensitivity.

The choice is intended to provide a practical starting point for investigating daily swing-trading forecasts without beginning with the higher beta observed for NVDA and TSLA.

MSFT should remain the principal alternative.

The final selection must be revisited if consistent historical measurements, data-quality checks, or the sensitivity analysis materially change the ranking.

### 7.2 Initial data provider: Tiingo

Tiingo is the preferred provider to evaluate first because its documentation explicitly describes:

* Daily historical prices.
* Raw and adjusted OHLCV fields.
* Dividend and split information.
* REST API access.
* An individual free tier that may be adequate for an initial research prototype.

The recommendation remains conditional on verifying the required ticker coverage, account access, applicable terms, and actual data quality.

### 7.3 Alternative provider: Polygon.io

Polygon should remain the principal alternative if Tiingo's coverage, data quality, or licensing terms prove unsuitable.

Its paid historical-data options may also become relevant if the project requires a longer dataset than the initial available plan supports.

## 8. Evidence Limitations

The present report does not claim that:

* The four assets have been scored using a consistent historical dataset.
* The provisional weights have been validated.
* The sensitivity analysis has been quantitatively completed.
* A data-provider account has been created.
* Any API has been tested.
* Historical data has been downloaded or validated.
* The proposed asset has been demonstrated to be profitable to trade.

The current recommendation is a documented preliminary decision based on the available market-statistics snapshots and provider documentation.

A subsequent data-validation exercise must establish the actual historical coverage, data quality, adjustment conventions, missing-data patterns, and reproducibility before the research proceeds to formal model evaluation.

## 9. Phase 1 Status

| Item                                       | Status                                     |
| ------------------------------------------ | ------------------------------------------ |
| Candidate assets identified                | Complete                                   |
| Preliminary comparative research           | Complete                                   |
| Provisional weighting framework retained   | Complete                                   |
| Sensitivity scenarios proposed             | Complete                                   |
| Quantitative sensitivity analysis          | Not yet executed                           |
| Data-provider documentation compared       | Complete                                   |
| Initial asset recommendation               | Awaiting approval                          |
| Initial provider recommendation            | Awaiting approval                          |
| Historical data acquisition and validation | Not yet performed                          |
| Phase 1 completion                         | Pending approval and required verification |

## 10. Approval Required

The following recommendations are submitted for review:

1. **AAPL as the initial research asset**, with MSFT retained as the principal alternative.
2. **Tiingo as the first data provider to evaluate**, with Polygon.io retained as the principal alternative.
3. The three proposed weighting scenarios as the starting design for the quantitative sensitivity analysis.

Approval of these recommendations will establish the working direction for the next step. It will not, by itself, constitute evidence that the asset-selection methodology has been empirically validated or that the provider's data has passed quality checks.
