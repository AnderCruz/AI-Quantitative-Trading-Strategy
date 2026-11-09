# Phase 3 — Final Data Quality Assessment Report

**Project:** AI Quantitative Trading & Strategy Optimisation System  
**Pilot Asset:** National Grid (NG.L)  
**Architecture:** Multi-asset  
**Phase:** 3 — Data Quality Assessment  
**Status:** COMPLETE  
**Scope:** Data quality, temporal integrity, point-in-time eligibility and auditability.

---

## 1. Executive Summary

Phase 3 assessed the quality, structural integrity, temporal characteristics and usability of the acquired market, interest rate and macroeconomic datasets.

The assessment identified several limitations involving historical availability, corporate actions, acquisition metadata, historical vintages and source frequencies.

The original acquired data has been preserved. No automatic corrections, imputations or deletions were performed during this phase.

The datasets have been classified according to their quality and temporal eligibility.

**Overall conclusion: Phase 3 is complete, with documented limitations and residual risks.**

The acquired datasets are suitable for progressing to exploratory data analysis under the restrictions established in this report. This conclusion does not imply that every dataset is eligible for strict point-in-time backtesting.

## 2. Phase 3 Completion Summary

| Step | Description | Status |
|---|---|---|
| 3.1 | Data Inventory and Baseline Inspection | Complete |
| 3.2 | Equity Data Quality Assessment | Complete |
| 3.3 | Interest Rate Data Quality Assessment | Complete |
| 3.4 | Macroeconomic Data Quality Assessment | Complete |
| 3.5 | Market Calendar and Timezone Validation | Complete |
| 3.6 | Cross-Asset and Macroeconomic Temporal Alignment | Complete |
| 3.7 | Final Data Validation and Phase Closure | Complete |

## 3. Equity Data Quality Assessment

Datasets:
- National Grid (NG.L)
- SSE plc (SSE.L)
- Severn Trent (SVT.L)
- FTSE 100 (^FTSE)

Total acquired observations: 37,409.

### Findings

- CSV and Parquet representations were consistent.
- File integrity was confirmed.
- Missing and zero-volume observations were identified.
- OHLC inconsistencies were detected in NG.L, SSE.L and SVT.L.
- Adjusted Close and Close differences were consistent with dividend adjustments.
- Yahoo Finance corporate action information was found to be incomplete.
- Historical NG.L rights issues require particular attention.
- Price denomination requires explicit GBP/GBp handling.

### Classification

| Dataset | Classification |
|---|---|
| NG.L | Accept with limitations |
| SSE.L | Accept with limitations |
| SVT.L | Accept with limitations |
| FTSE 100 | Accept with limitations |

The identified anomalies must remain documented and must not be silently corrected.

## 4. Interest Rate Data Quality Assessment

Datasets:
- Bank Rate
- SONIA
- Gilt nominal 2Y spot curve
- Gilt nominal 10Y spot curve

### Final Classification — Decision D-P3-023

| Dataset | Data Quality | PIT Classification |
|---|---|---|
| Bank Rate | Accept with limitations | PIT_CONDITIONAL |
| SONIA | Accept with limitations | PIT_CONDITIONAL |
| Gilt 2Y | Accept with limitations | PIT_UNVALIDATED |
| Gilt 10Y | Accept with limitations | PIT_UNVALIDATED |

### Bank Rate

- 13,104 observations.
- No invalid dates or duplicate observations.
- No missing or non-numeric values in the complete files.
- Two complete acquisitions and 15 partial acquisitions.
- Ten extreme historical movements checked against the official Bank of England series.

The 15 partial acquisitions were incorrectly recorded as successful acquisitions. Their physical integrity is confirmed, but their semantic validity remains inadequate.

### SONIA

- 7,496 observations.
- No invalid dates or duplicate observations.
- No missing or non-numeric values.
- Ten extreme movements checked against the official series.
- Methodological change effective 23 April 2018.

A conservative availability policy of 10:00 on the next London business day is adopted for the Bank of England database series.

### Gilt Curves

- Eight original workbooks.
- 12,480 unique dated observations.
- 12,090 valid observations per maturity.
- 390 missing observations per maturity.
- Identical missing dates across both maturities.

Historical availability and vintage reconstruction remain unverified.

Gilt datasets are not eligible for strict PIT backtesting.

## 5. Macroeconomic Data Quality Assessment

Datasets:

| Dataset | Frequency | Data Quality | PIT Classification |
|---|---|---|---|
| CPI | Annual, quarterly and monthly | Accept with limitations | PIT_CONDITIONAL |
| Core CPI | Annual, quarterly and monthly | Accept with limitations | PIT_CONDITIONAL |
| CPIH | Annual, quarterly and monthly | Accept with limitations | PIT_CONDITIONAL |
| Real GDP | Annual and quarterly | Accept with limitations | PIT_UNVALIDATED |
| GDP Growth | Quarterly | Accept with limitations | PIT_UNVALIDATED |

