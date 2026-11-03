"""Tests for Bank of England IADB request construction and CSV validation."""

from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from scripts.acquire_boe_data import (
    PROJECT_ROOT,
    IADBConfiguration,
    build_iadb_request_params,
    fetch_iadb_csv,
    load_bank_rate_config,
    load_iadb_config,
)


def _mock_csv_response(content: bytes) -> Mock:
    """Create a successful mocked BoE HTTP response."""

    response = Mock()
    response.content = content
    response.raise_for_status.return_value = None
    return response


def _fetch_with_mocked_csv(
    csv_content: bytes,
    date_from: date = date(2025, 1, 1),
    date_to: date | None = date(2025, 1, 31),
) -> bytes:
    """Fetch a supplied CSV payload through the mocked HTTP boundary."""

    with patch(
        "scripts.acquire_boe_data.requests.get",
        return_value=_mock_csv_response(csv_content),
    ):
        return fetch_iadb_csv(
            series_code="IUDBEDR",
            date_from=date_from,
            date_to=date_to,
        )


def test_load_bank_rate_config():
    """Load and validate the approved Bank Rate configuration."""

    config_path = (
        PROJECT_ROOT
        / "configs/datasets/uk_interest_rates/bank_rate.yaml"
    )

    config, config_hash = load_bank_rate_config(config_path)

    assert config.dataset.dataset_id == "UK_BANK_RATE"
    assert config.provider.name == "bank_of_england"
    assert config.provider.series_code == "IUDBEDR"
    assert config.data.frequency == "business_daily"
    assert config.data.currency == "GBP"
    assert config.temporal.timezone == "Europe/London"
    assert config.temporal.publication_schedule == "not_assumed"
    assert config.licensing.status == "pending_verification"
    assert config.licensing.commercial_use_approved is False
    assert config.licensing.redistribution_approved is False
    assert len(config_hash) == 64


def test_load_bank_rate_config_rejects_missing_file():
    """Reject a configuration file that does not exist."""

    with pytest.raises(FileNotFoundError):
        load_bank_rate_config(
            PROJECT_ROOT / "configs/nonexistent.yaml"
        )

def test_load_iadb_config_loads_bank_rate():
    config_path = (
        PROJECT_ROOT
        / "configs"
        / "datasets"
        / "uk_interest_rates"
        / "bank_rate.yaml"
    )

    config, config_hash = load_iadb_config(config_path)

    assert config.dataset.dataset_id == "UK_BANK_RATE"
    assert config.provider.series_code == "IUDBEDR"
    assert config.provider.source_type == "iadb"
    assert len(config_hash) == 64


def test_load_iadb_config_loads_sonia():
    config_path = (
        PROJECT_ROOT
        / "configs"
        / "datasets"
        / "uk_interest_rates"
        / "sonia.yaml"
    )

    config, config_hash = load_iadb_config(config_path)

    assert config.dataset.dataset_id == "UK_SONIA"
    assert config.provider.series_code == "IUDSOIA"
    assert config.provider.source_type == "iadb"
    assert config.storage.dataset_directory == "sonia"
    assert len(config_hash) == 64


def test_load_bank_rate_config_rejects_sonia_configuration():
    config_path = (
        PROJECT_ROOT
        / "configs"
        / "datasets"
        / "uk_interest_rates"
        / "sonia.yaml"
    )

    with pytest.raises(ValueError):
        load_bank_rate_config(config_path)


def test_iadb_configuration_rejects_invalid_provider_name():
    """Reject an IADB configuration with an invalid provider name."""

    config_path = (
        PROJECT_ROOT
        / "configs"
        / "datasets"
        / "uk_interest_rates"
        / "sonia.yaml"
    )

    config, _ = load_iadb_config(config_path)
    config_data = config.model_dump()

    config_data["provider"]["name"] = "invalid_provider"

    with pytest.raises(
        ValueError,
        match="provider must be bank_of_england",
    ):
        IADBConfiguration.model_validate(config_data)


def test_iadb_configuration_rejects_invalid_source_type():
    """Reject an IADB configuration with an invalid source type."""

    config_path = (
        PROJECT_ROOT
        / "configs"
        / "datasets"
        / "uk_interest_rates"
        / "sonia.yaml"
    )

    config, _ = load_iadb_config(config_path)
    config_data = config.model_dump()

    config_data["provider"]["source_type"] = "invalid_source"

    with pytest.raises(
        ValueError,
        match="source_type must be iadb",
    ):
        IADBConfiguration.model_validate(config_data)


