"""Generate forward-return regression and classification targets."""

import numpy as np
import pandas as pd


HORIZONS = (1, 5, 10)

REQUIRED_COLUMNS = {
    "date",
    "ticker",
    "Open",
    "Close",
}


def create_targets(data: pd.DataFrame) -> pd.DataFrame:
    """Create forward-return targets independently for each ticker.

    Predictions are assumed to be made after the close of session t.
    Entry is referenced to the next session's open, and exit to the
    close of the session corresponding to the selected horizon.

    The input DataFrame is not modified. The returned DataFrame preserves
    the original row order and includes six target columns.
    """
    # Validate the input type.
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Input data must be a pandas DataFrame.")

    # Validate the required columns.
    missing_columns = REQUIRED_COLUMNS.difference(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns: {missing}")

    # Work on a copy to preserve the source DataFrame.
    result = data.copy(deep=True)

    # Validate ticker and date identifiers.
    if result["ticker"].isna().any():
        raise ValueError("Ticker values must not be missing.")

    if result["date"].isna().any():
        raise ValueError("Date values must not be missing.")

    # Convert dates to datetime for reliable chronological ordering.
    result["date"] = pd.to_datetime(result["date"], errors="raise")

    # Reject duplicate observations for the same ticker and date.
    if result.duplicated(subset=["ticker", "date"]).any():
        raise ValueError("duplicate ticker-date observations are not allowed.")

    # Validate prices used in target calculations.
    for column in ("Open", "Close"):
        result[column] = pd.to_numeric(result[column], errors="raise")

        invalid_prices = (
            result[column].isna()
            | ~np.isfinite(result[column])
            | (result[column] <= 0)
        )

        if invalid_prices.any():
            raise ValueError(
                f"{column} must contain finite, strictly positive prices."
            )

    # Retain the input row order while calculating chronologically.
    result["_original_row_order"] = np.arange(len(result))

    result = result.sort_values(
        ["ticker", "date"],
        kind="stable",
    )

    # Calculate targets independently for each ticker.
    grouped = result.groupby("ticker", sort=False)

    for horizon in HORIZONS:
        # Entry is the next session's opening price.
        entry_price = grouped["Open"].shift(-1)

        # Exit is the close of session t+h.
        exit_price = grouped["Close"].shift(-horizon)

        # Calculate gross price return before transaction costs.
        forward_return = exit_price / entry_price - 1

        result[f"forward_return_{horizon}d"] = forward_return

        # Classify strictly positive returns as 1; other valid returns as 0.
        classification = pd.Series(
            np.nan,
            index=result.index,
            dtype="float64",
        )

        valid_returns = forward_return.notna()
        classification.loc[valid_returns] = (
            forward_return.loc[valid_returns] > 0
        ).astype(int)

        result[f"positive_return_{horizon}d"] = classification

    # Restore the original row order.
    result = result.sort_values("_original_row_order", kind="stable")
    result = result.drop(columns="_original_row_order")

    return result