### Main Findings

- Source files contain overlapping frequency representations.
- All five series were structurally inspected.
- No automatic transformations or frequency conversions were performed.
- Current ONS files do not provide complete historical publication timestamps for every observation.
- Historical vintages have not been fully reconstructed.

GDP datasets are not eligible for strict PIT backtesting until historical vintage limitations are resolved.

## 6. Market Calendar and Timezone Validation

The following operational rules were approved:

| Parameter | Policy |
|---|---|
| Primary trading calendar | LSE (XLON) |
| Operational timezone | Europe/London |
| Internal timestamp storage | UTC |
| Trading cut-off | 17:00 Europe/London |
| Signal generation | After market close |
| Earliest execution | Next LSE session |

GMT/BST transitions were validated.

The calendar library's historical coverage and exceptional closures remain subject to documented limitations.

## 7. Temporal Alignment and PIT Framework

Decisions D-P3-030 to D-P3-048 establish the temporal architecture and eligibility framework.

Core requirements:

1. Observation dates must be preserved.
2. Availability timestamps must not be fabricated.
3. Acquisition timestamps must be traceable.
4. Historical vintages must be preserved when available.
5. Source-specific calendars and frequencies must be respected.
6. No automatic forward-fill or synthetic weekend observations.
7. No future information may enter historical features.
8. Forecast targets must remain separate from model features.
9. Signals generated after market close must execute no earlier than the next LSE session.
10. Temporal eligibility decisions must be auditable.

The fundamental availability conditions are:

AvailabilityTimestamp <= DecisionTimestamp

AcquisitionTimestamp <= DecisionTimestamp

PIT classifications:

| Classification | Research | Model Training | Strict PIT Backtesting |
|---|---|---|---|
| PIT_VALIDATED | Allowed | Allowed | Allowed |
| PIT_CONDITIONAL | Allowed | With restrictions | Conservative policy only |
| PIT_UNVALIDATED | Allowed | Documented limitations | Not allowed |

PIT eligibility does not imply licensing or commercial-use permission.

## 8. File Integrity Assessment

The manifest and physical file checks covered:

| Indicator | Result |
|---|---:|
| Manifests | 25 |
| Files verified | 29 |
| Missing files | 0 |
| Size mismatches | 0 |
| SHA256 mismatches | 0 |

Physical file integrity was confirmed for the referenced acquisition files.

This does not imply semantic data quality or historical PIT validity.

## 9. Outstanding Risks

The following risks remain documented:

| Risk ID | Description | Priority | Status |
|---|---|---|---|
| R-P3-001 | Partial Bank Rate acquisitions | Medium | Open |
| R-P3-009 | Historical dividend discrepancies | Medium | Open |
| R-P3-010 | Incomplete Yahoo Finance corporate actions | High | Open |
| R-P3-011 | NG.L historical price discrepancy | Medium | Open |
| R-P3-021 | Gilt historical vintages | High | Open |
| R-P3-022 | Bank Rate publication timestamps | Medium | Open |
| R-P3-023 | Exceptional historical LSE closures | Medium | Open |
| R-P3-024 | Exchange calendar library changes | Low | Open |
| R-P3-025 | Macroeconomic frequency representation | Medium | Open |

Other partially resolved findings remain documented in the project risk register.

These risks do not prevent exploratory research, provided the stated dataset restrictions are respected.

## 10. Phase 3 Final Decisions

- D-P3-023: Final interest rate dataset classification approved.
- Existing PIT classifications retained.
- Original raw data preserved.
- No automatic corrections or imputations authorised.
- Temporal alignment policies retained.
- Dataset quality, PIT eligibility and licensing eligibility remain separate assessments.
- Outstanding risks transferred to the project risk register for treatment in appropriate future phases.

## 11. Phase 3 Exit Criteria

| Criterion | Result |
|---|---|
| Dataset inventory completed | PASS |
| Equity quality assessed | PASS |
| Interest rate quality assessed | PASS |
| Macroeconomic quality assessed | PASS |
| Calendar and timezone validated | PASS |
| Temporal alignment policies established | PASS |
| PIT eligibility classified | PASS |
| File integrity verified | PASS |
| Outstanding risks documented | PASS |
| Final assessment report completed | PASS |

## 12. Final Conclusion

Phase 3 — Data Quality Assessment is formally COMPLETE.

The project has established a documented understanding of the acquired datasets, their structural characteristics, quality limitations, temporal availability and point-in-time eligibility.

The datasets can progress to exploratory data analysis, subject to their individual restrictions.

No dataset is automatically promoted to unrestricted model training or strict PIT backtesting.

The next project phase is:

**Phase 4 — Exploratory Data Analysis (EDA).**

Progression requires explicit approval.