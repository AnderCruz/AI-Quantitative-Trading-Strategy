# Phase 2 Final Acquisition Report
## AI Quantitative Trading & Strategy Optimisation System

**Report status:** Final
**Phase:** 2 — Multi-Asset Data Acquisition
**Reporting date:** 5 November 2026
**Closure decision:** D139 — Approved
**Related decision:** D138 — ONS MM23 and QNA Semantic Validation

---

## 1. Executive Summary

Phase 2 implemented the initial multi-asset acquisition architecture and completed the approved acquisition workstreams for:

- Group A — Equities;
- Group B — UK Interest Rates;
- Group C — UK Inflation and Macroeconomic Data.

The work delivered configurable provider connectors, dataset configurations, immutable Raw acquisition records, manifests, SHA-256 checksums and acquisition documentation.

The ONS MM23 and QNA files were semantically inspected to confirm the five approved series. Both original files were persisted without transformation. Their file sizes, manifest status and SHA-256 hashes were independently verified.

The user approved the formal closure of Phase 2 on 5 November 2026. Closure does not constitute formal financial data quality approval or approval for model training. Phase 3 remains not started and requires separate approval.

---

## 2. Scope Delivered

### Group A — Equities

The acquired instruments were:

| Instrument | Symbol | Role | Records |
|---|---|---|---:|
| National Grid | `NG.L` | Pilot / target asset | 7,890 |
| SSE plc | `SSE.L` | Sector peer | 9,060 |
| Severn Trent | `SVT.L` | Sector peer | 9,455 |
| FTSE 100 | `^FTSE` | Market benchmark | 11,004 |
| **Total** | | | **37,409** |

Acquisition identifiers:

- NG.L: `20261103T000455Z_8b505769`
- SSE.L: `20261103T002507Z_de101edb`
- SVT.L: `20261103T002515Z_fdac38df`
- ^FTSE: `20261103T002524Z_9c7eb120`

The Group A verification evidence records checks of CSV and Parquet existence, manifest file sizes and hashes, content consistency after in-memory normalisation, record counts, columns and date ranges.

### Group B — UK Interest Rates

| Dataset | Source series / maturity | Acquisition evidence |
|---|---|---|
| `UK_BANK_RATE` | BoE IADB `IUDBEDR` | 13,104 observations, 1975-01-02 to 2026-11-02 |
| `UK_SONIA` | BoE IADB `IUDSOIA` | 7,496 observations, 1997-03-03 to 2026-10-30 |
| `UK_GILT_NOMINAL_2Y` | BoE nominal yield curve | Original archive acquired |
| `UK_GILT_NOMINAL_10Y` | BoE nominal yield curve | Original archive acquired |

SONIA acquisition:
- ID: `20261103T224853Z_fc90361c`
- SHA-256: `20ec43b3bdf2cd9b42f064d444e4ba902169f6690b42ca80b8d8a75673d6d6ce`
- File size: 148,599 bytes.

Bank Rate acquisition:
- ID: `20261103T225333Z_db83b1b8`
- File size: 231,447 bytes.
- Preliminary inspection recorded zero duplicate dates, zero missing values, numeric values and chronological ordering.

Gilt archive acquisition:
- ID: `20261105T125522Z_eec59b41`
- Original ZIP size: 39,275,836 bytes.
- SHA-256: `3b0c30fd38b9148731d66f7c2b1f9f57a84890b0cf021e4bd1a2c803b868211a`
- Eight Excel workbooks were validated inside the archive.
- The original ZIP and manifest were persisted without extraction or transformation.

The 2Y and 10Y series are to be extracted from the original source during a later processing stage. The derived 10Y-minus-2Y yield curve slope is not part of Raw acquisition.

### Group C — UK Inflation and Macroeconomic Data

The approved logical datasets and ONS codes were:

| Dataset ID | ONS code | Description | Frequency |
|---|---|---|---|
| `UK_CPI` | `D7G7` | CPI Annual Rate — All Items | Monthly |
| `UK_CORE_CPI` | `DKO8` | CPI 12-month rate excluding energy, food, alcoholic beverages and tobacco | Monthly |
| `UK_CPIH` | `L55O` | CPIH Annual Rate — All Items | Monthly |
| `UK_REAL_GDP` | `ABMI` | GDP — Chained Volume Measures, Seasonally Adjusted | Quarterly |
| `UK_GDP_GROWTH` | `IHYQ` | GDP Quarter-on-Quarter Growth, CVM SA | Quarterly |

The series codes were located in the `CDID` row of their respective CSV files. Series titles, units, observation counts and date labels were inspected. Semantic validation was approved under D138.

**MM23 — Inflation**
- Acquisition ID: `20261105T132954Z_b4ce351c`
- File: `original_data.csv`
- Size: 23,228,735 bytes
- SHA-256: `ed5b20bea47cda76f38519c17d4c48f7d2b003aad5b3c69aa8f4d4f805f6ebc1`
- Logical datasets: `UK_CPI`, `UK_CORE_CPI`, `UK_CPIH`

