# Phase 2 — Multi-Asset Data Acquisition
## Progress Register

**Project:** AI Quantitative Trading & Strategy Optimisation System
**Status:** In Progress
**Last updated:** 3 November 2026

---

## 1. Phase Objective

Implement the approved multi-asset data acquisition architecture and acquire the initial historical datasets required for subsequent data quality assessment and research.

Phase 2 covers acquisition architecture, provider configuration, historical acquisition, storage, integrity verification and acquisition documentation.

It does not include formal financial data quality approval, feature engineering or model development.

---

## 2. Overall Project Phase Status

| Phase | Description | Status |
|---|---|---|
| 0 | Project Definition & Technical Planning | Approved |
| 1 | Financial and Macroeconomic Data Sources Investigation | Approved |
| 2 | Multi-Asset Data Acquisition | In Progress |
| 3 | Data Quality Assessment & Temporal Alignment | Not Started |
| 4–16 | Subsequent research and implementation phases | Not Started |

---

## 3. Phase 2 Workstream Status

| Workstream | Description | Status |
|---|---|---|
| 2.1 | Data source and variable consolidation | Completed |
| 2.2.7 | Acquisition architecture design and approval | Completed |
| P0 | Initial National Grid historical acquisition | Completed |
| Group A | Equities acquisition and technical integrity verification | Completed |
| Group B | UK interest rates acquisition | Pending |
| Group C | UK energy data acquisition | Pending |
| Remaining sources | Acquisition according to the approved source priority and roadmap | Pending |
| Phase 2 closure | Consolidated evidence, documentation and approval | Pending |

---

## 4. Completed Deliverables

### 4.1 Phase 2.1 — Source and Variable Consolidation

The project established eight data groups:

1. Target asset.
2. Comparable companies.
3. Equity markets.
4. Rates and fixed income.
5. Energy and commodities.
6. Foreign exchange.
7. Macroeconomic indicators.
8. Credit and company fundamentals.

Acquisition priorities were defined, with NG.L as the initial pilot.

### 4.2 Phase 2.2.7 — Acquisition Architecture

The acquisition architecture was completed and approved.

Key deliverables include:

- Provider-independent adapter architecture.
- External YAML asset configurations.
- Pydantic configuration validation.
- Historical, fixed-range and incremental acquisition modes.
- Immutable Raw acquisition storage.
- Acquisition manifests and SHA-256 checksums.
- Atomic file commits.
- Dataset-specific watermarks and revision handling.
- Retry, backoff, rate-limit and circuit-breaker principles.
- Structured logging, audit trail and data lineage.

### 4.3 P0 — National Grid Historical Acquisition

**Asset:** National Grid
**Provider symbol:** NG.L
**Provider:** Yahoo Finance
**Frequency:** Daily

| Attribute | Result |
|---|---|
| Acquisition ID | `20261103T000455Z_8b505769` |
| Records | 7,890 |
| First observation | 1995-12-11 |
| Last observation | 2026-11-02 |
| Manifest status | success |
| Formats | CSV and Parquet |

Files are stored under:

`data/raw/market/yahoo_finance/NG.L/`

The acquisition report is:

`reports/acquisition/NG_L_acquisition_report.md`

### 4.4 Group A — Equities

**Scope:** SSE.L, SVT.L and ^FTSE.

| Asset | Acquisition ID | Records | First observation | Last observation |
|---|---|---:|---|---|
| SSE.L | `20261103T002507Z_de101edb` | 9,060 | 1991-06-17 | 2026-11-02 |
| SVT.L | `20261103T002515Z_fdac38df` | 9,455 | 1989-12-11 | 2026-11-02 |
| ^FTSE | `20261103T002524Z_9c7eb120` | 11,004 | 1984-01-03 | 2026-11-02 |
| **Total** | | **29,519** | | |

The acquisition produced CSV, Parquet and manifest files for each instrument.

**Technical integrity verification: PASSED**

The verification confirmed:

- CSV and Parquet files exist.
- File sizes match manifest metadata.
- SHA-256 checksums match.
- CSV and Parquet contents match after in-memory normalisation.
- Record counts, columns and date ranges match manifest metadata.

