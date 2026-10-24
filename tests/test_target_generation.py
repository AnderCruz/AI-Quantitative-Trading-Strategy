"""Unit tests for forward-return target generation."""

import numpy as np
import pandas as pd
import pytest

from src.target_generation import create_targets


HORIZONS = (1, 5, 10)

REGRESSION_TARGETS = [
    f"forward_return_{h}d" for h in HORIZONS
]

CLASSIFICATION_TARGETS = [
    f"positive_return_{h}d" for h in HORIZONS
]

TARGET_COLUMNS = REGRESSION_TARGETS + CLASSIFICATION_TARGETS


def make_price_data(
    ticker: str = "ASSET_A",
    periods: int = 15,
    start_price: float = 100.0,
) -> pd.DataFrame:
    """Create deterministic synthetic daily price data."""
    dates = pd.bdate_range("2025-01-01", periods=periods)

    return pd.DataFrame(
        {
            "date": dates,
            "ticker": ticker,
            "Open": start_price + np.arange(periods, dtype=float),
            "Close": start_price + np.arange(periods, dtype=float) + 0.5,
            "High": start_price + np.arange(periods, dtype=float) + 1.0,
            "Low": start_price + np.arange(periods, dtype=float) - 0.5,
            "Volume": np.full(periods, 1_000_000),
            "Dividends": np.zeros(periods),
            "Stock Splits": np.zeros(periods),
        }
    )


def test_creates_all_six_target_columns():
    """All approved regression and classification targets are created."""
    data = make_price_data()

    result = create_targets(data)

    assert all(column in result.columns for column in TARGET_COLUMNS)


def test_one_session_return_uses_next_open_and_following_close():
    """The one-session target uses the approved entry and exit prices."""
    data = make_price_data(periods=4)

    result = create_targets(data)

    expected_return = data.loc[1, "Close"] / data.loc[1, "Open"] - 1

    assert result.loc[0, "forward_return_1d"] == pytest.approx(
        expected_return
    )


def test_classification_target_matches_regression_target():
    """Classification is one only for strictly positive returns."""
    data = make_price_data(periods=15)

    result = create_targets(data)

    for horizon in HORIZONS:
        regression = result[f"forward_return_{horizon}d"]
        classification = result[f"positive_return_{horizon}d"]

        valid = regression.notna()

        expected = (regression.loc[valid] > 0).astype(int)

        pd.testing.assert_series_equal(
            classification.loc[valid].astype(int),
            expected.astype(int),
            check_names=False,
        )


def test_unavailable_future_targets_remain_missing():
    """Targets requiring unavailable future prices remain missing."""
    data = make_price_data(periods=12)

    result = create_targets(data)

    for horizon in HORIZONS:
        target = f"forward_return_{horizon}d"

        assert result[target].iloc[-horizon:].isna().all()


def test_calculations_do_not_cross_ticker_boundaries():
    """Targets are calculated independently for each ticker."""
    first = make_price_data(ticker="ASSET_A", periods=12, start_price=100)
    second = make_price_data(ticker="ASSET_B", periods=12, start_price=500)

    data = pd.concat([first, second], ignore_index=True)

    result = create_targets(data)

    first_result = result[result["ticker"] == "ASSET_A"].reset_index(drop=True)
    second_result = result[result["ticker"] == "ASSET_B"].reset_index(drop=True)

    expected_first = (
        first.loc[1, "Close"] / first.loc[1, "Open"] - 1
    )
    expected_second = (
        second.loc[1, "Close"] / second.loc[1, "Open"] - 1
    )

    assert first_result.loc[0, "forward_return_1d"] == pytest.approx(
        expected_first
    )
    assert second_result.loc[0, "forward_return_1d"] == pytest.approx(
        expected_second
    )


def test_original_input_data_is_not_modified():
    """Target generation preserves the original input DataFrame."""
    data = make_price_data()
    original = data.copy(deep=True)

    create_targets(data)

    pd.testing.assert_frame_equal(data, original)


