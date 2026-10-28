"""Integrate historical features, forward targets and target maturity dates.

This module composes the project's existing calculation functions. It does not
reimplement feature, target or maturity calculations.
"""

from __future__ import annotations

import pandas as pd

from src.feature_engineering import create_historical_return_features
from src.target_generation import HORIZONS, create_targets
from src.temporal_split import get_target_maturity_dates


FEATURE_COLUMNS = (
    "close_return_1d",
    "close_return_5d",
    "close_return_10d",
    "close_return_20d",
    "close_volatility_5d",
    "close_volatility_10d",
    "close_volatility_20d",
)

TARGET_COLUMNS = tuple(
    column
    for horizon in HORIZONS
    for column in (
        f"forward_return_{horizon}d",
        f"positive_return_{horizon}d",
    )
)

MATURITY_COLUMNS = tuple(
    f"target_maturity_date_{horizon}d" for horizon in HORIZONS
)

GENERATED_COLUMNS = FEATURE_COLUMNS + TARGET_COLUMNS + MATURITY_COLUMNS

REQUIRED_INPUT_COLUMNS = {"date", "ticker", "Open", "Close"}


def build_feature_target_dataset(data: pd.DataFrame) -> pd.DataFrame:
    """Return historical data enriched with features, targets and maturity dates.

    The existing project functions remain the single source of truth for all
    calculations. A temporary RangeIndex is used internally to avoid
    label-based alignment problems when the input index contains duplicates.

    The returned DataFrame preserves the original row order and index.

    Args:
        data: Historical market data containing at least date, ticker, Open
            and Close.

    Returns:
        A copy of the input with seven features, six targets and three
        target-maturity columns appended.

    Raises:
        TypeError: If data is not a pandas DataFrame.
        ValueError: If required columns are missing or generated columns
            already exist in the input.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Input data must be a pandas DataFrame.")

    missing = REQUIRED_INPUT_COLUMNS.difference(data.columns)
    if missing:
        raise ValueError(
            "Missing required input columns: " + ", ".join(sorted(missing))
        )

    collisions = set(GENERATED_COLUMNS).intersection(data.columns)
    if collisions:
        raise ValueError(
            "Input already contains pipeline output columns: "
            + ", ".join(sorted(collisions))
        )

    # Use a clean working index to prevent accidental alignment by duplicate
    # pandas index labels.
    working = data.reset_index(drop=True).copy(deep=True)

    features = create_historical_return_features(working)
    targets = create_targets(working)
    maturity_dates = get_target_maturity_dates(
        working,
        horizons=tuple(HORIZONS),
    )

    expected_groups = (
        ("features", features, FEATURE_COLUMNS),
        ("targets", targets, TARGET_COLUMNS),
        ("maturity dates", maturity_dates, MATURITY_COLUMNS),
    )

    for group_name, frame, required_columns in expected_groups:
        missing_columns = set(required_columns).difference(frame.columns)

        if missing_columns:
            raise ValueError(
                f"The {group_name} stage did not produce required columns: "
                + ", ".join(sorted(missing_columns))
            )

        if len(frame) != len(working):
            raise ValueError(
                f"The {group_name} stage changed the number of observations."
            )

    # Assign values by position, not by index labels.
    result = data.copy(deep=True)

    for frame, columns in (
        (features, FEATURE_COLUMNS),
        (targets, TARGET_COLUMNS),
        (maturity_dates, MATURITY_COLUMNS),
    ):
        for column in columns:
            result[column] = frame[column].to_numpy(copy=True)

    if not result.index.equals(data.index) or len(result) != len(data):
        raise RuntimeError(
            "The integrated pipeline failed to preserve row alignment."
        )

    return result