@pytest.mark.parametrize(
    ("field", "unsafe_value"),
    [
        ("provider_directory", "../outside"),
        ("provider_directory", "/tmp/data"),
        ("provider_directory", "bank/of/england"),
        ("dataset_directory", "../../outside"),
        ("dataset_directory", "/tmp/data"),
        ("dataset_directory", "bank/rate"),
    ],
)
def test_iadb_configuration_rejects_unsafe_storage_directories(
    field: str,
    unsafe_value: str,
):
    """Reject unsafe storage directory names."""

    config_path = (
        PROJECT_ROOT
        / "configs"
        / "datasets"
        / "uk_interest_rates"
        / "bank_rate.yaml"
    )

    config, _ = load_iadb_config(config_path)
    config_data = config.model_dump()

    config_data["storage"][field] = unsafe_value

    with pytest.raises(ValueError):
        IADBConfiguration.model_validate(config_data)


def test_build_iadb_request_params():
    """Build a valid Bank Rate CSV request."""

    params = build_iadb_request_params(
        series_code="IUDBEDR",
        date_from=date(1975, 1, 1),
    )

    assert params == {
        "csv.x": "yes",
        "Datefrom": "01/Jan/1975",
        "Dateto": "now",
        "SeriesCodes": "IUDBEDR",
        "CSVF": "TN",
        "UsingCodes": "Y",
        "VPD": "N",
    }


def test_build_iadb_request_params_with_custom_end_date():
    """Support an explicitly defined end date."""

    params = build_iadb_request_params(
        series_code="IUDBEDR",
        date_from=date(1975, 1, 1),
        date_to=date(2025, 12, 31),
    )

    assert params["Datefrom"] == "01/Jan/1975"
    assert params["Dateto"] == "31/Dec/2025"


def test_build_iadb_request_params_rejects_empty_series_code():
    """Reject an empty series code."""

    with pytest.raises(ValueError):
        build_iadb_request_params(
            series_code="",
            date_from=date(1975, 1, 1),
        )


def test_build_iadb_request_params_rejects_invalid_date_range():
    """Reject an end date earlier than the start date."""

    with pytest.raises(ValueError):
        build_iadb_request_params(
            series_code="IUDBEDR",
            date_from=date(2025, 1, 1),
            date_to=date(2024, 12, 31),
        )


def test_fetch_iadb_csv_returns_original_csv_bytes():
    """Return the exact original bytes after validating the CSV."""

    csv_content = (
        b"DATE,IUDBEDR\n"
        b"01 Jan 2025,4.75\n"
        b"02 Jan 2025,4.75\n"
    )

    with patch(
        "scripts.acquire_boe_data.requests.get",
        return_value=_mock_csv_response(csv_content),
    ) as mock_get:
        result = fetch_iadb_csv(
            series_code="IUDBEDR",
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 31),
        )

    assert result == csv_content
    mock_get.assert_called_once()


def test_fetch_iadb_csv_rejects_empty_response():
    """Reject an empty HTTP response."""

    with patch(
        "scripts.acquire_boe_data.requests.get",
        return_value=_mock_csv_response(b""),
    ):
        with pytest.raises(ValueError, match="empty response"):
            fetch_iadb_csv(
                series_code="IUDBEDR",
                date_from=date(2025, 1, 1),
            )


def test_fetch_iadb_csv_rejects_html_response():
    """Reject HTML returned instead of CSV."""

    with patch(
        "scripts.acquire_boe_data.requests.get",
        return_value=_mock_csv_response(
            b"<html><body>Error</body></html>"
        ),
    ):
        with pytest.raises(ValueError, match="HTML"):
            fetch_iadb_csv(
                series_code="IUDBEDR",
                date_from=date(2025, 1, 1),
            )


def test_fetch_iadb_csv_handles_http_error():
    """Translate HTTP errors into a connector-level error."""

    response = Mock()
    response.raise_for_status.side_effect = (
        requests.exceptions.HTTPError("404 Client Error")
    )

    with patch(
        "scripts.acquire_boe_data.requests.get",
        return_value=response,
    ):
        with pytest.raises(RuntimeError, match="HTTP error"):
            fetch_iadb_csv(
                series_code="IUDBEDR",
                date_from=date(2025, 1, 1),
            )


def test_fetch_iadb_csv_handles_timeout():
    """Translate request timeouts into a connector-level error."""

    with patch(
        "scripts.acquire_boe_data.requests.get",
        side_effect=requests.exceptions.Timeout,
    ):
        with pytest.raises(RuntimeError, match="timed out"):
            fetch_iadb_csv(
                series_code="IUDBEDR",
                date_from=date(2025, 1, 1),
            )


def test_fetch_iadb_csv_handles_connection_error():
    """Translate connection errors into a connector-level error."""

    with patch(
        "scripts.acquire_boe_data.requests.get",
        side_effect=requests.exceptions.ConnectionError,
    ):
        with pytest.raises(RuntimeError, match="request failed"):
            fetch_iadb_csv(
                series_code="IUDBEDR",
                date_from=date(2025, 1, 1),
            )


