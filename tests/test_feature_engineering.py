import numpy as np
import pandas as pd
import pytest

from src.feature_engineering import (
    RETURN_WINDOWS,
    create_historical_return_features,
)


def make_price_data(
    ticker: str = "ASSET_A",
    periods: int = 25,
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
        }
    )


FEATURE_COLUMNS = [
    f"close_return_{window}d" for window in RETURN_WINDOWS
]


def test_creates_all_four_historical_return_features():
    """All four approved historical return features are created."""
    data = make_price_data()

    result = create_historical_return_features(data)

    assert all(column in result.columns for column in FEATURE_COLUMNS)


@pytest.mark.parametrize("window", RETURN_WINDOWS)
def test_historical_returns_match_explicit_calculations(window):
    """Historical returns use the close from the specified prior session."""
    data = make_price_data(periods=25, start_price=100.0)

    result = create_historical_return_features(data)

    expected_return = (
        data.loc[window, "Close"] / data.loc[0, "Close"] - 1
    )

    assert result.loc[window, f"close_return_{window}d"] == pytest.approx(
        expected_return
    )


@pytest.mark.parametrize("window", RETURN_WINDOWS)
def test_insufficient_history_remains_missing(window):
    """Features remain missing when the required history is unavailable."""
    data = make_price_data(periods=25)

    result = create_historical_return_features(data)

    assert result[f"close_return_{window}d"].iloc[:window].isna().all()


def test_calculations_do_not_cross_ticker_boundaries():
    """Historical returns are calculated independently for each ticker."""
    first = make_price_data(
        ticker="ASSET_A",
        periods=25,
        start_price=100.0,
    )
    second = make_price_data(
        ticker="ASSET_B",
        periods=25,
        start_price=500.0,
    )

    data = pd.concat([first, second], ignore_index=True)

    result = create_historical_return_features(data)

    first_result = result[result["ticker"] == "ASSET_A"].reset_index(drop=True)
    second_result = result[result["ticker"] == "ASSET_B"].reset_index(drop=True)

    expected_first = first.loc[1, "Close"] / first.loc[0, "Close"] - 1
    expected_second = second.loc[1, "Close"] / second.loc[0, "Close"] - 1

    assert first_result.loc[1, "close_return_1d"] == pytest.approx(
        expected_first
    )
    assert second_result.loc[1, "close_return_1d"] == pytest.approx(
        expected_second
    )


def test_original_input_data_is_not_modified():
    """Feature engineering preserves the original input DataFrame."""
    data = make_price_data()
    original = data.copy(deep=True)

    create_historical_return_features(data)

    pd.testing.assert_frame_equal(data, original)


def test_unsorted_input_is_returned_in_original_row_order():
    """Calculations are chronological while the original row order is preserved."""
    data = make_price_data()
    shuffled = data.sample(frac=1, random_state=42).reset_index(drop=True)

    result = create_historical_return_features(shuffled)

    assert result["date"].tolist() == shuffled["date"].tolist()

    chronological = result.sort_values("date").reset_index(drop=True)
    expected = chronological.loc[1, "Close"] / chronological.loc[0, "Close"] - 1

    first_date = chronological.loc[1, "date"]
    actual = result.loc[
        result["date"] == first_date,
        "close_return_1d",
    ].iloc[0]

    assert actual == pytest.approx(expected)


def test_non_sequential_dataframe_index_is_preserved():
    """Non-sequential DataFrame indices are preserved."""
    data = make_price_data()
    data.index = np.arange(100, 125) * 2

    result = create_historical_return_features(data)

    assert result.index.tolist() == data.index.tolist()


