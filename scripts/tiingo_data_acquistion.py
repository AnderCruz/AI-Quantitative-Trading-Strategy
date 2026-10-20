"""Download, validate and consolidate daily OHLCV data from Tiingo.

Run from the project root with:
    python scripts/tiingo_data_acquistion.py

The script expects TIINGO_API_KEY to be available as an environment variable
or in the project-root .env file, loaded by src/config.py.
"""

# Import standard-library utilities for JSON, paths, timestamps and execution.
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Define the project root before importing project modules.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Ensure the project root is importable when this file is run directly.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import third-party libraries for data processing and HTTP requests.
import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import the centralised credential configuration.
from src.config import get_tiingo_api_key


# Define the output directories.
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "tiingo"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "reports" / "data_quality"

# Define the candidate stocks and requested historical period.
TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA"]
START_DATE = "2015-01-01"
END_DATE = "2026-01-01"  # Exclusive end date.

# Define the Tiingo daily-price endpoint and request timeout.
BASE_URL = "https://api.tiingo.com/tiingo/daily"
REQUEST_TIMEOUT_SECONDS = 30

# Define the required raw and adjusted market-data fields.
RAW_OHLCV = ["open", "high", "low", "close", "volume"]
RAW_PRICE_FIELDS = ["open", "high", "low", "close"]
ADJUSTED_OHLCV = ["adjOpen", "adjHigh", "adjLow", "adjClose", "adjVolume"]
ADJUSTED_PRICE_FIELDS = ["adjOpen", "adjHigh", "adjLow", "adjClose"]
REQUIRED_FIELDS = RAW_OHLCV + ADJUSTED_OHLCV

# Corporate-action fields are useful but are treated as warnings if absent.
CORPORATE_ACTION_FIELDS = ["divCash", "splitFactor"]


def create_output_directories() -> None:
    """Create the directories required by this workflow."""
    for directory in (RAW_DATA_DIR, PROCESSED_DATA_DIR, REPORT_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def create_http_session() -> requests.Session:
    """Create an HTTP session with conservative retries for transient errors."""
    session = requests.Session()
    retry_policy = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_policy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def write_json_atomically(path: Path, payload: Any) -> None:
    """Write JSON to a temporary file before replacing the target file."""
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False, default=str)
    temporary_path.replace(path)


def download_ticker_data(
    session: requests.Session,
    ticker: str,
    api_key: str,
) -> tuple[pd.DataFrame, Path, int]:
    """Download one ticker's daily observations and preserve the raw response."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {api_key}",
    }
    params = {"startDate": START_DATE, "endDate": END_DATE}
    url = f"{BASE_URL}/{ticker}/prices"

    # Send the request without logging credentials or request headers.
    response = session.get(
        url,
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    # Parse and validate the basic response structure.
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError(f"{ticker}: API response was not a list.")
    if not payload:
        raise ValueError(f"{ticker}: API returned no observations.")
    if not all(isinstance(row, dict) for row in payload):
        raise ValueError(f"{ticker}: API response contains an invalid row.")

    # Convert the response into a chronological DataFrame.
    data = pd.DataFrame(payload)

    # Ensure that the required date field exists.
    if "date" not in data.columns:
        raise ValueError(f"{ticker}: API response has no date field.")

    # Parse dates before writing the raw response to disk.
    # Invalid or missing dates must not overwrite existing raw data.
    data["date"] = pd.to_datetime(data["date"], utc=True, errors="raise")

    # Sort observations chronologically and add the ticker identifier.
    data = data.sort_values("date", kind="stable").reset_index(drop=True)
    data["ticker"] = ticker

    # Preserve the original provider response after basic validation.
    raw_path = RAW_DATA_DIR / f"{ticker.lower()}_daily_raw.json"
    write_json_atomically(raw_path, payload)

    return data, raw_path, response.status_code


def _numeric_frame(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Convert selected columns to numeric values, coercing invalid values to NaN."""
    return data[columns].apply(pd.to_numeric, errors="coerce")


def _count_invalid_numeric_rows(values: pd.DataFrame) -> int:
    """Count rows containing missing, non-numeric or non-finite values."""
    array = values.to_numpy(dtype=float, na_value=np.nan)
    return int((~np.isfinite(array)).any(axis=1).sum())


def _count_invalid_ohlc_rows(values: pd.DataFrame) -> int:
    """Count rows where OHLC relationships are inconsistent."""
    high = values["high"]
    low = values["low"]
    open_price = values["open"]
    close_price = values["close"]
    invalid = (
        (high < low)
        | (high < open_price)
        | (high < close_price)
        | (low > open_price)
        | (low > close_price)
    )
    return int(invalid.fillna(True).sum())


