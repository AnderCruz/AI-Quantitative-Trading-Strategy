# Import the libraries required for data analysis and report generation.
import json
from pathlib import Path

import pandas as pd


# Define the project root directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]


# Define the input dataset and output report directories.
DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "candidate_stocks_daily.csv"
)

REPORT_DIR = PROJECT_ROOT / "reports" / "data_quality"


# Define the candidate stocks.
TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA"]


# Define the columns required for the analysis.
REQUIRED_COLUMNS = [
    "date",
    "ticker",
    "close",
    "adjClose",
    "splitFactor",
    "divCash",
]


# Define the number of observations to display around each stock split.
EVENT_WINDOW = 2


def load_data() -> pd.DataFrame:
    """Load the existing dataset and validate its required columns."""

    # Check that the input dataset exists.
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {DATA_PATH}"
        )

    # Load the dataset and parse the date column.
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])

    # Check that all required columns are available.
    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # Restrict the analysis to the four approved candidate stocks.
    df = df.loc[df["ticker"].isin(TICKERS)].copy()

    # Convert numerical fields explicitly.
    numeric_columns = [
        "close",
        "adjClose",
        "splitFactor",
        "divCash",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # Sort the observations chronologically within each stock.
    df = df.sort_values(
        ["ticker", "date"]
    ).reset_index(drop=True)

    # Reject duplicate ticker-date observations.
    duplicate_count = df.duplicated(
        subset=["ticker", "date"]
    ).sum()

    if duplicate_count > 0:
        raise ValueError(
            f"Found {duplicate_count} duplicate ticker-date rows."
        )

    # Reject missing or non-positive prices.
    invalid_prices = (
        df[["close", "adjClose"]].isna().any(axis=1)
        | (df["close"] <= 0)
        | (df["adjClose"] <= 0)
    )

    if invalid_prices.any():
        raise ValueError(
            f"Found {invalid_prices.sum()} rows with invalid prices."
        )

    # Confirm that all four stocks are represented.
    available_tickers = set(df["ticker"].unique())
    expected_tickers = set(TICKERS)

    if available_tickers != expected_tickers:
        raise ValueError(
            "The dataset does not contain exactly the expected "
            f"candidate stocks. Found: {sorted(available_tickers)}"
        )

    return df


def calculate_adjustment_metrics(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate adjustment ratios and raw versus adjusted returns."""

    # Calculate adjustment ratios and returns separately for each stock.
    groups = []

    for ticker, group in df.groupby("ticker", sort=True):
        # Create a separate copy to avoid modifying the original data.
        group = group.copy()

        # Calculate the adjusted-to-raw closing-price ratio.
        group["adjustment_ratio"] = (
            group["adjClose"] / group["close"]
        )

        # Calculate close-to-close raw and adjusted returns.
        group["raw_return"] = group["close"].pct_change()

        group["adjusted_return"] = (
            group["adjClose"].pct_change()
        )

        # Calculate the difference between the two return series.
        group["return_difference"] = (
            group["adjusted_return"] - group["raw_return"]
        )

        # Retain the ticker identifier for reporting.
        group["ticker"] = ticker

        groups.append(group)

    # Combine all candidate stocks into a single analysis dataset.
    analysed_df = pd.concat(
        groups,
        ignore_index=True,
    )

    # Calculate descriptive statistics for each candidate stock.
    summary_rows = []

    for ticker, group in analysed_df.groupby("ticker", sort=True):
        ratios = group["adjustment_ratio"]

        summary_rows.append(
            {
                "ticker": ticker,
                "observations": int(len(group)),
                "first_date": group["date"].min().date().isoformat(),
                "last_date": group["date"].max().date().isoformat(),
                "ratio_min": float(ratios.min()),
                "ratio_25th_percentile": float(ratios.quantile(0.25)),
                "ratio_median": float(ratios.median()),
                "ratio_mean": float(ratios.mean()),
                "ratio_75th_percentile": float(ratios.quantile(0.75)),
                "ratio_max": float(ratios.max()),
                "ratio_std": float(ratios.std()),
                "raw_return_abs_max": float(
                    group["raw_return"].abs().max()
                ),
                "adjusted_return_abs_max": float(
                    group["adjusted_return"].abs().max()
                ),
            }
        )

    summary_df = pd.DataFrame(summary_rows)

    return analysed_df, summary_df


def analyse_split_events(
    analysed_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Inspect raw and adjusted prices around recorded stock splits."""

    event_rows = []
    window_rows = []

    # Examine each stock independently.
    for ticker in TICKERS:
        stock = (
            analysed_df.loc[analysed_df["ticker"] == ticker]
            .sort_values("date")
            .reset_index(drop=True)
        )

        # Identify rows with a non-unit split factor.
        split_positions = stock.index[
            stock["splitFactor"].notna()
            & (stock["splitFactor"] != 1)
        ].tolist()

        # Inspect each recorded split event.
        for position in split_positions:
            event = stock.loc[position]

            event_rows.append(
                {
                    "ticker": ticker,
                    "split_date": event["date"].date().isoformat(),
                    "split_factor": float(event["splitFactor"]),
                    "raw_close": float(event["close"]),
                    "adjusted_close": float(event["adjClose"]),
                    "adjustment_ratio": float(
                        event["adjustment_ratio"]
                    ),
                    "raw_return_on_event_date": (
                        float(event["raw_return"])
                        if pd.notna(event["raw_return"])
                        else None
                    ),
                    "adjusted_return_on_event_date": (
                        float(event["adjusted_return"])
                        if pd.notna(event["adjusted_return"])
                        else None
                    ),
                }
            )

            # Select observations before and after the split date.
            start_position = max(
                0,
                position - EVENT_WINDOW,
            )

            end_position = min(
                len(stock) - 1,
                position + EVENT_WINDOW,
            )

            event_window = stock.loc[
                start_position:end_position
            ].copy()

            # Record the distance from the split date.
            event_window["sessions_from_split"] = (
                event_window.index - position
            )

            # Add event identifiers to the window records.
            event_window["split_date"] = (
                event["date"].date().isoformat()
            )

            event_window["split_factor_at_event"] = float(
                event["splitFactor"]
            )

            # Retain the fields needed to review the event.
            for _, row in event_window.iterrows():
                window_rows.append(
                    {
                        "ticker": ticker,
                        "split_date": row["split_date"],
                        "split_factor_at_event": (
                            row["split_factor_at_event"]
                        ),
                        "sessions_from_split": int(
                            row["sessions_from_split"]
                        ),
                        "date": row["date"].date().isoformat(),
                        "close": float(row["close"]),
                        "adjClose": float(row["adjClose"]),
                        "adjustment_ratio": float(
                            row["adjustment_ratio"]
                        ),
                        "raw_return": (
                            float(row["raw_return"])
                            if pd.notna(row["raw_return"])
                            else None
                        ),
                        "adjusted_return": (
                            float(row["adjusted_return"])
                            if pd.notna(row["adjusted_return"])
                            else None
                        ),
                    }
                )

    # Convert the collected records into dataframes.
    events_df = pd.DataFrame(event_rows)
    windows_df = pd.DataFrame(window_rows)

    return events_df, windows_df


def save_reports(
    analysed_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    events_df: pd.DataFrame,
    windows_df: pd.DataFrame,
) -> None:
    """Save the analysis outputs and a reproducible JSON report."""

    # Create the output directory if it does not exist.
    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Save the observation-level analysis.
    analysed_df.to_csv(
        REPORT_DIR / "tiingo_adjustment_ratios.csv",
        index=False,
    )

    # Save descriptive statistics by ticker.
    summary_df.to_csv(
        REPORT_DIR / "tiingo_adjustment_ratio_summary.csv",
        index=False,
    )

    # Save split-event details.
    events_df.to_csv(
        REPORT_DIR / "tiingo_split_event_analysis.csv",
        index=False,
    )

    # Save the observations surrounding each split.
    windows_df.to_csv(
        REPORT_DIR / "tiingo_split_event_windows.csv",
        index=False,
    )

    # Prepare a machine-readable JSON report.
    report = {
        "analysis": "Tiingo Price-Adjustment Ratio Analysis",
        "input_dataset": str(DATA_PATH),
        "candidate_tickers": TICKERS,
        "event_window_sessions": EVENT_WINDOW,
        "interpretation_note": (
            "This report describes relationships between raw and "
            "adjusted prices. It does not independently establish "
            "the correctness of every corporate-action adjustment."
        ),
        "ticker_summary": summary_df.to_dict(
            orient="records"
        ),
        "split_events": events_df.to_dict(
            orient="records"
        ),
    }

    # Save the JSON report.
    report_path = (
        REPORT_DIR
        / "tiingo_adjustment_ratio_analysis.json"
    )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            allow_nan=False,
        )

    print("\nREPORTS SAVED")
    print("=" * 70)
    print(f"Observation-level analysis: {REPORT_DIR / 'tiingo_adjustment_ratios.csv'}")
    print(f"Ticker summary: {REPORT_DIR / 'tiingo_adjustment_ratio_summary.csv'}")
    print(f"Split events: {REPORT_DIR / 'tiingo_split_event_analysis.csv'}")
    print(f"Split windows: {REPORT_DIR / 'tiingo_split_event_windows.csv'}")
    print(f"JSON report: {report_path}")


def main() -> None:
    """Run the complete price-adjustment analysis."""

    # Load and validate the existing dataset.
    df = load_data()

    print("=" * 80)
    print("TIINGO PRICE-ADJUSTMENT RATIO ANALYSIS")
    print("=" * 80)
    print(f"Input dataset: {DATA_PATH}")
    print(f"Dataset shape: {df.shape}")
    print(f"Candidate stocks: {', '.join(TICKERS)}")

    # Calculate price-adjustment ratios and return metrics.
    analysed_df, summary_df = calculate_adjustment_metrics(df)

    # Analyse the observations surrounding stock splits.
    events_df, windows_df = analyse_split_events(analysed_df)

    # Display the descriptive statistics.
    print("\nADJUSTMENT-RATIO AND RETURN SUMMARY")
    print("=" * 80)

    display_columns = [
        "ticker",
        "observations",
        "first_date",
        "last_date",
        "ratio_min",
        "ratio_median",
        "ratio_mean",
        "ratio_max",
        "raw_return_abs_max",
        "adjusted_return_abs_max",
    ]

    print(
        summary_df[display_columns].to_string(
            index=False,
            float_format=lambda value: f"{value:.6f}",
        )
    )

    # Display the identified split events.
    print("\nRECORDED STOCK-SPLIT EVENTS")
    print("=" * 80)

    if events_df.empty:
        print("No non-unit split factors were found.")
    else:
        print(
            events_df.to_string(
                index=False,
                float_format=lambda value: f"{value:.6f}",
            )
        )

    # Display the observations surrounding each split.
    print("\nOBSERVATIONS AROUND STOCK SPLITS")
    print("=" * 80)

    if windows_df.empty:
        print("No split-event windows are available.")
    else:
        print(
            windows_df.to_string(
                index=False,
                float_format=lambda value: f"{value:.6f}",
            )
        )

    # Save all analysis outputs.
    save_reports(
        analysed_df,
        summary_df,
        events_df,
        windows_df,
    )

    print("\nANALYSIS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()