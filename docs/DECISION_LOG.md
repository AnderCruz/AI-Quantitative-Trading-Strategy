# Decision Log
## AI Quantitative Trading & Strategy Optimisation System

**Document status:** Active
**Project phase:** Phase 2 — Multi-Asset Data Acquisition
**Last updated:** 5 November 2026

---

## 1. Purpose

This document records confirmed architectural, technical, data governance and project-scope decisions.

It is intended to provide an auditable record of decisions that influence the system's design and implementation.

Historical decisions D01–D129 were approved during previous project discussions. Their complete individual descriptions are not reconstructed here because the full original decision records are not available in this document. The approved decisions remain part of the project's decision history.

---

## 2. Project Scope and Governance

### 2.1 Multi-Asset Architecture

**Decision:** The system must support multiple assets and providers from its initial architecture.

**Rationale:**
- Avoid an architecture tied exclusively to National Grid.
- Support future asset classes and instruments.
- Separate asset configuration from acquisition implementation.
- Allow independent provider connectors.

**Implementation principle:** National Grid (`NG.L`) is the initial pilot asset, not a hard-coded system dependency.

### 2.2 Initial Trading Scope

**Decision:** The initial research scope is daily-frequency, long-only swing trading, with GBP as the base currency and hypothetical starting capital of £1,000.

**Restrictions:**
- Research, backtesting and paper trading only.
- No live trading or broker integration.
- No leverage, derivatives or short selling without explicit approval.
- Paper trading is mandatory before any discussion of live trading.

### 2.3 FRED/ALFRED Usage Restriction

**Decision:** FRED/ALFRED data must not be used to train project models without written authorisation that expressly resolves the relevant restriction.

**Future review:** Reassess this decision at the end of the project, when the commercialisation question is evaluated.

---

## 3. Data Sources and Licensing

### 3.1 Yahoo Finance

**Decision:** Yahoo Finance is conditionally accepted for exploratory research and historical market-data acquisition.

**Restrictions and caveats:**
- It is accessed through an unofficial interface.
- No redistribution or commercial-use rights are assumed.
- Licensing and terms must be reviewed before any commercial use.
- Provider metadata and configured assumptions must not be represented as independently verified facts.

### 3.2 Source-Level Licensing

**Decision:** Licensing and permitted usage must be assessed at dataset/provider level.

The presence of an accessible API or downloadable dataset does not automatically establish permission for commercial use, redistribution or model training.

---

## 4. Data Acquisition Architecture

The following architectural decisions were approved for Phase 2.2.7.

### 4.1 Provider-Independent Design

- Use modular, provider-independent acquisition components.
- Implement independent provider connectors using an adapter pattern.
- Keep acquisition pipelines separate from downstream processing pipelines.
- Avoid provider-specific assumptions in shared acquisition logic.

### 4.2 Configuration Management

- Store asset and acquisition settings in external YAML configuration files.
- Validate configuration using Pydantic.
- Support global, asset, provider, dataset and environment-level configuration.
- Validate configuration before acquisition starts.
- Record the configuration version or hash in acquisition metadata.
- Store credentials in environment variables; never commit secrets.

### 4.3 Acquisition Modes

The architecture must support:
- Full historical acquisition.
- Fixed date-range acquisition.
- Incremental acquisition.

Incremental acquisition must use independent dataset watermarks. A watermark advances only after successful validation and commit.

### 4.4 Raw Data Immutability

**Decision:** Raw acquisitions are immutable.

- Never overwrite an existing Raw acquisition.
- Store each acquisition as a separately identifiable version.
- Use controlled reruns with an `acquisition_id`.
- Store files in temporary locations before validation and commit.
- Validate files and calculate SHA-256 checksums before atomic commit.
- Preserve revised source data as new versions.

### 4.5 Reliability and Failure Handling

- Classify errors as transient, permanent or investigation-required.
- Use configurable retries, exponential backoff and jitter.
- Respect provider rate limits and `Retry-After` instructions.
- Support provider-specific circuit breakers.
- Isolate provider failures so one provider does not automatically stop unrelated acquisitions.
- Use normalised acquisition statuses, including success, warnings, valid empty, incomplete and failed/rejected.

### 4.6 Data Integrity and Idempotency

- Use dataset-specific logical keys and idempotency rules.
- Maintain temporal continuity checks appropriate to each dataset.
- Reconcile acquisitions deterministically.
- Keep historical backfills separately traceable.
- Record file sizes, checksums, record counts and acquisition metadata.

### 4.7 Logging, Audit and Lineage

- Use structured JSON logs.
- Maintain a central acquisition audit trail.
- Preserve lineage from provider through Raw, Interim and Processed datasets to downstream research artefacts.
- Keep operational monitoring separate from formal data quality assessment.
- Use append-only audit records with configurable retention.

### 4.8 Infrastructure Scope

**Decision:** Start with local acquisition monitoring and logging.

The initial implementation will not introduce Airflow, Prefect, Dagster, cloud monitoring services or external observability platforms unless a demonstrated requirement justifies them.

---

## 5. Data Storage and Temporal Principles

### 5.1 Storage Layers

The project uses the following logical layers:

- `data/raw/` — immutable provider acquisitions.
- `data/interim/` — standardised and typed data with source metadata.
- `data/processed/` — consolidated datasets prepared for subsequent assessment.

**Important:** Processed does not mean approved for modelling.

### 5.2 Temporal and Point-in-Time Controls

- Preserve source timestamps and original time-zone semantics.
- Use UTC internally while retaining relevant local-time information.
- Respect Europe/London GMT/BST transitions.
- Do not automatically forward-fill missing observations.
- Use publication timestamps and data vintages for macroeconomic point-in-time joins.
- Do not use macroeconomic information before it was publicly available.
- Do not use same-bar look-ahead execution: after-close signals execute no earlier than the next eligible trading session.

