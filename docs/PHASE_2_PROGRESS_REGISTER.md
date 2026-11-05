# Phase 2 — Multi-Asset Data Acquisition
## Final Progress Register

**Project:** AI Quantitative Trading & Strategy Optimisation System
**Status:** **COMPLETED — CLOSURE APPROVED**
**Last updated:** 5 November 2026
**Closure decision:** D139
**Related decision:** D138 — ONS MM23 and QNA Semantic Validation

---

## 1. Phase Objective

Implement the approved multi-asset acquisition architecture and acquire the initial historical datasets selected for the project.

Phase 2 covered:
- acquisition architecture and provider connectors;
- dataset and asset configuration;
- historical data acquisition;
- immutable Raw persistence;
- acquisition metadata, manifests and checksums;
- technical acquisition and file-integrity verification;
- documentation of source, licensing and temporal limitations.

Phase 2 did **not** include formal financial data quality approval, temporal alignment, feature engineering, target construction or model development.

---

## 2. Overall Project Phase Status

| Phase | Description | Status |
|---|---|---|
| 0 | Project Definition & Technical Planning | Approved |
| 1 | Financial and Macroeconomic Data Sources Investigation | Approved |
| 2 | Multi-Asset Data Acquisition | **Completed — Closure Approved** |
| 3 | Data Quality Assessment & Temporal Alignment | Not Started |
| 4–16 | Subsequent research and implementation phases | Not Started |

Phase 3 must not begin until the user explicitly approves it.

---

## 3. Phase 2 Workstream Status

| Workstream | Description | Status |
|---|---|---|
| 2.1 | Data source and variable consolidation | Completed |
| 2.2.7 | Acquisition architecture design and approval | Completed |
| P0 | Initial National Grid historical acquisition | Completed |
| Group A | Equities acquisition and technical integrity verification | Completed |
| Group B | UK interest rates acquisition | Completed |
| Group C | UK inflation and macroeconomic data acquisition | Completed |
| Phase 2 closure | Consolidated evidence, documentation and approval | Completed — D139 |

**Scope note:** This register records the completion of the approved acquisition workstreams listed above. It does not imply that every potential source family identified during the wider source investigation has been acquired. Energy, foreign exchange, credit and company-fundamental datasets are not represented as acquired by this register.

---

## 4. Acquisition Architecture

The approved architecture is provider-independent and modular, using independent provider connectors and external configuration.

Key capabilities implemented across the acquisition workstreams include:
- YAML configuration and Pydantic validation;
- provider-specific acquisition adapters;
- separation of acquisition from downstream processing;
- historical acquisition support;
- immutable Raw acquisition directories;
- unique acquisition identifiers;
- manifests and SHA-256 checksums;
- atomic persistence patterns;
- configuration hashes;
- structured acquisition status and metadata;
- provider-specific error handling and retry principles;
- auditability and data lineage.

The BoE IADB connector was generalised for multiple series while retaining the existing Bank Rate compatibility interface. A separate ONS-specific connector was implemented; the BoE connector was not modified to accommodate ONS.

---

## 5. Group A — Equities

### 5.1 Approved instruments

| Instrument | Provider symbol | Role |
|---|---|---|
| National Grid | `NG.L` | Pilot / target asset |
| SSE plc | `SSE.L` | Sector peer |
| Severn Trent | `SVT.L` | Sector peer |
| FTSE 100 | `^FTSE` | Market benchmark |

### 5.2 Acquisition evidence

| Asset | Acquisition ID | Records | First observation | Last observation |
|---|---|---:|---|---|
| NG.L | `20261103T000455Z_8b505769` | 7,890 | 1995-12-11 | 2026-11-02 |
| SSE.L | `20261103T002507Z_de101edb` | 9,060 | 1991-06-17 | 2026-11-02 |
| SVT.L | `20261103T002515Z_fdac38df` | 9,455 | 1989-12-11 | 2026-11-02 |
| ^FTSE | `20261103T002524Z_9c7eb120` | 11,004 | 1984-01-03 | 2026-11-02 |
| **Total** | | **37,409** | | |

The NG.L acquisition was completed as the initial pilot. Group A subsequently added SSE.L, SVT.L and the FTSE 100 benchmark.

### 5.3 Verification and artefacts

- CSV and Parquet files were acquired.
- File sizes and SHA-256 checksums were checked against manifests.
- CSV and Parquet contents were compared after in-memory normalisation.
- Record counts, date ranges and columns were checked against manifest metadata.

**Verification result:** Passed, according to the acquisition verification evidence recorded for Group A.

Relevant files:
- `configs/assets/ng_l.yaml`
- `configs/assets/sse_l.yaml`
- `configs/assets/svt_l.yaml`
- `configs/assets/ftse_100.yaml`
- `scripts/acquire_market_data.py`
- `scripts/verify_acquisition_integrity.py`
- `reports/acquisition/NG_L_acquisition_report.md`
- `reports/acquisition/EQUITIES_GROUP_A_ACQUISITION_REPORT.md`