def test_duplicate_dataframe_indices_are_supported():
    """Duplicate DataFrame indices do not corrupt feature calculations."""
    data = make_price_data()
    data.index = [index // 2 for index in range(len(data))]

    result = create_historical_return_features(data)

    expected = data.iloc[1]["Close"] / data.iloc[0]["Close"] - 1

    assert result.index.tolist() == data.index.tolist()
    assert result.iloc[1]["close_return_1d"] == pytest.approx(expected)


def test_missing_required_columns_raise_a_clear_error():
    """Missing required input columns produce a useful exception."""
    data = make_price_data().drop(columns=["Close"])

    with pytest.raises(ValueError, match="Close"):
        create_historical_return_features(data)


def test_duplicate_ticker_dates_are_rejected():
    """Duplicate observations for a ticker and date are rejected."""
    data = make_price_data()
    data = pd.concat([data, data.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="Duplicate"):
        create_historical_return_features(data)


@pytest.mark.parametrize(
    "invalid_price",
    [np.nan, np.inf, -np.inf, 0.0, -1.0],
)
def test_invalid_closing_prices_are_rejected(invalid_price):
    """Missing, non-finite, and non-positive closing prices are rejected."""
    data = make_price_data()
    data.loc[3, "Close"] = invalid_price

    with pytest.raises(ValueError, match="Close"):
        create_historical_return_features(data)

def test_invalid_dates_are_rejected():
    """Invalid dates are rejected."""
    data = make_price_data()

    # Allow an invalid string to be assigned to the date column.
    data["date"] = data["date"].astype(object)
    data.loc[3, "date"] = "not-a-date"

    with pytest.raises((ValueError, TypeError)):
        create_historical_return_features(data)

def test_missing_ticker_is_rejected():
    """Missing ticker identifiers are rejected."""
    data = make_price_data()
    data.loc[3, "ticker"] = None

    with pytest.raises(ValueError, match="Ticker"):
        create_historical_return_features(data)

def test_missing_date_is_rejected():
    """Missing dates are rejected."""
    data = make_price_data()
    data.loc[3, "date"] = pd.NaT

    with pytest.raises(ValueError, match="Date"):
        create_historical_return_features(data)

# Import NumPy and pandas for independent calculations.
import numpy as np
import pandas as pd

# Import the feature-engineering function.
from src.feature_engineering import create_historical_return_features


def test_volatility_features_match_sample_standard_deviation():
    # Create deterministic closing prices.
    data = pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-01", periods=25),
            "ticker": ["TEST"] * 25,
            "Close": np.arange(100, 125, dtype=float),
        }
    )

    # Calculate the features.
    result = create_historical_return_features(data)

    # Calculate one-session returns independently.
    daily_returns = data["Close"].pct_change()

    # Verify each volatility feature against pandas' sample standard deviation.
    for window in (5, 10, 20):
        expected = daily_returns.rolling(
            window=window,
            min_periods=window,
        ).std(ddof=1)

        pd.testing.assert_series_equal(
            result[f"close_volatility_{window}d"],
            expected.rename(f"close_volatility_{window}d"),
            check_names=True,
        )


def test_volatility_features_require_complete_windows():
    # Create enough observations to test all three windows.
    data = pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-01", periods=22),
            "ticker": ["TEST"] * 22,
            "Close": np.arange(100, 122, dtype=float),
        }
    )

    # Calculate the features.
    result = create_historical_return_features(data)

    # Five returns require six closing prices.
    assert result["close_volatility_5d"].iloc[:5].isna().all()
    assert result["close_volatility_5d"].iloc[5:].notna().all()

    # Ten returns require eleven closing prices.
    assert result["close_volatility_10d"].iloc[:10].isna().all()
    assert result["close_volatility_10d"].iloc[10:].notna().all()

    # Twenty returns require twenty-one closing prices.
    assert result["close_volatility_20d"].iloc[:20].isna().all()
    assert result["close_volatility_20d"].iloc[20:].notna().all()


def test_volatility_features_do_not_mix_tickers():
    # Create two assets with different price histories.
    data = pd.DataFrame(
        {
            "date": list(pd.bdate_range("2024-01-01", periods=22)) * 2,
            "ticker": ["AAA"] * 22 + ["BBB"] * 22,
            "Close": list(np.arange(100, 122, dtype=float))
            + list(np.arange(200, 222, dtype=float) ** 1.1),
        }
    )

    # Calculate features jointly.
    combined = create_historical_return_features(data)

    # Calculate features independently for each asset.
    for ticker in ("AAA", "BBB"):
        individual_data = data.loc[data["ticker"] == ticker].copy()
        individual = create_historical_return_features(individual_data)

        for window in (5, 10, 20):
            column = f"close_volatility_{window}d"

            np.testing.assert_allclose(
                combined.loc[combined["ticker"] == ticker, column].to_numpy(),
                individual[column].to_numpy(),
                equal_nan=True,
            )


def test_volatility_features_preserve_duplicate_dataframe_indices():
    # Create a DataFrame with duplicate index labels.
    data = pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-01", periods=22),
            "ticker": ["TEST"] * 22,
            "Close": np.arange(100, 122, dtype=float),
        },
        index=[0] * 22,
    )

    # Calculate the features.
    result = create_historical_return_features(data)

    # Verify that the original index is preserved.
    assert result.index.equals(data.index)

    # Verify that each volatility feature contains the expected values.
    daily_returns = data["Close"].pct_change()

    for window in (5, 10, 20):
        column = f"close_volatility_{window}d"
        expected = daily_returns.rolling(window=window, min_periods=window).std(
            ddof=1
        )

        np.testing.assert_allclose(
            result[column].to_numpy(),
            expected.to_numpy(),
            equal_nan=True,
        )


def test_volatility_features_do_not_use_future_observations():
    # Create a deterministic historical price series.
    data = pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-01", periods=30),
            "ticker": ["TEST"] * 30,
            "Close": np.linspace(100, 130, 30),
        }
    )

    # Calculate features using the complete series.
    complete = create_historical_return_features(data)

    # Calculate features using only observations available at a cutoff.
    cutoff = 20
    truncated = create_historical_return_features(data.iloc[: cutoff + 1])

    # Features at the cutoff must not change when future observations are added.
    for window in (5, 10, 20):
        column = f"close_volatility_{window}d"

        np.testing.assert_allclose(
            complete[column].iloc[cutoff],
            truncated[column].iloc[cutoff],
            equal_nan=True,
        )