# Equities Group A — Historical Data Acquisition Report

**Project:** AI Quantitative Trading & Strategy Optimisation System
**Phase:** Phase 2 — Multi-Asset Data Acquisition
**Group:** Group A — Equities
**Status:** Acquisition and integrity verification completed
**Data provider:** Yahoo Finance via yfinance
**Frequency:** Daily (1d)
**Retrieval date:** 3 November 2026 (UTC)
**Last observation:** 2 November 2026

## 1. Executive Summary

Historical market data acquisition was completed for three additional instruments:

* SSE plc (`SSE.L`)
* Severn Trent plc (`SVT.L`)
* FTSE 100 Index (`^FTSE`)

The acquisition process produced 29,519 historical observations across the three instruments.

CSV and Parquet representations were generated for each instrument, accompanied by an acquisition manifest containing configuration metadata, software versions, file sizes, SHA-256 checksums and acquisition warnings.

All three acquisitions passed the implemented file-integrity, checksum, representation-consistency and manifest-consistency checks.

The existing National Grid (`NG.L`) acquisition was not repeated.

## 2. Acquisition Results

| Instrument       | Ticker | Type   |    Records | Observation Start | Observation End |
| ---------------- | ------ | ------ | ---------: | ----------------- | --------------- |
| SSE plc          | SSE.L  | Equity |      9,060 | 1991-06-17        | 2026-11-02      |
| Severn Trent plc | SVT.L  | Equity |      9,455 | 1989-12-11        | 2026-11-02      |
| FTSE 100 Index   | ^FTSE  | Index  |     11,004 | 1984-01-03        | 2026-11-02      |
| **Total**        |        |        | **29,519** |                   |                 |

## 3. Acquisition Identifiers

| Instrument | Acquisition ID              |
| ---------- | --------------------------- |
| SSE.L      | `20261103T002507Z_de101edb` |
| SVT.L      | `20261103T002515Z_fdac38df` |
| ^FTSE      | `20261103T002524Z_9c7eb120` |

## 4. Data Representation

Each acquisition contains:

* Original CSV representation.
* Parquet representation.
* JSON acquisition manifest.

### 4.1 Equity Instruments

SSE.L and SVT.L contain the following columns:

* Open
* High
* Low
* Close
* Adj Close
* Volume
* Dividends
* Stock Splits

### 4.2 FTSE 100 Index

The FTSE 100 acquisition contains:

* Open
* High
* Low
* Close
* Adj Close
* Volume

Dividend and stock split columns were not returned for the index. This is an expected instrument-specific difference and was recorded in the acquisition manifest.

## 5. Acquisition Configuration

The following parameters were used:

| Parameter          | Value          |
| ------------------ | -------------- |
| Provider           | Yahoo Finance  |
| Python library     | yfinance 1.7.0 |
| Frequency          | 1d             |
| Historical period  | max            |
| auto_adjust        | False          |
| repair             | False          |
| keepna             | True           |
| prepost            | False          |
| rounding           | False          |
| progress           | False          |
| threads            | False          |
| actions — equities | True           |
| actions — index    | False          |

The acquisition configurations are stored separately from the acquisition implementation under `configs/assets/`.

## 6. Software Environment

| Component | Version |
| --------- | ------- |
| Python    | 3.12.3  |
| yfinance  | 1.7.0   |
| pandas    | 3.1.0   |
| pyarrow   | 26.0.0  |
| pydantic  | 2.14.2  |
| PyYAML    | 6.0.3   |

## 7. Integrity Verification

The verification script `scripts/verify_acquisition_integrity.py` was executed successfully.

The following checks passed for all three instruments:

1. Acquisition directory existence.
2. Manifest existence and readability.
3. CSV and Parquet file existence.
4. File size consistency against manifest metadata.
5. SHA-256 checksum consistency.
6. CSV and Parquet record count consistency.
7. Column name and ordering consistency.
8. Datetime index consistency.
9. Data value consistency within the configured floating-point tolerances.
10. Observation start and end date consistency.
11. Manifest column metadata consistency.

**Final result: ALL INTEGRITY CHECKS PASSED.**

The comparison normalises datetime precision and column metadata in memory only. The original Raw files remain unchanged.

## 8. Warnings and Technical Observations

### 8.1 Pandas Deprecation Warnings

The acquisition process recorded Pandas4Warning messages relating to the use of the `inplace` argument in several DataFrame operations.

These warnings did not prevent successful acquisition or file verification.

They are recorded as technical maintenance items for a future implementation review.

### 8.2 Optional Index Columns

The FTSE 100 acquisition did not return `Dividends` or `Stock Splits`.

These fields are not required for the index configuration.

### 8.3 Currency Metadata

GBP is currently recorded as a configured currency assumption.

It has not been independently verified against provider-level instrument metadata.

### 8.4 Data Provider and Licensing

Yahoo Finance data is currently classified as suitable for research and exploratory use only.

Redistribution and commercial use remain subject to a separate licensing assessment.

The acquired data must not be interpreted as having unrestricted commercial-use rights.

## 9. Storage and Reproducibility

Acquisitions are stored independently by instrument:

* `data/raw/market/yahoo_finance/SSE.L/`
* `data/raw/market/yahoo_finance/SVT.L/`
* `data/raw/market/yahoo_finance/^FTSE/`

Each acquisition has its own immutable acquisition directory.

Raw market data is excluded from Git and must not be committed.

Acquisition manifests preserve the configuration hash, acquisition identifier, timestamps, software versions and file checksums.

## 10. Scope Boundary

This report covers historical acquisition and technical file-integrity verification only.

It does not represent:

* Formal financial data quality assessment.
* Corporate action validation.
* Price or volume accuracy validation.
* Trading calendar validation.
* Missing-value assessment.
* Cross-instrument temporal alignment.
* Point-in-time data validation.
* Feature engineering or modelling approval.

These activities belong to subsequent project work.

## 11. Group A Conclusion

Group A historical acquisition and technical integrity verification are complete.

All three instruments were successfully acquired, stored and verified.

The results support proceeding with the remaining approved Phase 2 acquisition groups, subject to the existing project architecture, source restrictions and licensing decisions.

**Group A status: COMPLETED — TECHNICAL INTEGRITY VERIFIED.**

**Phase 2 status: IN PROGRESS.**