### 5.3 Dataset Metadata

Where applicable, retain:
- Provider and dataset identifier.
- Acquisition timestamp.
- Observation date.
- Publication date.
- Frequency.
- Currency and unit.
- Licence information.
- Data version.
- Adjustment convention.

---

## 6. Group A — Equities Acquisition Record

**Status:** Completed — acquisition and technical integrity verification.

The approved Group A instruments are:

| Instrument | Provider symbol | Role |
|---|---|---|
| National Grid | NG.L | Pilot / target asset |
| SSE plc | SSE.L | Sector peer |
| Severn Trent | SVT.L | Sector peer |
| FTSE 100 | ^FTSE | Market benchmark |

The initial NG.L acquisition was completed previously. The subsequent Group A acquisition covered SSE.L, SVT.L and ^FTSE.

The technical integrity verification confirmed:
- CSV and Parquet files exist.
- File sizes and SHA-256 checksums match their manifests.
- CSV and Parquet contents match after in-memory normalisation.
- Record counts, date ranges and columns are consistent with the manifests.

This record documents acquisition execution. It does not constitute formal financial data quality approval.

---

## 7. Decision Governance

Any material change to:
- project scope;
- data-provider usage or licensing;
- acquisition architecture;
- temporal or point-in-time policy;
- modelling methodology;
- strategy constraints;
- risk limits;
- backtesting or execution assumptions;

must be discussed and explicitly approved before implementation.

New decisions should be added with a unique identifier, date, status, rationale, consequences and links to relevant implementation evidence.


## 5. Phase 2 Closure Decisions

**Project phase:** Phase 2 — Multi-Asset Data Acquisition
**Decision date:** 5 November 2026

---

## D138 — ONS MM23 and QNA Semantic Validation

**Status:** APPROVED
**Date:** 5 November 2026

**Decision:** Approve the semantic validation of the five selected ONS series and the use of the MM23 and QNA source files for their respective logical datasets.

**Approved mappings:**

| Logical dataset ID | ONS series code | Description | Frequency |
|---|---|---|---|
| `UK_CPI` | `D7G7` | CPI Annual Rate — All Items | Monthly |
| `UK_CORE_CPI` | `DKO8` | CPI 12-month rate excluding energy, food, alcoholic beverages and tobacco | Monthly |
| `UK_CPIH` | `L55O` | CPIH Annual Rate — All Items | Monthly |
| `UK_REAL_GDP` | `ABMI` | GDP — Chained Volume Measures, Seasonally Adjusted | Quarterly |
| `UK_GDP_GROWTH` | `IHYQ` | GDP Quarter-on-Quarter Growth, CVM SA | Quarterly |

**Approved acquisition design:**
- Use one original MM23 CSV acquisition for the three inflation datasets.
- Use one original QNA CSV acquisition for the two GDP datasets.
- Preserve the downloaded source files without transformation during acquisition.
- Retain acquisition manifests, configuration hashes, file sizes and SHA-256 checksums.
- Keep the limitations concerning historical revisions and point-in-time availability explicit.

**Evidence:**
- ONS MM23 and QNA CSV files were fetched and inspected.
- All five approved series codes were found in the `CDID` row.
- Series titles, units, observation counts and date labels were inspected.
- The ONS connector's targeted tests and the full test suite passed at the time of implementation.

**Consequences and limitations:**
- Semantic identification is accepted for acquisition purposes.
- This decision does not constitute formal data quality approval or approval for modelling.
- The current ONS CSV release date is not the historical publication timestamp for every observation.
- Historical revisions and point-in-time vintages remain unresolved and must be assessed in the appropriate subsequent phase.
- Licensing and commercial-use permissions remain subject to dataset-level review.

---

## D139 — Phase 2 Closure

**Status:** APPROVED
**Date:** 5 November 2026

**Decision:** Approve the formal closure of Phase 2 — Multi-Asset Data Acquisition, with outstanding risks and limitations retained in the project records.

**Closure scope:**
- Group A — Equities.
- Group B — UK Interest Rates.
- Group C — UK Inflation and Macroeconomic Data.

**Closure evidence:**
- Approved acquisition configurations and provider connectors were implemented.
- The selected acquisitions were executed and recorded with acquisition identifiers and manifests.
- Raw file integrity checks were completed for the acquired datasets where specified in the group records.
- Group C ONS semantic validation was approved under D138.
- Group C ONS Raw file size, manifest status and SHA-256 checks passed.
- The relevant implementation and tests were committed to the repository.

**Explicit exclusions:**
- Phase 2 closure does not approve the datasets for modelling.
- Formal financial data quality assessment and temporal alignment are not included.
- Feature engineering, target construction, forecasting, strategy research and backtesting are not included.
- Source families not acquired in Groups A–C are not represented as acquired or validated by this closure.

**Outstanding risks:**
- Provider and dataset licensing, including commercial use and redistribution.
- Yahoo Finance's unofficial access interface and unresolved usage rights.
- Dataset-specific Bank of England reuse terms.
- ONS historical revisions and point-in-time vintage availability.
- Currency and adjustment assumptions requiring independent verification.
- Market calendar completeness, missing observations and cross-provider temporal alignment.
- The distinction between file integrity and financial data quality.
- FRED/ALFRED training restriction: no model training without written authorisation expressly resolving the relevant restriction.

**Consequences:**
- Phase 2 is recorded as completed.
- Phase 3 — Data Quality Assessment & Temporal Alignment remains not started and requires its own explicit approval.
- No change is made to the project's long-only, research/backtesting/paper-trading-only restrictions.
