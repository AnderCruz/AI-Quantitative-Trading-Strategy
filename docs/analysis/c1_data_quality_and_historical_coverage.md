# C1 — Final Data Quality Decision

## Decision

**Status: CONDITIONALLY ACCEPTED FOR PREDICTIVE RESEARCH**

The configured `LLOY.L` historical dataset is conditionally accepted for the project's predictive research phase. The decision is based on the completed structural checks, historical coverage assessment, temporal eligibility audit, feature and target integration checks, and documented review of the three known OHLC inconsistencies.

This decision does not certify that the complete historical price series is free from errors. Full reconciliation of historical corporate actions and independent verification of all historical prices have not been completed.

## Evidence Reviewed

* Historical dataset: 2,985 observations from 2 January 2015 to 23 October 2026.
* Market-data source: Yahoo Finance via `yfinance`.
* Three documented OHLC inconsistencies: 31 March 2015, 15 June 2020 and 1 May 2024.
* Temporal periods, target maturity and walk-forward eligibility checks completed.
* Automated tests: 95 passed in the recorded test run.
* The source dataset remains unchanged.

## Known Limitations

The three OHLC inconsistencies remain unexplained. The historical relationship between raw and adjusted prices, dividend records, stock splits and other corporate actions has not been fully reconciled.

The existing preliminary impact analysis identified potentially affected features and targets. Its results are indicative and do not establish that every potentially exposed observation is materially incorrect.

The approved forecasting targets continue to represent gross price returns based on the specified Open and Close prices. Dividend cash flows, transaction costs, slippage and taxes are not included in those target returns.

## Conditions of Use

1. Preserve the original historical dataset and all three documented anomalies.
2. Do not silently correct or delete anomalous observations.
3. Retain the approved target definition and temporal-validation design.
4. Document these data limitations when interpreting model evaluation results.
5. Do not interpret forecasting performance as evidence of net trading profitability.
6. Reassess data eligibility only if subsequent evidence identifies a material issue affecting the validity of the analysis.

Dividend-inclusive portfolio accounting and realistic execution simulation require appropriate treatment of corporate actions, transaction costs and other relevant trading assumptions.

## Final Assessment

C1 is closed with a conditional acceptance for predictive research. No claim is made that the historical price series has been fully certified or that the resulting models will be profitable.

**Final status: CONDITIONALLY ACCEPTED FOR PREDICTIVE RESEARCH.**