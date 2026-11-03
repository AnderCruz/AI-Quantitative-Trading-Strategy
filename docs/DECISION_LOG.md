# Decision Log
## AI Quantitative Trading & Strategy Optimisation System

**Document status:** Active
**Project phase:** Phase 2 — Multi-Asset Data Acquisition
**Last updated:** 3 November 2026

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
