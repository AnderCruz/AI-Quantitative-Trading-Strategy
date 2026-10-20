# Import standard libraries for file handling, timestamps and environment variables.
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import third-party libraries for data processing and HTTP requests.
import pandas as pd
import requests


# Define the project root and output directories.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "tiingo"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "reports" / "data_quality"

# Define the candidate stocks.
TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA"]

# Define the historical observation window.
START_DATE = "2015-01-01"
END_DATE = "2026-01-01"

# Define the Tiingo daily-price endpoint.
BASE_URL = "https://api.tiingo.com/tiingo/daily"

# Define the expected raw and adjusted market-data fields.
RAW_OHLCV = ["open", "high", "low", "close", "volume"]
ADJUSTED_OHLCV = [
    "adjOpen",
    "adjHigh",
    "adjLow",
    "adjClose",
    "adjVolume",
]

# Define the expected corporate-action fields.
CORPORATE_ACTION_FIELDS = ["divCash", "splitFactor"]


def create_output_directories():
    # Create the required output directories if they do not exist.
    for directory in [
        RAW_DATA_DIR,
        PROCESSED_DATA_DIR,
        REPORT_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def download_ticker_data(session, ticker, api_key):
    # Build the request headers without exposing the API token.
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {api_key}",
    }

    # Define the requested historical period.
    params = {
        "startDate": START_DATE,
        "endDate": END_DATE,
    }

    # Send the historical-data request.
    response = session.get(
        f"{BASE_URL}/{ticker}/prices",
        headers=headers,
        params=params,
        timeout=30,
    )

    # Raise an exception for unsuccessful HTTP responses.
    response.raise_for_status()

    # Parse the API response as JSON.
    payload = response.json()

    # Check that the response contains a list of observations.
    if not isinstance(payload, list):
        raise ValueError(
            f"{ticker}: Expected a list of historical observations."
        )

    # Reject an empty response.
    if not payload:
        raise ValueError(
            f"{ticker}: The API returned no historical observations."
        )

    # Preserve the original response before processing.
    raw_file = RAW_DATA_DIR / f"{ticker.lower()}_daily_raw.json"

    with raw_file.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    # Convert the response into a DataFrame.
    data = pd.DataFrame(payload)

    # Verify that the date field exists.
    if "date" not in data.columns:
        raise ValueError(f"{ticker}: The response has no date field.")

    # Convert dates to timezone-aware UTC timestamps.
    data["date"] = pd.to_datetime(
        data["date"],
        utc=True,
        errors="raise",
    )

    # Sort observations chronologically.
    data = data.sort_values("date").reset_index(drop=True)

    # Add the ticker identifier.
    data["ticker"] = ticker

    # Return the processed observations and original response path.
    return data, raw_file