**Limitation:** These checks establish file integrity and acquisition consistency. They do not establish financial data quality, corporate-action correctness, complete trading-session coverage or suitability for temporal alignment.

---

## 6. Group B — UK Interest Rates

### 6.1 Approved datasets

| Logical dataset | Provider/source | Series or instrument | Acquisition result |
|---|---|---|---|
| `UK_BANK_RATE` | Bank of England IADB | `IUDBEDR` | Acquired |
| `UK_SONIA` | Bank of England IADB | `IUDSOIA` | Acquired |
| `UK_GILT_NOMINAL_2Y` | Bank of England yield curve archive | 2-year nominal maturity | Source archive acquired |
| `UK_GILT_NOMINAL_10Y` | Bank of England yield curve archive | 10-year nominal maturity | Source archive acquired |

The 2-year and 10-year series are to be derived from the original yield-curve source during a later processing stage. The original archive was not transformed during acquisition.

### 6.2 Bank Rate

- Acquisition ID: `20261103T225333Z_db83b1b8`
- Observations: 13,104
- Date range: 1975-01-02 to 2026-11-02
- Preliminary checks recorded: zero duplicate dates, zero missing values, numeric values and chronological ordering.
- Raw CSV size: 231,447 bytes.
- Manifest status: success.
- No watermark was updated.

### 6.3 SONIA

- Acquisition ID: `20261103T224853Z_fc90361c`
- Observations: 7,496
- Date range: 1997-03-03 to 2026-10-30
- Raw CSV size: 148,599 bytes.
- SHA-256: `20ec43b3bdf2cd9b42f064d444e4ba902169f6690b42ca80b8d8a75673d6d6ce`
- Manifest status: success.
- No watermark was updated.

### 6.4 Gilt nominal yield curve archive

- Acquisition ID: `20261105T125522Z_eec59b41`
- Raw path: `data/raw/macro/bank_of_england/yield_curve_archive/acquisition_20261105T125522Z_eec59b41`
- Original ZIP size: 39,275,836 bytes.
- SHA-256: `3b0c30fd38b9148731d66f7c2b1f9f57a84890b0cf021e4bd1a2c803b868211a`
- Eight Excel workbooks were validated inside the ZIP archive.
- The original ZIP and manifest were persisted.
- No extraction or transformation was performed during acquisition.
- No watermark was updated.

### 6.5 Implementation and tests

- Generic BoE IADB configuration and acquisition support were implemented.
- Bank Rate compatibility interfaces were retained.
- The yield-curve archive acquisition script and concurrency-safe directory commit logic were implemented.
- The full test suite after the yield-curve work reported 141 passing tests.
- The ONS work subsequently extended the full suite to 167 passing tests.

Relevant files include:
- `scripts/acquire_boe_yield_curves.py`
- BoE IADB acquisition connector and associated tests
- `tests/acquisition/test_boe_yield_curves.py`

**Limitation:** The yield-curve concurrency test used two threads in one process; it did not establish independent-process concurrency behaviour.

---

## 7. Group C — UK Inflation and Macroeconomic Data

### 7.1 Approved ONS datasets

| Logical dataset ID | ONS code | Description | Frequency |
|---|---|---|---|
| `UK_CPI` | `D7G7` | CPI Annual Rate — All Items | Monthly |
| `UK_CORE_CPI` | `DKO8` | CPI 12-month rate excluding energy, food, alcoholic beverages and tobacco | Monthly |
| `UK_CPIH` | `L55O` | CPIH Annual Rate — All Items | Monthly |
| `UK_REAL_GDP` | `ABMI` | GDP — Chained Volume Measures, Seasonally Adjusted | Quarterly |
| `UK_GDP_GROWTH` | `IHYQ` | GDP Quarter-on-Quarter Growth, CVM SA | Quarterly |

### 7.2 Semantic validation

The five series codes were located in the ONS CSV `CDID` row. Their titles, units, observation counts and date labels were inspected.

Observed series counts and ranges at acquisition inspection:

| Series | Observations | First observation | Last observation |
|---|---:|---|---|
| D7G7 | 641 | 1989 | 2026 SEP |
| DKO8 | 641 | 1989 | 2026 SEP |
| L55O | 641 | 1989 | 2026 SEP |
| ABMI | 364 | 1948 | 2026 Q2 |
| IHYQ | 285 | 1955 Q2 | 2026 Q2 |

Semantic validation was formally approved under **D138 — ONS MM23 and QNA Semantic Validation**.

### 7.3 Raw acquisitions

**Inflation — MM23**
- Acquisition ID: `20261105T132954Z_b4ce351c`
- Path: `data/raw/macro/ons/inflation/acquisition_20261105T132954Z_b4ce351c`
- File: `original_data.csv`
- Size: 23,228,735 bytes
- SHA-256: `ed5b20bea47cda76f38519c17d4c48f7d2b003aad5b3c69aa8f4d4f805f6ebc1`
- Dataset IDs: `UK_CPI`, `UK_CORE_CPI`, `UK_CPIH`