def test_fetch_iadb_csv_rejects_missing_date_column():
    """Reject a CSV without the DATE column."""

    content = b"PERIOD,IUDBEDR\n01 Jan 2025,4.75\n"

    with pytest.raises(ValueError, match="DATE column"):
        _fetch_with_mocked_csv(content)


def test_fetch_iadb_csv_rejects_missing_series_column():
    """Reject a CSV without the requested series column."""

    content = b"DATE,OTHER_SERIES\n01 Jan 2025,4.75\n"

    with pytest.raises(ValueError, match="IUDBEDR column"):
        _fetch_with_mocked_csv(content)


def test_fetch_iadb_csv_rejects_invalid_timeout():
    """Reject a timeout that is not a positive integer."""

    with pytest.raises(ValueError, match="positive integer"):
        fetch_iadb_csv(
            series_code="IUDBEDR",
            date_from=date(2025, 1, 1),
            timeout=0,
        )


def test_fetch_iadb_csv_rejects_boolean_timeout():
    """Reject booleans even though bool is a subclass of int."""

    with pytest.raises(ValueError, match="positive integer"):
        fetch_iadb_csv(
            series_code="IUDBEDR",
            date_from=date(2025, 1, 1),
            timeout=True,
        )


def test_build_iadb_request_params_rejects_datetime_start_date():
    """Reject datetime where a date-only value is required."""

    with pytest.raises(ValueError, match="Start date"):
        build_iadb_request_params(
            series_code="IUDBEDR",
            date_from=datetime(2025, 1, 1),
        )


def test_build_iadb_request_params_rejects_datetime_end_date():
    """Reject datetime where a date-only end value is required."""

    with pytest.raises(ValueError, match="End date"):
        build_iadb_request_params(
            series_code="IUDBEDR",
            date_from=date(2025, 1, 1),
            date_to=datetime(2025, 1, 31),
        )


def test_fetch_iadb_csv_rejects_invalid_observation_date():
    """Reject an observation date that cannot be parsed."""

    content = b"DATE,IUDBEDR\nnot-a-date,4.75\n"

    with pytest.raises(ValueError, match="invalid observation date"):
        _fetch_with_mocked_csv(content)


def test_fetch_iadb_csv_rejects_observation_before_requested_range():
    """Reject observations earlier than the requested start date."""

    content = b"DATE,IUDBEDR\n31 Dec 2024,4.75\n"

    with pytest.raises(ValueError, match="outside the requested date range"):
        _fetch_with_mocked_csv(content)


def test_fetch_iadb_csv_rejects_observation_after_requested_range():
    """Reject observations later than the requested end date."""

    content = b"DATE,IUDBEDR\n03 Feb 2025,4.75\n"

    with pytest.raises(ValueError, match="outside the requested date range"):
        _fetch_with_mocked_csv(content)


def test_fetch_iadb_csv_rejects_duplicate_observation_dates():
    """Reject duplicate observation dates."""

    content = (
        b"DATE,IUDBEDR\n"
        b"02 Jan 2025,4.75\n"
        b"02 Jan 2025,4.75\n"
    )

    with pytest.raises(ValueError, match="duplicate observation date"):
        _fetch_with_mocked_csv(content)


def test_fetch_iadb_csv_rejects_non_chronological_observations():
    """Reject observations that are not in ascending date order."""

    content = (
        b"DATE,IUDBEDR\n"
        b"03 Jan 2025,4.75\n"
        b"02 Jan 2025,4.75\n"
    )

    with pytest.raises(ValueError, match="chronological order"):
        _fetch_with_mocked_csv(content)


@pytest.mark.parametrize(
    "value",
    ["not-a-number", "NaN", "inf", "-inf"],
)
def test_fetch_iadb_csv_rejects_non_finite_or_non_numeric_values(value):
    """Reject non-numeric and non-finite rate observations."""

    content = (
        "DATE,IUDBEDR\n"
        f"02 Jan 2025,{value}\n"
    ).encode("utf-8")

    with pytest.raises(ValueError, match="finite numeric value"):
        _fetch_with_mocked_csv(content)


def test_fetch_iadb_csv_rejects_missing_rate_value():
    """Reject an observation with an empty rate value."""

    content = b"DATE,IUDBEDR\n02 Jan 2025,\n"

    with pytest.raises(ValueError, match="finite numeric value"):
        _fetch_with_mocked_csv(content)


def test_fetch_iadb_csv_rejects_malformed_row():
    """Reject a row whose field count differs from the CSV header."""

    content = (
        b"DATE,IUDBEDR\n"
        b"02 Jan 2025,4.75,unexpected\n"
    )

    with pytest.raises(ValueError, match="malformed CSV row"):
        _fetch_with_mocked_csv(content)


def test_fetch_iadb_csv_rejects_response_without_observations():
    """Reject a valid header that contains no observations."""

    content = b"DATE,IUDBEDR\n"

    with pytest.raises(ValueError, match="no valid observations"):
        _fetch_with_mocked_csv(content)