def validate_ticker_data(ticker: str, data: pd.DataFrame) -> dict[str, Any]:
    """Validate one ticker's market data and return errors and warnings separately."""
    errors: list[str] = []
    warnings: list[str] = []

    # Check that the date field is available before date-based validation.
    if "date" not in data.columns:
        return {
            "ticker": ticker,
            "observations": int(len(data)),
            "errors": ["Missing required date field."],
            "warnings": [],
            "passed": False,
        }

    # Check for missing required price and volume columns.
    missing_columns = [column for column in REQUIRED_FIELDS if column not in data.columns]
    if missing_columns:
        errors.append(f"Missing required fields: {missing_columns}")

    # Validate duplicate dates and the requested date window.
    duplicate_dates = int(data["date"].duplicated().sum())
    if duplicate_dates:
        errors.append(f"Duplicate observation dates: {duplicate_dates}")

    start_boundary = pd.Timestamp(START_DATE, tz="UTC")
    end_boundary = pd.Timestamp(END_DATE, tz="UTC")
    outside_window = (data["date"] < start_boundary) | (data["date"] >= end_boundary)
    outside_window_count = int(outside_window.fillna(True).sum())
    if outside_window_count:
        errors.append(f"Observations outside requested window: {outside_window_count}")

    # Initialise metrics so the report remains consistent if columns are missing.
    missing_raw_values: int | None = None
    missing_adjusted_values: int | None = None
    invalid_raw_numeric_rows: int | None = None
    invalid_adjusted_numeric_rows: int | None = None
    invalid_raw_price_rows: int | None = None
    invalid_adjusted_price_rows: int | None = None
    invalid_ohlc_rows: int | None = None
    invalid_adjusted_ohlc_rows: int | None = None
    negative_volume_rows: int | None = None
    zero_volume_rows: int | None = None

    # Validate raw OHLCV data only when all required columns are present.
    if all(column in data.columns for column in RAW_OHLCV):
        raw_values = data[RAW_OHLCV]
        missing_raw_values = int(raw_values.isna().sum().sum())
        numeric_raw = _numeric_frame(data, RAW_OHLCV)
        invalid_raw_numeric_rows = _count_invalid_numeric_rows(numeric_raw)

        if missing_raw_values:
            errors.append(f"Missing raw OHLCV values: {missing_raw_values}")
        if invalid_raw_numeric_rows:
            errors.append(
                "Raw OHLCV contains missing, non-numeric or non-finite values "
                f"in {invalid_raw_numeric_rows} row(s)."
            )

        # Perform range and consistency checks only on rows with valid numbers.
        valid_raw_rows = np.isfinite(numeric_raw.to_numpy(dtype=float)).all(axis=1)
        valid_raw = numeric_raw.loc[valid_raw_rows]
        if not valid_raw.empty:
            invalid_raw_price_rows = int((valid_raw[RAW_PRICE_FIELDS] <= 0).any(axis=1).sum())
            invalid_ohlc_rows = _count_invalid_ohlc_rows(valid_raw)
            negative_volume_rows = int((valid_raw["volume"] < 0).sum())
            zero_volume_rows = int((valid_raw["volume"] == 0).sum())
            if invalid_raw_price_rows:
                errors.append(f"Rows with non-positive raw prices: {invalid_raw_price_rows}")
            if invalid_ohlc_rows:
                errors.append(f"Rows failing raw OHLC consistency checks: {invalid_ohlc_rows}")
            if negative_volume_rows:
                errors.append(f"Rows with negative volume: {negative_volume_rows}")
            if zero_volume_rows:
                warnings.append(f"Rows with zero volume: {zero_volume_rows}")

    # Validate adjusted OHLCV data, including NaN and infinite values.
    if all(column in data.columns for column in ADJUSTED_OHLCV):
        adjusted_values = data[ADJUSTED_OHLCV]
        missing_adjusted_values = int(adjusted_values.isna().sum().sum())
        numeric_adjusted = _numeric_frame(data, ADJUSTED_OHLCV)
        invalid_adjusted_numeric_rows = _count_invalid_numeric_rows(numeric_adjusted)

        if missing_adjusted_values:
            errors.append(f"Missing adjusted OHLCV values: {missing_adjusted_values}")
        if invalid_adjusted_numeric_rows:
            errors.append(
                "Adjusted OHLCV contains missing, non-numeric or non-finite values "
                f"in {invalid_adjusted_numeric_rows} row(s)."
            )

        valid_adjusted_rows = np.isfinite(numeric_adjusted.to_numpy(dtype=float)).all(axis=1)
        valid_adjusted = numeric_adjusted.loc[valid_adjusted_rows]
        if not valid_adjusted.empty:
            invalid_adjusted_price_rows = int(
                (valid_adjusted[ADJUSTED_PRICE_FIELDS] <= 0).any(axis=1).sum()
            )
            adjusted_for_ohlc = valid_adjusted.rename(
                columns={
                    "adjOpen": "open",
                    "adjHigh": "high",
                    "adjLow": "low",
                    "adjClose": "close",
                }
            )
            invalid_adjusted_ohlc_rows = _count_invalid_ohlc_rows(adjusted_for_ohlc)
            if invalid_adjusted_price_rows:
                errors.append(
                    "Rows with non-positive adjusted prices: "
                    f"{invalid_adjusted_price_rows}"
                )
            if invalid_adjusted_ohlc_rows:
                errors.append(
                    "Rows failing adjusted OHLC consistency checks: "
                    f"{invalid_adjusted_ohlc_rows}"
                )

    # Treat absent corporate-action fields as warnings, not validation errors.
    missing_corporate_action_fields = [
        column for column in CORPORATE_ACTION_FIELDS if column not in data.columns
    ]
    if missing_corporate_action_fields:
        warnings.append(
            f"Missing corporate-action fields: {missing_corporate_action_fields}"
        )

    # Build a stable report record.
    return {
        "ticker": ticker,
        "observations": int(len(data)),
        "first_date": data["date"].min().date().isoformat() if not data.empty else None,
        "last_date": data["date"].max().date().isoformat() if not data.empty else None,
        "duplicate_dates": duplicate_dates,
        "missing_raw_ohlcv_values": missing_raw_values,
        "missing_adjusted_ohlcv_values": missing_adjusted_values,
        "invalid_raw_numeric_rows": invalid_raw_numeric_rows,
        "invalid_adjusted_numeric_rows": invalid_adjusted_numeric_rows,
        "invalid_raw_price_rows": invalid_raw_price_rows,
        "invalid_adjusted_price_rows": invalid_adjusted_price_rows,
        "negative_volume_rows": negative_volume_rows,
        "zero_volume_rows": zero_volume_rows,
        "invalid_ohlc_rows": invalid_ohlc_rows,
        "invalid_adjusted_ohlc_rows": invalid_adjusted_ohlc_rows,
        "outside_window_rows": outside_window_count,
        "missing_columns": missing_columns,
        "errors": errors,
        "warnings": warnings,
        "passed": len(errors) == 0,
    }