**GDP — QNA**
- Acquisition ID: `20261105T132956Z_60b29116`
- Path: `data/raw/macro/ons/gdp/acquisition_20261105T132956Z_60b29116`
- File: `original_data.csv`
- Size: 2,246,438 bytes
- SHA-256: `8dfccc4c35c0ede47b77b9ad3783db82223da44823d93c6eabc0f33641f79583`
- Dataset IDs: `UK_REAL_GDP`, `UK_GDP_GROWTH`

Both manifests report successful acquisition, the expected dataset IDs, the source endpoint, retrieval timestamp, configuration SHA-256, file size and file SHA-256. Independent verification confirmed that the physical file sizes and SHA-256 hashes match the manifests.

### 7.4 Implementation and tests

Relevant files:
- `configs/datasets/uk_macro/inflation.yaml`
- `configs/datasets/uk_macro/gdp.yaml`
- `scripts/acquire_ons_data.py`
- `tests/acquisition/test_ons_acquisition.py`

The ONS connector uses ONS-specific Pydantic models and supports configuration validation, fetch-only operation and explicit persistence. The BoE connector was not modified to accommodate ONS.

- ONS targeted tests: 26 passed.
- Full test suite after ONS implementation: 167 passed.

**Temporal limitation:** The release date in the current ONS CSV is metadata for the current release; it must not be interpreted as the historical availability timestamp for every observation. Historical revisions and point-in-time vintages remain unresolved.

---

## 8. Repository and Version-Control Evidence

Recorded implementation commits:
- `b141056 feat: implement multi-asset equity data acquisition`
- `90ba4c6 feat: add BoE yield curve and ONS macro data acquisition`

The second commit includes the ONS configurations, ONS connector, yield-curve acquisition script and associated tests.

Raw market and macroeconomic data are excluded from Git and remain in local Raw storage.

The repository status was reported clean after the implementation commit was pushed. A final status check should be performed when applying this documentation update.

---

## 9. Licensing, Governance and Outstanding Risks

| Risk / limitation | Phase 2 assessment | Required treatment |
|---|---|---|
| Yahoo Finance licensing | No commercial or redistribution rights assumed; unofficial interface | Review provider terms and permitted use before any commercial use |
| Bank of England licensing | Terms require dataset-level assessment; no blanket commercial clearance assumed | Verify relevant dataset terms before redistribution or commercial use |
| ONS licensing | Dataset-level licensing and commercial permissions remain subject to review | Verify licence and attribution obligations before commercial use |
| Point-in-time macro data | Current releases may include historical revisions | Investigate vintage and historical release availability before point-in-time modelling |
| Macro publication timing | Current file release date is not the release timestamp of every historical observation | Use observation-level/as-of publication metadata where available; do not backdate availability |
| Equity currency metadata | GBP is configured for LSE instruments; independent verification remains necessary | Verify in data quality assessment |
| Corporate actions and adjustments | Correctness has not been assessed | Assess adjustment conventions and corporate actions in Phase 3 |
| Market calendars and completeness | Acquisition record counts do not prove complete session coverage | Assess expected sessions, gaps and duplicates in Phase 3 |
| Cross-provider temporal alignment | Not assessed in Phase 2 | Assess calendars, time zones, release lags and as-of joins in Phase 3 |
| Yield-curve concurrency | Test evidence covers two threads in one process | Treat independent-process concurrency as unverified |
| FRED/ALFRED | Training prohibited without written authorisation expressly resolving the restriction | Maintain the restriction; revisit only during the later commercialisation review |

No risk listed above is silently treated as resolved by Phase 2 closure.

---

## 10. Phase 2 Exit Criteria Review

| Exit criterion | Result |
|---|---|
| Approved acquisition workstreams addressed | Passed for Groups A, B and C |
| Required acquisitions recorded with identifiers and manifests | Passed for the acquired datasets |
| Technical integrity checks completed | Passed as documented in the group records |
| Provenance and licensing limitations documented | Passed |
| Acquisition reports and project registers prepared | This final register and consolidated report complete the documentation set |
| Outstanding risks recorded | Passed |
| Explicit user approval for closure | Approved — D139 |

**Important:** Passing Phase 2 exit criteria does not approve the data for modelling or establish financial data quality.

---

## 11. Final Phase 2 Status and Gate

**Phase 2 — Multi-Asset Data Acquisition: COMPLETED — CLOSURE APPROVED.**

Closure was explicitly approved by the user on 5 November 2026 and recorded as D139.

**Phase 3 — Data Quality Assessment & Temporal Alignment: NOT STARTED.**

Phase 3 requires separate explicit approval. No Phase 3 implementation, transformation pipeline, feature engineering or modelling work is authorised by this Phase 2 closure.