def test_unsorted_input_is_returned_in_original_row_order():
    """Targets use chronological order but preserve the input row order."""
    data = make_price_data(periods=12)
    shuffled = data.sample(frac=1, random_state=42).reset_index(drop=True)

    result = create_targets(shuffled)

    assert result["date"].tolist() == shuffled["date"].tolist()

    chronological = result.sort_values("date").reset_index(drop=True)
    expected = (
        chronological.loc[1, "Close"] / chronological.loc[1, "Open"] - 1
    )

    first_date = chronological.loc[0, "date"]
    actual = result.loc[
        result["date"] == first_date, "forward_return_1d"
    ].iloc[0]

    assert actual == pytest.approx(expected)


def test_missing_required_columns_raise_a_clear_error():
    """Missing required input columns produce a useful exception."""
    data = make_price_data().drop(columns=["Open"])

    with pytest.raises(ValueError, match="Open"):
        create_targets(data)


def test_duplicate_ticker_dates_are_rejected():
    """Duplicate observations for a ticker and date are rejected."""
    data = make_price_data(periods=12)
    data = pd.concat([data, data.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate"):
        create_targets(data)


@pytest.mark.parametrize(
    ("horizon", "expected_return"),
    [
        (1, 101.5 / 101.0 - 1),
        (5, 105.5 / 101.0 - 1),
        (10, 110.5 / 101.0 - 1),
    ],
)
def test_forward_returns_match_explicit_horizon_calculations(
    horizon, expected_return
):
    """Forward returns must use the approved entry and exit sessions."""
    data = make_price_data(periods=15, start_price=100.0)

    result = create_targets(data)

    actual_return = result.loc[0, f"forward_return_{horizon}d"]

    assert actual_return == pytest.approx(expected_return)


def test_non_sequential_dataframe_index_is_preserved():
    """Non-sequential DataFrame indices are preserved."""
    data = make_price_data(periods=12)
    data.index = np.arange(100, 112) * 2

    result = create_targets(data)

    assert result.index.tolist() == data.index.tolist()

    expected_return = data.iloc[1]["Close"] / data.iloc[1]["Open"] - 1

    assert result.iloc[0]["forward_return_1d"] == pytest.approx(
        expected_return
    )


def test_duplicate_dataframe_indices_are_supported():
    """Duplicate DataFrame indices do not corrupt target calculations."""
    data = make_price_data(periods=12)
    data.index = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5]

    result = create_targets(data)

    expected_return = data.iloc[1]["Close"] / data.iloc[1]["Open"] - 1

    assert result.index.tolist() == data.index.tolist()
    assert result.iloc[0]["forward_return_1d"] == pytest.approx(
        expected_return
    )


@pytest.mark.parametrize("invalid_price", [np.nan, np.inf, -np.inf, 0.0, -1.0])
@pytest.mark.parametrize("price_column", ["Open", "Close"])
def test_invalid_execution_prices_are_rejected(invalid_price, price_column):
    """Missing, non-finite, and non-positive execution prices are rejected."""
    data = make_price_data(periods=12)
    data.loc[3, price_column] = invalid_price

    with pytest.raises(ValueError, match=price_column):
        create_targets(data)


def test_invalid_dates_are_rejected():
    """Unparseable date values are rejected."""
    data = make_price_data(periods=12)
    data["date"] = data["date"].astype(object)
    data.loc[3, "date"] = "not-a-valid-date"

    with pytest.raises((ValueError, TypeError)):
        create_targets(data)


def test_missing_ticker_values_are_rejected():
    """Missing ticker identifiers are rejected."""
    data = make_price_data(periods=12)
    data.loc[3, "ticker"] = None

    with pytest.raises(ValueError, match="Ticker"):
        create_targets(data)


def test_non_dataframe_input_is_rejected():
    """Inputs other than pandas DataFrames are rejected."""
    with pytest.raises(TypeError, match="DataFrame"):
        create_targets([{"date": "2025-01-01"}])
