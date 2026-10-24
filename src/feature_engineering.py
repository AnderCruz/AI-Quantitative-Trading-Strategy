"""Generate historical price-based features."""

import numpy as np
import pandas as pd


RETURN_WINDOWS = (1, 5, 10, 20)

REQUIRED_COLUMNS = {
    "date",
    "ticker",
    "Close",
}


def create_historical_return_features(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """Create historical closing-price return features.

    Features are calculated independently for each ticker using
    information available on or before each observation date.

    The input DataFrame is not modified. The returned DataFrame
    preserves the original row order and index.
    """
    # Validate the input type.
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Input data must be a pandas DataFrame.")

    # Validate the required columns.
    missing_columns = REQUIRED_COLUMNS.difference(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns: {missing}")

    # Work on a copy to preserve the original DataFrame.
    result = data.copy(deep=True)

    # Validate ticker and date identifiers.
    if result["ticker"].isna().any():
        raise ValueError("Ticker values must not be missing.")

    if result["date"].isna().any():
        raise ValueError("Date values must not be missing.")

    # Convert dates and closing prices to their required types.
    result["date"] = pd.to_datetime(result["date"], errors="raise")
    result["Close"] = pd.to_numeric(result["Close"], errors="raise")

    # Validate closing prices.
    invalid_prices = (
        result["Close"].isna()
        | ~np.isfinite(result["Close"])
        | (result["Close"] <= 0)
    )

    if invalid_prices.any():
        raise ValueError(
            "Close must contain finite, strictly positive prices."
        )

    # Reject duplicate observations for the same ticker and date.
    if result.duplicated(subset=["ticker", "date"]).any():
        raise ValueError(
            "Duplicate ticker-date observations are not allowed."
        )

    # Preserve the original row order during chronological calculations.
    result["_original_row_order"] = np.arange(len(result))

    result = result.sort_values(
        ["ticker", "date"],
        kind="stable",
    )

    # Calculate historical returns independently for each ticker.
    grouped = result.groupby("ticker", sort=False)["Close"]

    for window in RETURN_WINDOWS:
        # Compare the current close with the close k sessions earlier.
        previous_close = grouped.shift(window)

        result[f"close_return_{window}d"] = (
            result["Close"] / previous_close - 1
        )

    # Calculate one-session returns for volatility estimation.
    result["_close_return_1d"] = (
        result.groupby("ticker", sort=False)["Close"]
        .pct_change()
    )

    # Calculate rolling sample volatility using historical returns only.
    volatility_windows = (5, 10, 20)

    for window in volatility_windows:
        # Group returns by ticker to prevent cross-asset contamination.
        rolling_volatility = (
            result.groupby("ticker", sort=False)["_close_return_1d"]
            .rolling(window=window, min_periods=window)
            .std(ddof=1)
        )

        # Remove the ticker index level created by the grouped rolling operation.
        rolling_volatility = rolling_volatility.reset_index(
            level=0,
            drop=True,
        )

        # Store the volatility feature.
        result[f"close_volatility_{window}d"] = rolling_volatility

    # Remove the temporary one-session return column.
    result = result.drop(columns="_close_return_1d")

    # Restore the original row order and remove the temporary column.
    result = result.sort_values(
        "_original_row_order",
        kind="stable",
    )
    result = result.drop(columns="_original_row_order")

    return result