def main() -> int:
    """Run the data acquisition, validation and reporting workflow."""
    # Validate credentials before creating directories or making requests.
    try:
        api_key = get_tiingo_api_key()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    create_output_directories()
    retrieval_timestamp = datetime.now(timezone.utc).isoformat()
    ticker_datasets: dict[str, pd.DataFrame] = {}
    validation_results: list[dict[str, Any]] = []
    raw_files: list[str] = []

    # Use one session and retry transient GET failures.
    with create_http_session() as session:
        for ticker in TICKERS:
            print(f"\nProcessing {ticker}...")
            try:
                data, raw_path, http_status = download_ticker_data(session, ticker, api_key)
                result = validate_ticker_data(ticker, data)
                result["http_status"] = http_status
                result["raw_file"] = str(raw_path.relative_to(PROJECT_ROOT))
                ticker_datasets[ticker] = data
                raw_files.append(result["raw_file"])
                validation_results.append(result)

                print(f"Observations: {result['observations']}")
                print(f"Date range: {result.get('first_date')} to {result.get('last_date')}")
                print(f"Validation passed: {result['passed']}")
                for error in result.get("errors", []):
                    print(f"ERROR: {error}")
                for warning in result.get("warnings", []):
                    print(f"WARNING: {warning}")

            except requests.RequestException as exc:
                # Log the exception type only; never print headers or credentials.
                message = f"Request failed ({type(exc).__name__})."
                print(f"ERROR: {ticker}: {message}")
                validation_results.append({
                    "ticker": ticker,
                    "http_status": getattr(getattr(exc, "response", None), "status_code", None),
                    "passed": False,
                    "errors": [message],
                    "warnings": [],
                })
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                message = f"Response processing failed ({type(exc).__name__})."
                print(f"ERROR: {ticker}: {message}")
                validation_results.append({
                    "ticker": ticker,
                    "http_status": None,
                    "passed": False,
                    "errors": [message],
                    "warnings": [],
                })

    # Check whether every requested ticker was downloaded and validated.
    all_downloads_completed = all(ticker in ticker_datasets for ticker in TICKERS)
    all_tickers_passed = (
        all_downloads_completed
        and len(validation_results) == len(TICKERS)
        and all(result.get("passed", False) for result in validation_results)
    )

    # Compare trading dates only when all ticker datasets are available.
    common_date_count: int | None = None
    date_sets_identical: bool | None = None
    if all_downloads_completed:
        ticker_date_sets = {
            ticker: set(data["date"].tolist()) for ticker, data in ticker_datasets.items()
        }
        common_dates = set.intersection(*(ticker_date_sets[ticker] for ticker in TICKERS))
        common_date_count = len(common_dates)
        reference_dates = ticker_date_sets[TICKERS[0]]
        date_sets_identical = all(
            ticker_date_sets[ticker] == reference_dates for ticker in TICKERS[1:]
        )

        for result in validation_results:
            result["common_trading_dates"] = common_date_count
            result["date_sets_identical"] = date_sets_identical

        if not date_sets_identical:
            print("\nWARNING: Candidate datasets do not have identical date sets.")

    # Only publish the consolidated CSV when all validation checks pass and
    # candidate date sets are identical. This avoids replacing a prior dataset
    # with data known to be incomplete or inconsistent.

    # Initialise publication status and error information.
    dataset_saved = False
    publication_error = None
    csv_path = PROCESSED_DATA_DIR / "candidate_stocks_daily.csv"

    # Publish the dataset only when all validation checks pass.
    if all_tickers_passed and date_sets_identical is True:
        # Combine all validated ticker datasets.
        combined_data = pd.concat(
            [ticker_datasets[ticker] for ticker in TICKERS],
            ignore_index=True,
        ).sort_values(
            ["ticker", "date"],
            kind="stable",
        ).reset_index(drop=True)

        # Define a temporary file alongside the target CSV.
        temporary_csv_path = csv_path.with_suffix(csv_path.suffix + ".tmp")

        try:
            # Write the complete dataset before replacing the existing CSV.
            combined_data.to_csv(temporary_csv_path, index=False)

            # Publish the dataset only after the temporary write succeeds.
            temporary_csv_path.replace(csv_path)

            # Mark publication as successful only after replacement completes.
            dataset_saved = True
            print(f"\nConsolidated dataset saved to: {csv_path}")

        except OSError as exc:
            # Record the failure without exposing unrelated system details.
            publication_error = (
                f"CSV publication failed ({type(exc).__name__})."
            )
            print(f"\nERROR: {publication_error}", file=sys.stderr)

        finally:
            # Remove any temporary file left behind after publication.
            try:
                temporary_csv_path.unlink(missing_ok=True)
            except OSError as exc:
                # Report cleanup failures without changing publication status.
                cleanup_error = (
                    f"Temporary CSV cleanup failed ({type(exc).__name__})."
                )
                print(f"WARNING: {cleanup_error}", file=sys.stderr)

    else:
        # Explain why the consolidated dataset was not updated.
        publication_error = (
            "CSV publication skipped because acquisition, validation, "
            "or cross-ticker date checks did not pass."
        )
        print(f"\nWARNING: {publication_error}")

    # Create the data-quality report regardless of acquisition success.
    report = {
        "retrieval_timestamp_utc": retrieval_timestamp,
        "provider": "Tiingo",
        "requested_start_date": START_DATE,
        "requested_end_date_exclusive": END_DATE,
        "tickers": TICKERS,
        "raw_files": raw_files,
        "all_downloads_completed": all_downloads_completed,
        "all_tickers_passed_validation": all_tickers_passed,
        "common_trading_dates": common_date_count,
        "date_sets_identical": date_sets_identical,

        # Record publication status and any associated error.
        "consolidated_dataset_saved": dataset_saved,
        "consolidated_dataset_path": (
            str(csv_path.relative_to(PROJECT_ROOT))
            if dataset_saved
            else None
        ),
        "publication_error": publication_error,

        "ticker_results": validation_results,
    }
    report_path = REPORT_DIR / "tiingo_data_quality_report.json"
    write_json_atomically(report_path, report)
    print(f"Quality report saved to: {report_path}")

    # Return a non-zero exit code when the workflow did not fully pass.
    print("\nDATA ACQUISITION SUMMARY")
    print(f"All downloads completed: {all_downloads_completed}")
    print(f"All ticker validations passed: {all_tickers_passed}")
    print(f"Date sets identical: {date_sets_identical}")
    print(f"Consolidated dataset updated: {dataset_saved}")

    return 0 if dataset_saved else 1


if __name__ == "__main__":
    # Exit with the workflow's status code so failures are visible to shells and CI.
    raise SystemExit(main())
