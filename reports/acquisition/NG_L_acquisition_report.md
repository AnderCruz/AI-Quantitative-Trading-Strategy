# NG.L Historical Market Data Acquisition Report

## 1. Acquisition Overview

| Attribute              | Value                                                                            |
| ---------------------- | -------------------------------------------------------------------------------- |
| Asset                  | National Grid                                                                    |
| Ticker                 | NG.L                                                                             |
| Provider               | Yahoo Finance                                                                    |
| Acquisition library    | yfinance                                                                         |
| Acquisition ID         | 20261103T000455Z_8b505769                                                        |
| Frequency              | Daily                                                                            |
| Requested period       | Maximum available history                                                        |
| Currency               | GBP (configured assumption; not independently verified by the provider response) |
| Retrieval date         | 2 November 2026 (local time)                                                     |
| First observation      | 11 December 1995                                                                 |
| Last observation       | 2 November 2026                                                                  |
| Number of observations | 7,890                                                                            |
| Acquisition status     | Success                                                                          |

## 2. Acquisition Configuration

The following parameters were approved and used:

| Parameter     | Value   |
| ------------- | ------- |
| `period`      | `max`   |
| `interval`    | `1d`    |
| `auto_adjust` | `False` |
| `actions`     | `True`  |
| `repair`      | `False` |
| `keepna`      | `True`  |
| `prepost`     | `False` |
| `rounding`    | `False` |
| `progress`    | `False` |
| `threads`     | `False` |

## 3. Acquired Data

The acquisition returned eight columns:

* Open
* High
* Low
* Close
* Adj Close
* Volume
* Dividends
* Stock Splits

Original OHLC prices, adjusted closing prices and corporate action fields were preserved separately.

No formal data cleaning or transformation was performed.

## 4. Storage Outputs

The acquisition generated the following files:

| File          | Format  |                 Size |
| ------------- | ------- | -------------------: |
| NG.L.csv      | CSV     |        862,847 bytes |
| NG.L.parquet  | Parquet |        321,393 bytes |
| manifest.json | JSON    | Acquisition metadata |

Storage location:

`data/raw/market/yahoo_finance/NG.L/acquisition_20261103T000455Z_8b505769/`

## 5. Technical Integrity Verification

The following checks were performed after acquisition:

| Check                               | Result     |
| ----------------------------------- | ---------- |
| Manifest successfully loaded        | Passed     |
| CSV file exists and is readable     | Passed     |
| Parquet file exists and is readable | Passed     |
| CSV SHA-256 checksum                | Valid      |
| Parquet SHA-256 checksum            | Valid      |
| CSV record count                    | 7,890      |
| Parquet record count                | 7,890      |
| Manifest record count               | 7,890      |
| CSV and Parquet column names        | Consistent |
| First observation date              | Consistent |
| Last observation date               | Consistent |

These checks establish basic technical integrity. They do not establish financial data quality or complete value-by-value equivalence between the two formats.

## 6. Warnings and Limitations

### 6.1 Library compatibility warnings

During execution, yfinance emitted Pandas4Warning messages concerning deprecated `inplace` arguments in internal operations.

The acquisition completed successfully. These warnings were not captured in the manifest, which reported an empty warnings list.

The acquisition implementation should be improved to record relevant runtime warnings in future runs.

### 6.2 Python version metadata

The manifest recorded `Python 3.12+` rather than the exact interpreter version.

Future acquisitions should record the exact Python version.

### 6.3 Data provenance

The files preserve the DataFrame returned by yfinance. They do not constitute a preservation of the original Yahoo Finance HTTP response.

### 6.4 Historical coverage

The provider returned observations from 11 December 1995 to 2 November 2026.

This represents the history returned for this request, not a guarantee that the provider contains the complete official trading history.

### 6.5 Licensing

The dataset is restricted to exploratory and research use pending a separate licensing assessment.

Redistribution and commercial use must not be assumed to be permitted.

## 7. Phase Boundary

This acquisition belongs to Phase 2 — Multi-Asset Data Acquisition.

The following activities have not yet been performed:

* Formal missing-value assessment.
* Duplicate and temporal continuity assessment.
* OHLC consistency checks.
* Corporate action validation.
* Outlier analysis.
* Trading calendar validation.
* Cross-source reconciliation.
* Formal data quality approval.

These activities belong to Phase 3 — Data Quality Assessment & Temporal Alignment.

## 8. Acquisition Decision

**Decision: ACCEPTED FOR PHASE 2 STORAGE, SUBJECT TO PHASE 3 VALIDATION.**

The acquisition passed the performed technical integrity checks.

The dataset must not yet be considered validated for modelling or forecasting.

## 9. Current Status

* NG.L historical acquisition: Completed.
* CSV and Parquet integrity: Passed.
* Acquisition manifest: Created.
* Formal data quality validation: Pending.
* Licensing assessment: Pending.
* Phase 2 overall: In progress.