**QNA — GDP**
- Acquisition ID: `20261105T132956Z_60b29116`
- File: `original_data.csv`
- Size: 2,246,438 bytes
- SHA-256: `8dfccc4c35c0ede47b77b9ad3783db82223da44823d93c6eabc0f33641f79583`
- Logical datasets: `UK_REAL_GDP`, `UK_GDP_GROWTH`

Both original CSV files were persisted without transformation. Their manifests identify the provider, source dataset, source page and endpoint, retrieval timestamp, configuration hash, logical dataset IDs, file size and SHA-256 checksum. Independent checks confirmed that the physical file sizes and hashes match the manifests.

---

## 3. Architecture and Implementation

The implemented acquisition approach is modular and provider-independent.

Delivered capabilities include:
- external YAML configurations;
- Pydantic configuration validation;
- independent provider connectors;
- separation between acquisition and downstream processing;
- immutable Raw acquisition directories;
- unique acquisition identifiers;
- acquisition manifests;
- configuration and file SHA-256 hashes;
- atomic persistence patterns;
- structured acquisition metadata;
- provider-specific error handling and retry principles.

The BoE IADB connector was generalised to support multiple series while retaining the Bank Rate compatibility interface. The ONS connector uses ONS-specific models and logic; the BoE connector was not modified to accommodate ONS.

### Principal implementation files

- `scripts/acquire_market_data.py`
- `scripts/verify_acquisition_integrity.py`
- `scripts/acquire_boe_yield_curves.py`
- `scripts/acquire_ons_data.py`
- `configs/assets/`
- `configs/datasets/uk_macro/`
- `tests/acquisition/`

### Recorded test evidence

- Full test suite after the BoE yield-curve work: 141 passed.
- ONS targeted test suite: 26 passed.
- Full test suite after ONS implementation: 167 passed.

These results are the execution outputs reported during the project work. They are not a claim that tests were rerun while preparing this report.

---

## 4. Version-Control Evidence

Recorded commits:

- `b141056 feat: implement multi-asset equity data acquisition`
- `90ba4c6 feat: add BoE yield curve and ONS macro data acquisition`

The latter commit includes the BoE yield-curve acquisition implementation, ONS configurations, ONS connector and associated tests.

The Raw market and macroeconomic files are excluded from Git and remain in local Raw storage. The repository was reported clean and synchronised with `origin/Main` after the implementation commit was pushed. A fresh status check should be performed after applying this report and the associated documentation updates.

---

## 5. Data Governance and Known Limitations

### Licensing

- Yahoo Finance is accessed through an unofficial interface. No redistribution or commercial-use rights are assumed.
- Bank of England reuse terms require dataset-level assessment; no blanket commercial permission is assumed.
- ONS licensing, attribution and commercial-use permissions remain subject to dataset-level review.
- Data accessibility does not itself establish permission for model training, redistribution or commercial use.

### Point-in-time and revisions

- Current ONS CSV files may include revised historical observations.
- The current file's release date is not the historical publication timestamp for every observation.
- Historical point-in-time vintages and observation-level release availability remain unresolved.
- Macroeconomic values must not be used before they were publicly available.

### Market data and temporal alignment

- Acquisition record counts do not prove complete trading-session coverage.
- GBP configuration for LSE instruments requires independent verification.
- Corporate-action and adjustment conventions have not been formally assessed.
- Cross-provider calendars, time zones, publication lags and as-of joins have not been assessed.
- Raw file integrity must not be confused with financial data quality.

### Other constraints

- The yield-curve concurrency test used two threads in one process; independent-process concurrency remains unverified.
- FRED/ALFRED data must not be used to train project models without written authorisation expressly resolving the relevant restriction.
- Potential source families outside Groups A–C are not represented as acquired by this report.

---

## 6. Phase 2 Exit Review

| Exit requirement | Evidence / status |
|---|---|
| Approved acquisition workstreams addressed | Groups A, B and C completed |
| Acquisitions recorded | Acquisition identifiers and manifests recorded for the acquired datasets |
| Technical integrity checks | Completed as documented in the group records |
| Provenance and licensing limitations | Recorded |
| Acquisition documentation | Group reports and final Phase 2 documentation prepared |
| Outstanding risks | Recorded in the progress register and Decision Log |
| Explicit closure approval | Approved by the user under D139 |

**Phase 2 result: COMPLETED — CLOSURE APPROVED.**

---

## 7. Handover Boundary

Phase 2 delivers acquired and traceable Raw source data. It does not deliver a modelling-ready dataset.

The following remain outside Phase 2:
- formal data quality assessment;
- missing-data and market-calendar assessment;
- corporate-action validation;
- unit, currency and frequency standardisation;
- temporal alignment and point-in-time joins;
- Raw-to-Interim or Interim-to-Processed transformation;
- feature engineering and target construction;
- forecasting, strategy development and backtesting.

**Phase 3 — Data Quality Assessment & Temporal Alignment is NOT STARTED.** It requires separate explicit user approval before any implementation begins.