def validate_ticker_data(ticker, data):
    # Initialise the validation results for this ticker.
    issues = []

    # Identify required fields that are missing from the response.
    required_fields = RAW_OHLCV + ADJUSTED_OHLCV

    missing_columns = [
        column
        for column in required_fields
        if column not in data.columns
    ]

    # Record missing required fields.
    if missing_columns:
        issues.append(
            f"Missing required fields: {missing_columns}"
        )

    # Check for duplicate observation dates.
    duplicate_dates = int(data["date"].duplicated().sum())

    if duplicate_dates:
        issues.append(
            f"Duplicate observation dates: {duplicate_dates}"
        )

    # Check whether observations fall outside the requested window.
    start_boundary = pd.Timestamp(START_DATE, tz="UTC")
    end_boundary = pd.Timestamp(END_DATE, tz="UTC")

    outside_window = (
        (data["date"] < start_boundary)
        | (data["date"] >= end_boundary)
    )

    outside_window_count = int(outside_window.sum())

    if outside_window_count:
        issues.append(
            f"Observations outside requested window: "
            f"{outside_window_count}"
        )

    # Initialise numerical validation results.
    missing_raw_values = None
    missing_adjusted_values = None
    invalid_raw_prices = None
    invalid_adjusted_prices = None
    negative_volume_rows = None
    zero_volume_rows = None
    invalid_ohlc_rows = None

    # Validate raw OHLCV fields when all required columns are available.
    if all(column in data.columns for column in RAW_OHLCV):
        raw_values = data[RAW_OHLCV]

        # Count missing raw market-data values.
        missing_raw_values = int(raw_values.isna().sum().sum())

        if missing_raw_values:
            issues.append(
                f"Missing raw OHLCV values: {missing_raw_values}"
            )

        # Identify non-finite values in raw market data.
        numeric_raw = raw_values.apply(
            pd.to_numeric,
            errors="coerce",
        )

        finite_raw = numeric_raw.map(
            lambda value: pd.notna(value)
            and value not in [float("inf"), float("-inf")]
        )

        if not finite_raw.all().all():
            issues.append(
                "Raw OHLCV contains non-numeric or non-finite values."
            )

        # Check that raw prices are strictly positive.
        raw_price_columns = ["open", "high", "low", "close"]

        invalid_raw_prices = int(
            (numeric_raw[raw_price_columns] <= 0).any(axis=1).sum()
        )

        if invalid_raw_prices:
            issues.append(
                f"Rows with non-positive raw prices: "
                f"{invalid_raw_prices}"
            )

        # Check that high and low are consistent with open and close.
        invalid_ohlc = (
            (numeric_raw["high"] < numeric_raw["low"])
            | (numeric_raw["high"] < numeric_raw["open"])
            | (numeric_raw["high"] < numeric_raw["close"])
            | (numeric_raw["low"] > numeric_raw["open"])
            | (numeric_raw["low"] > numeric_raw["close"])
        )

        invalid_ohlc_rows = int(invalid_ohlc.sum())

        if invalid_ohlc_rows:
            issues.append(
                f"Rows failing OHLC consistency checks: "
                f"{invalid_ohlc_rows}"
            )

        # Check for negative and zero volume.
        negative_volume_rows = int(
            (numeric_raw["volume"] < 0).sum()
        )

        zero_volume_rows = int(
            (numeric_raw["volume"] == 0).sum()
        )

        if negative_volume_rows:
            issues.append(
                f"Rows with negative volume: {negative_volume_rows}"
            )

        if zero_volume_rows:
            issues.append(
                f"Rows with zero volume: {zero_volume_rows}"
            )

    # Validate adjusted OHLCV fields when all are available.
    if all(column in data.columns for column in ADJUSTED_OHLCV):
        adjusted_values = data[ADJUSTED_OHLCV]

        # Count missing adjusted market-data values.
        missing_adjusted_values = int(
            adjusted_values.isna().sum().sum()
        )

        if missing_adjusted_values:
            issues.append(
                "Missing adjusted OHLCV values: "
                f"{missing_adjusted_values}"
            )

        # Convert adjusted fields to numeric values.
        numeric_adjusted = adjusted_values.apply(
            pd.to_numeric,
            errors="coerce",
        )

        # Check for invalid adjusted prices.
        adjusted_price_columns = [
            "adjOpen",
            "adjHigh",
            "adjLow",
            "adjClose",
        ]

        invalid_adjusted_prices = int(
            (numeric_adjusted[adjusted_price_columns] <= 0)
            .any(axis=1)
            .sum()
        )

        if invalid_adjusted_prices:
            issues.append(
                "Rows with non-positive adjusted prices: "
                f"{invalid_adjusted_prices}"
            )

        # Check that adjusted high and low are consistent.
        invalid_adjusted_ohlc = (
            (numeric_adjusted["adjHigh"] < numeric_adjusted["adjLow"])
            | (
                numeric_adjusted["adjHigh"]
                < numeric_adjusted["adjOpen"]
            )
            | (
                numeric_adjusted["adjHigh"]
                < numeric_adjusted["adjClose"]
            )
            | (
                numeric_adjusted["adjLow"]
                > numeric_adjusted["adjOpen"]
            )
            | (
                numeric_adjusted["adjLow"]
                > numeric_adjusted["adjClose"]
            )
        )

        if invalid_adjusted_ohlc.any():
            issues.append(
                "Adjusted OHLC fields contain inconsistent prices."
            )

    # Check whether corporate-action fields are present.
    missing_corporate_action_fields = [
        column
        for column in CORPORATE_ACTION_FIELDS
        if column not in data.columns
    ]

    # Record absent corporate-action fields as warnings.
    if missing_corporate_action_fields:
        issues.append(
            "Missing corporate-action fields: "
            f"{missing_corporate_action_fields}"
        )

    # Return the ticker-level validation summary.
    return {
        "ticker": ticker,
        "observations": len(data),
        "first_date": data["date"].min().date().isoformat(),
        "last_date": data["date"].max().date().isoformat(),
        "duplicate_dates": duplicate_dates,
        "missing_raw_ohlcv_values": missing_raw_values,
        "missing_adjusted_ohlcv_values": missing_adjusted_values,
        "invalid_raw_price_rows": invalid_raw_prices,
        "invalid_adjusted_price_rows": invalid_adjusted_prices,
        "negative_volume_rows": negative_volume_rows,
        "zero_volume_rows": zero_volume_rows,
        "invalid_ohlc_rows": invalid_ohlc_rows,
        "outside_window_rows": outside_window_count,
        "missing_columns": missing_columns,
        "issues": issues,
        "passed": len(issues) == 0,
    }


