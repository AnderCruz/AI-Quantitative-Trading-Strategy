# Import the libraries required for the API request and data inspection.
import os
import sys

import pandas as pd
import requests

# Retrieve the API token from the environment.
api_key = os.getenv("TIINGO_API_KEY")

# Stop execution if the token is missing.
if not api_key:
    sys.exit("ERROR: TIINGO_API_KEY is not configured.")

# Define the candidate stocks.
tickers = ["AAPL", "MSFT", "NVDA", "TSLA"]

# Define a common historical window.
start_date = "2015-10-01"
end_date = "2026-10-01"

# Configure the authentication header.
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Token {api_key}",
}

# Define the daily historical-price endpoint.
base_url = "https://api.tiingo.com/tiingo/daily"

# Store the results for the final comparison.
coverage_results = []

# Retrieve and inspect each candidate independently.
for ticker in tickers:
    print(f"\n{'=' * 60}")
    print(f"Ticker: {ticker}")
    print(f"{'=' * 60}")

    # Request daily historical prices.
    try:
        response = requests.get(
            f"{base_url}/{ticker}/prices",
            headers=headers,
            params={
                "startDate": start_date,
                "endDate": end_date,
            },
            timeout=30,
        )

        # Display the HTTP status without exposing credentials.
        print(f"HTTP status: {response.status_code}")

        # Stop processing this ticker if the request fails.
        if not response.ok:
            print("ERROR: Historical-data request failed.")
            print(f"Response: {response.text[:300]}")

            coverage_results.append({
                "ticker": ticker,
                "status": response.status_code,
                "observations": None,
                "first_date": None,
                "last_date": None,
                "duplicate_dates": None,
                "missing_values": None,
            })
            continue

        # Convert the JSON response into a DataFrame.
        data = pd.DataFrame(response.json())

        # Check whether the API returned any observations.
        if data.empty:
            print("WARNING: No observations returned.")

            coverage_results.append({
                "ticker": ticker,
                "status": response.status_code,
                "observations": 0,
                "first_date": None,
                "last_date": None,
                "duplicate_dates": 0,
                "missing_values": None,
            })
            continue

        # Convert the date column to pandas datetime values.
        data["date"] = pd.to_datetime(data["date"], utc=True)

        # Sort observations chronologically.
        data = data.sort_values("date").reset_index(drop=True)

        # Check for duplicated dates.
        duplicate_dates = int(data["date"].duplicated().sum())

        # Identify available raw and adjusted price fields.
        price_columns = [
            column
            for column in [
                "open",
                "high",
                "low",
                "close",
                "volume",
                "adjOpen",
                "adjHigh",
                "adjLow",
                "adjClose",
                "adjVolume",
                "divCash",
                "splitFactor",
            ]
            if column in data.columns
        ]

        # Check missing values in the core OHLCV fields.
        core_columns = [
            column
            for column in ["open", "high", "low", "close", "volume"]
            if column in data.columns
        ]

        missing_values = int(
            data[core_columns].isna().sum().sum()
        )

        # Check whether any core OHLCV columns are absent.
        missing_columns = [
            column
            for column in ["open", "high", "low", "close", "volume"]
            if column not in data.columns
        ]

        # Report the main coverage statistics.
        print(f"Observations: {len(data):,}")
        print(f"First observation: {data['date'].min()}")
        print(f"Last observation: {data['date'].max()}")
        print(f"Duplicate dates: {duplicate_dates}")
        print(f"Missing OHLCV values: {missing_values}")
        print(f"Missing OHLCV columns: {missing_columns}")
        print(f"Available fields: {price_columns}")

        # Check basic price consistency where the required fields exist.
        if all(
            column in data.columns
            for column in ["high", "low", "open", "close"]
        ):
            invalid_prices = (
                (data["high"] < data["low"])
                | (data["high"] < data["open"])
                | (data["high"] < data["close"])
                | (data["low"] > data["open"])
                | (data["low"] > data["close"])
            )

            print(
                "Rows failing basic OHLC consistency checks: "
                f"{int(invalid_prices.sum())}"
            )

        # Record the coverage results for comparison.
        coverage_results.append({
            "ticker": ticker,
            "status": response.status_code,
            "observations": len(data),
            "first_date": data["date"].min().date(),
            "last_date": data["date"].max().date(),
            "duplicate_dates": duplicate_dates,
            "missing_values": missing_values,
        })

    except requests.RequestException as exc:
        # Report the error type without displaying credentials.
        print(f"Connection error: {type(exc).__name__}")

    except (ValueError, KeyError, TypeError) as exc:
        # Report unexpected response-format problems.
        print(f"Data-processing error: {type(exc).__name__}")

# Display a consolidated comparison.
print(f"\n{'=' * 60}")
print("HISTORICAL COVERAGE SUMMARY")
print(f"{'=' * 60}")

if coverage_results:
    summary = pd.DataFrame(coverage_results)
    print(summary.to_string(index=False))
else:
    print("No coverage results were collected.")