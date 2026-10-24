"""Tests for the configured single-asset Yahoo Finance acquisition."""

# Import test utilities.
from unittest.mock import Mock

import pandas as pd
import pytest

# Import the module under test.
from scripts import yahoo_single_asset_acquisition as acquisition


# Define a valid test configuration.
@pytest.fixture
def valid_config():
    """Return a minimal valid acquisition configuration."""

    return {
        "asset": {
            "ticker": "LLOY.L",
            "exchange": "LSE",
            "country": "UK",
            "currency": "GBP",
        },
        "data": {
            "provider": "yfinance",
            "start_date": "2026-01-01",
            "end_date": "2026-01-05",
            "interval": "1d",
        },
    }


# Define deterministic market data for tests.
@pytest.fixture
def sample_market_data():
    """Return simulated daily OHLCV data."""

    dates = pd.to_datetime(
        ["2026-01-02", "2026-01-04"],
        utc=True,
    )

    return pd.DataFrame(
        {
            "Open": [100.0, 102.0],
            "High": [103.0, 104.0],
            "Low": [99.0, 101.0],
            "Close": [102.0, 103.0],
            "Adj Close": [102.0, 103.0],
            "Volume": [1000, 1200],
            "Dividends": [0.0, 0.0],
            "Stock Splits": [0.0, 0.0],
        },
        index=dates,
    )


def test_download_uses_central_configuration(
    monkeypatch,
    valid_config,
    sample_market_data,
):
    """Verify that configured acquisition parameters reach yfinance."""

    # Mock the external provider to prevent network access.
    download_mock = Mock(return_value=sample_market_data.copy())
    monkeypatch.setattr(acquisition.yf, "download", download_mock)

    # Download and validate simulated observations.
    result = acquisition.download_asset_data(valid_config)

    # Verify the configured acquisition parameters.
    download_mock.assert_called_once_with(
        "LLOY.L",
        start="2026-01-01",
        end="2026-01-05",
        interval="1d",
        auto_adjust=False,
        actions=True,
        repair=False,
        keepna=True,
        progress=False,
        threads=False,
        timeout=30,
        multi_level_index=False,
    )

    # Verify the normalised result.
    assert len(result) == 2
    assert result["ticker"].eq("LLOY.L").all()
    assert result["date"].is_monotonic_increasing


def test_download_rejects_empty_provider_response(
    monkeypatch,
    valid_config,
):
    """Verify that an empty provider response raises an error."""

    # Simulate an empty provider response.
    monkeypatch.setattr(
        acquisition.yf,
        "download",
        Mock(return_value=pd.DataFrame()),
    )

    # Confirm that empty data is rejected.
    with pytest.raises(RuntimeError, match="No historical data returned"):
        acquisition.download_asset_data(valid_config)


def test_validation_rejects_duplicate_dates():
    """Verify that duplicate trading dates are rejected."""

    # Create two rows with the same trading date.
    dates = pd.to_datetime(
        ["2026-01-02", "2026-01-02"],
        utc=True,
    )

    data = pd.DataFrame(
        {
            "date": dates,
            "Open": [100.0, 100.0],
            "High": [103.0, 103.0],
            "Low": [99.0, 99.0],
            "Close": [102.0, 102.0],
            "Adj Close": [102.0, 102.0],
            "Volume": [1000, 1000],
            "Dividends": [0.0, 0.0],
            "Stock Splits": [0.0, 0.0],
            "ticker": ["LLOY.L", "LLOY.L"],
        }
    )

    # Confirm that duplicate dates are rejected.
    with pytest.raises(ValueError, match="duplicate dates"):
        acquisition.validate_asset_data(
            data,
            ticker="LLOY.L",
            start_date="2026-01-01",
            end_date="2026-01-05",
        )


def test_validation_rejects_data_after_exclusive_end_date():
    """Verify that the configured end date is exclusive."""

    # Create an observation on the exclusive end date.
    dates = pd.to_datetime(["2026-01-05"], utc=True)

    data = pd.DataFrame(
        {
            "date": dates,
            "Open": [100.0],
            "High": [103.0],
            "Low": [99.0],
            "Close": [102.0],
            "Adj Close": [102.0],
            "Volume": [1000],
            "Dividends": [0.0],
            "Stock Splits": [0.0],
            "ticker": ["LLOY.L"],
        }
    )

    # Confirm that the end date is not included.
    with pytest.raises(ValueError, match="beyond the requested period"):
        acquisition.validate_asset_data(
            data,
            ticker="LLOY.L",
            start_date="2026-01-01",
            end_date="2026-01-05",
        )


def test_validation_rejects_negative_volume():
    """Verify that negative trading volume is rejected."""

    # Create a row with invalid negative volume.
    dates = pd.to_datetime(["2026-01-02"], utc=True)

    data = pd.DataFrame(
        {
            "date": dates,
            "Open": [100.0],
            "High": [103.0],
            "Low": [99.0],
            "Close": [102.0],
            "Adj Close": [102.0],
            "Volume": [-1],
            "Dividends": [0.0],
            "Stock Splits": [0.0],
            "ticker": ["LLOY.L"],
        }
    )

    # Confirm that negative volume is rejected.
    with pytest.raises(ValueError, match="negative volume"):
        acquisition.validate_asset_data(
            data,
            ticker="LLOY.L",
            start_date="2026-01-01",
            end_date="2026-01-05",
        )
