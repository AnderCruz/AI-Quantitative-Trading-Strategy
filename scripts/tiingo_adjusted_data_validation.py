# Import the libraries required for data inspection.
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# Define the project root and input dataset.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "candidate_stocks_daily.csv"

# Define the candidate stocks.
TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA"]

# Define raw and adjusted price fields.
RAW_PRICE_COLUMNS = ["open", "high", "low", "close"]
ADJUSTED_PRICE_COLUMNS = [
    "adjOpen",
    "adjHigh",
    "adjLow",
    "adjClose",
]

# Define adjusted OHLCV fields.
ADJUSTED_OHLCV_COLUMNS = ADJUSTED_PRICE_COLUMNS + ["adjVolume"]


def main():
    # Stop if the expected dataset does not exist.
    if not DATA_PATH.exists():
        sys.exit(f"ERROR: Dataset not found: {DATA_PATH}")

    # Load the consolidated dataset.
    data = pd.read_csv(DATA_PATH, parse_dates=["date"])

    # Display the dataset dimensions.
    print("=" * 70)
    print("ADJUSTED DATA AND CORPORATE-ACTION VALIDATION")
    print("=" * 70)
    print(f"Dataset shape: {data.shape}")

    # Confirm that the expected columns are available.
    required_columns = (
        ["date", "ticker"]
        + RAW_PRICE_COLUMNS
        + ["volume"]
        + ADJUSTED_OHLCV_COLUMNS
        + ["divCash", "splitFactor"]
    )

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        sys.exit(f"ERROR: Missing columns: {missing_columns}")

    # Convert market-data fields to numeric values.
    numeric_columns = (
        RAW_PRICE_COLUMNS
        + ["volume"]
        + ADJUSTED_OHLCV_COLUMNS
        + ["divCash", "splitFactor"]
    )

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    # Report the overall missing-value counts.
    print("\nMissing values by field:")
    print(data[required_columns].isna().sum().to_string())

    # Store the results for each ticker.
    results = []

    # Inspect each candidate separately.
    for ticker in TICKERS:
        group = (
            data[data["ticker"] == ticker]
            .sort_values("date")
            .copy()
        )

        print("\n" + "=" * 70)
        print(f"Ticker: {ticker}")
        print("=" * 70)

        # Check missing adjusted OHLCV values.
        missing_adjusted = int(
            group[ADJUSTED_OHLCV_COLUMNS].isna().sum().sum()
        )

        # Check non-positive raw prices.
        invalid_raw_prices = int(
            (group[RAW_PRICE_COLUMNS] <= 0).any(axis=1).sum()
        )

        # Check non-positive adjusted prices.
        invalid_adjusted_prices = int(
            (group[ADJUSTED_PRICE_COLUMNS] <= 0).any(axis=1).sum()
        )

        # Check negative volume values.
        negative_raw_volume = int((group["volume"] < 0).sum())
        negative_adjusted_volume = int((group["adjVolume"] < 0).sum())

        # Check zero-volume observations.
        zero_raw_volume = int((group["volume"] == 0).sum())

        # Check raw OHLC consistency.
        invalid_raw_ohlc = (
            (group["high"] < group["low"])
            | (group["high"] < group["open"])
            | (group["high"] < group["close"])
            | (group["low"] > group["open"])
            | (group["low"] > group["close"])
        )

        # Check adjusted OHLC consistency.
        invalid_adjusted_ohlc = (
            (group["adjHigh"] < group["adjLow"])
            | (group["adjHigh"] < group["adjOpen"])
            | (group["adjHigh"] < group["adjClose"])
            | (group["adjLow"] > group["adjOpen"])
            | (group["adjLow"] > group["adjClose"])
        )

        # Count observations with dividend cash values.
        dividend_observations = int(
            (group["divCash"].fillna(0) != 0).sum()
        )

        # Count observations with non-unit split factors.
        split_observations = int(
            (
                group["splitFactor"].notna()
                & ~np.isclose(
                    group["splitFactor"].fillna(1),
                    1.0,
                )
            ).sum()
        )

        # Display the validation metrics.
        print(f"Observations: {len(group):,}")
        print(f"Missing adjusted OHLCV values: {missing_adjusted}")
        print(f"Rows with non-positive raw prices: {invalid_raw_prices}")
        print(
            "Rows with non-positive adjusted prices: "
            f"{invalid_adjusted_prices}"
        )
        print(f"Negative raw-volume rows: {negative_raw_volume}")
        print(
            "Negative adjusted-volume rows: "
            f"{negative_adjusted_volume}"
        )
        print(f"Zero raw-volume rows: {zero_raw_volume}")
        print(
            "Rows failing raw OHLC checks: "
            f"{int(invalid_raw_ohlc.sum())}"
        )
        print(
            "Rows failing adjusted OHLC checks: "
            f"{int(invalid_adjusted_ohlc.sum())}"
        )
        print(
            "Observations with non-zero dividend cash: "
            f"{dividend_observations}"
        )
        print(
            "Observations with non-unit split factors: "
            f"{split_observations}"
        )

        # Record the validation results.
        results.append({
            "ticker": ticker,
            "observations": len(group),
            "missing_adjusted_ohlcv": missing_adjusted,
            "invalid_raw_prices": invalid_raw_prices,
            "invalid_adjusted_prices": invalid_adjusted_prices,
            "negative_raw_volume": negative_raw_volume,
            "negative_adjusted_volume": negative_adjusted_volume,
            "zero_raw_volume": zero_raw_volume,
            "invalid_raw_ohlc": int(invalid_raw_ohlc.sum()),
            "invalid_adjusted_ohlc": int(
                invalid_adjusted_ohlc.sum()
            ),
            "dividend_observations": dividend_observations,
            "split_observations": split_observations,
        })

    # Compare trading-date sets across all candidates.
    date_sets = {
        ticker: set(
            data.loc[data["ticker"] == ticker, "date"]
        )
        for ticker in TICKERS
    }

    # Check whether all four candidates share identical dates.
    identical_dates = all(
        date_sets[ticker] == date_sets[TICKERS[0]]
        for ticker in TICKERS[1:]
    )

    print("\n" + "=" * 70)
    print("CROSS-TICKER DATE VALIDATION")
    print("=" * 70)
    print(f"Identical trading-date sets: {identical_dates}")

    # Display the consolidated validation table.
    summary = pd.DataFrame(results)

    print("\n" + "=" * 70)
    print("CONSOLIDATED VALIDATION SUMMARY")
    print("=" * 70)
    print(summary.to_string(index=False))

    # Check core numerical integrity conditions.
    critical_columns = [
        "missing_adjusted_ohlcv",
        "invalid_raw_prices",
        "invalid_adjusted_prices",
        "negative_raw_volume",
        "negative_adjusted_volume",
        "invalid_raw_ohlc",
        "invalid_adjusted_ohlc",
    ]

    critical_checks_passed = bool(
        (summary[critical_columns] == 0).all().all()
    )

    # Report the result without implying that all data risks are resolved.
    print("\n" + "=" * 70)
    print("VALIDATION RESULT")
    print("=" * 70)
    print(f"Critical numerical checks passed: {critical_checks_passed}")
    print(f"Trading-date consistency passed: {identical_dates}")

    # Return a non-zero status if a critical check fails.
    if not critical_checks_passed or not identical_dates:
        sys.exit(1)


if __name__ == "__main__":
    # Run the adjusted-data validation workflow.
    main()