Verification script:

`scripts/verify_acquisition_integrity.py`

Consolidated report:

`reports/acquisition/EQUITIES_GROUP_A_ACQUISITION_REPORT.md`

**Scope limitation:** These checks establish file integrity and acquisition consistency. They do not establish financial data quality, corporate-action correctness, completeness of trading sessions, absence of market-data errors or temporal alignment suitability.

---

## 5. Current Repository Deliverables

| Path | Purpose | Status |
|---|---|---|
| `configs/assets/ng_l.yaml` | National Grid configuration | Created |
| `configs/assets/sse_l.yaml` | SSE configuration | Created |
| `configs/assets/svt_l.yaml` | Severn Trent configuration | Created |
| `configs/assets/ftse_100.yaml` | FTSE 100 configuration | Created |
| `scripts/acquire_market_data.py` | Configurable multi-asset acquisition | Implemented |
| `scripts/verify_acquisition_integrity.py` | Group A integrity verification | Implemented |
| `reports/acquisition/NG_L_acquisition_report.md` | NG.L acquisition report | Created |
| `reports/acquisition/EQUITIES_GROUP_A_ACQUISITION_REPORT.md` | Group A consolidated report | Created |
| `docs/DECISION_LOG.md` | Confirmed project decisions | Created |
| `docs/PHASE_2_PROGRESS_REGISTER.md` | Phase 2 progress register | Created |

Raw market data is stored locally under `data/raw/` and excluded from Git.

---

## 6. Dependencies and Environment

Current pinned dependencies:

- yfinance 1.7.0
- pyarrow 26.0.0
- pandas 3.1.0
- PyYAML 6.0.3
- pydantic 2.14.2

Environment reported by the user:

- Ubuntu 24.04.4 LTS
- Python 3.12.3
- Git 2.43.0

---

## 7. Outstanding Work

The following work remains before Phase 2 can be considered complete:

1. Acquire the approved UK interest-rate datasets (Group B).
2. Acquire the approved UK energy datasets (Group C).
3. Continue with the remaining approved source groups according to their priorities.
4. Record acquisition parameters, identifiers, manifests and limitations for every dataset.
5. Verify technical integrity and acquisition consistency.
6. Produce consolidated acquisition reports.
7. Update this register and the Decision Log as approved work is completed.
8. Review outstanding licensing, access and data-availability constraints.
9. Conduct a Phase 2 completion review and obtain explicit approval.

---

## 8. Risks and Limitations

| Risk | Current assessment | Mitigation |
|---|---|---|
| Yahoo Finance licensing | Commercial and redistribution rights not established | Restrict current use to exploratory research and review terms before commercial use |
| Provider data quality | Not formally assessed | Defer formal assessment to Phase 3 |
| Currency metadata | GBP configured for LSE instruments; independent provider verification remains necessary | Verify during data quality assessment |
| Historical completeness | Acquisition record counts alone do not establish completeness | Assess calendars and missing observations in Phase 3 |
| Corporate actions | Raw fields retained where available; correctness not yet assessed | Validate adjustment conventions and corporate actions in Phase 3 |
| Macro publication timing | Point-in-time controls required | Preserve publication timestamps and vintages |
| Provider availability | External provider access may change | Maintain independent connectors and acquisition audit records |

---

## 9. Phase 2 Exit Criteria

Phase 2 may only be closed when:

- All approved acquisition groups have been addressed or explicitly deferred with justification.
- Required datasets have acquisition records and manifests.
- Technical integrity checks have been completed.
- Data provenance and licensing limitations are documented.
- Acquisition reports and project registers are updated.
- Outstanding risks and limitations are recorded.
- The user explicitly approves Phase 2 closure.

Passing these criteria does not automatically approve datasets for modelling.

---

## 10. Current Gate

**Phase 2 status: IN PROGRESS**

Group A is complete at the acquisition and technical integrity level.

Formal data quality assessment and temporal alignment remain outside the current phase and must not begin until Phase 2 is completed and explicitly approved.

**Next planned workstream:** Group B — UK Interest Rates.