def main():
    # Create output directories before downloading data.
    create_output_directories()

    # Retrieve the API token from the environment.
    api_key = os.getenv("TIINGO_API_KEY")

    # Stop if the token is unavailable.
    if not api_key:
        sys.exit(
            "ERROR: TIINGO_API_KEY is not configured in this session."
        )

    # Record the retrieval timestamp in UTC.
    retrieval_timestamp = datetime.now(timezone.utc).isoformat()

    # Store ticker datasets and validation summaries.
    ticker_datasets = {}
    validation_results = []
    raw_files = []

    # Reuse one HTTP session for the requests.
    with requests.Session() as session:

        # Download and validate every candidate independently.
        for ticker in TICKERS:
            print(f"\nProcessing {ticker}...")

            try:
                # Retrieve historical observations.
                data, raw_file = download_ticker_data(
                    session,
                    ticker,
                    api_key,
                )

                # Preserve the observations for cross-ticker analysis.
                ticker_datasets[ticker] = data

                # Record the raw response location.
                raw_files.append(str(raw_file.relative_to(PROJECT_ROOT)))

                # Validate the downloaded observations.
                result = validate_ticker_data(ticker, data)

                # Add acquisition metadata.
                result["http_status"] = 200
                result["raw_file"] = str(
                    raw_file.relative_to(PROJECT_ROOT)
                )

                # Store the validation results.
                validation_results.append(result)

                # Display the principal results.
                print(f"Observations: {result['observations']}")
                print(f"Date range: {result['first_date']} to "
                      f"{result['last_date']}")
                print(f"Validation passed: {result['passed']}")

                # Display identified issues.
                for issue in result["issues"]:
                    print(f"WARNING: {issue}")

            except requests.RequestException as exc:
                # Record API failures without exposing credentials.
                print(
                    f"ERROR: {ticker} request failed: "
                    f"{type(exc).__name__}"
                )

                validation_results.append({
                    "ticker": ticker,
                    "http_status": None,
                    "passed": False,
                    "issues": [
                        f"Request failed: {type(exc).__name__}"
                    ],
                })

            except (ValueError, KeyError, TypeError) as exc:
                # Record response and processing failures.
                print(
                    f"ERROR: {ticker} processing failed: "
                    f"{type(exc).__name__}"
                )

                validation_results.append({
                    "ticker": ticker,
                    "http_status": None,
                    "passed": False,
                    "issues": [
                        f"Processing failed: {type(exc).__name__}"
                    ],
                })

    # Stop cross-ticker comparisons if any ticker failed acquisition.
    acquisition_complete = all(
        ticker in ticker_datasets for ticker in TICKERS
    )

    # Prepare the cross-ticker date comparison.
    common_date_count = None
    date_sets_identical = None

    if acquisition_complete:
        # Build a date set for each candidate.
        ticker_date_sets = {
            ticker: set(data["date"])
            for ticker, data in ticker_datasets.items()
        }

        # Count dates shared by all four candidates.
        common_dates = set.intersection(
            *ticker_date_sets.values()
        )

        common_date_count = len(common_dates)

        # Check whether all candidate date sets are identical.
        date_sets_identical = all(
            ticker_date_sets[ticker] == ticker_date_sets[TICKERS[0]]
            for ticker in TICKERS[1:]
        )

        # Record the result for each ticker.
        for result in validation_results:
            result["common_trading_dates"] = common_date_count
            result["date_sets_identical"] = date_sets_identical

        # Warn if the candidates do not share identical dates.
        if not date_sets_identical:
            print(
                "\nWARNING: The candidate datasets do not contain "
                "identical date sets."
            )

    # Save the consolidated historical dataset when all downloads succeed.
    if acquisition_complete:
        # Combine the individual ticker datasets.
        combined_data = pd.concat(
            ticker_datasets.values(),
            ignore_index=True,
        )

        # Sort the combined dataset by ticker and date.
        combined_data = combined_data.sort_values(
            ["ticker", "date"]
        ).reset_index(drop=True)

        # Save the consolidated dataset as CSV.
        csv_path = PROCESSED_DATA_DIR / "candidate_stocks_daily.csv"

        combined_data.to_csv(
            csv_path,
            index=False,
        )

        print(f"\nConsolidated dataset saved to: {csv_path}")

    # Prepare the data-quality report.
    report = {
        "retrieval_timestamp_utc": retrieval_timestamp,
        "provider": "Tiingo",
        "requested_start_date": START_DATE,
        "requested_end_date_exclusive": END_DATE,
        "tickers": TICKERS,
        "raw_files": raw_files,
        "all_downloads_completed": acquisition_complete,
        "common_trading_dates": common_date_count,
        "date_sets_identical": date_sets_identical,
        "ticker_results": validation_results,
    }

    # Save the report as JSON.
    report_path = REPORT_DIR / "tiingo_data_quality_report.json"

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, default=str)

    print(f"Quality report saved to: {report_path}")

    # Summarise the validation outcome.
    all_tickers_passed = (
        acquisition_complete
        and len(validation_results) == len(TICKERS)
        and all(
            result.get("passed", False)
            for result in validation_results
        )
    )

    print("\nDATA ACQUISITION SUMMARY")
    print(f"All downloads completed: {acquisition_complete}")
    print(f"All ticker checks passed: {all_tickers_passed}")
    print(f"Date sets identical: {date_sets_identical}")

    # Return a failure status when a validation check fails.
    if not all_tickers_passed:
        sys.exit(1)


if __name__ == "__main__":
    # Execute the acquisition and validation workflow.
    main()