# Import the required library and path utilities.
from pathlib import Path

import pandas as pd


# Define the project root and input dataset.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "candidate_stocks_daily.csv"
)


# Load the previously acquired dataset without making API requests.
df = pd.read_csv(DATA_PATH, parse_dates=["date"])


# Define the candidate stocks.
tickers = ["AAPL", "MSFT", "NVDA", "TSLA"]


# Inspect records containing dividends or stock splits.
for ticker in tickers:
    # Select the current stock.
    stock = df.loc[df["ticker"] == ticker].copy()

    # Identify rows with non-zero dividend cash or a non-unit split factor.
    corporate_actions = stock.loc[
        (stock["divCash"] != 0)
        | (stock["splitFactor"] != 1)
    ].copy()

    # Display the corporate-action records.
    print("\n" + "=" * 90)
    print(f"CORPORATE-ACTION REVIEW: {ticker}")
    print("=" * 90)

    # Display the relevant fields in chronological order.
    columns = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "adjClose",
        "volume",
        "adjVolume",
        "divCash",
        "splitFactor",
    ]

    print(
        corporate_actions[columns]
        .sort_values("date")
        .to_string(index=False)
    )