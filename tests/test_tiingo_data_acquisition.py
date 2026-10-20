# Import the required libraries.
import pandas as pd
import pytest
import requests

# Import the acquisition module and its relevant functions.
from scripts import tiingo_data_acquistion as acquisition
from scripts.tiingo_data_acquistion import validate_ticker_data


# Define a reusable valid market-data observation.
@pytest.fixture
def valid_market_data() -> pd.DataFrame:
    """Return one valid synthetic market-data observation."""

    # Define internally consistent OHLCV values.
    row = {
        "date": pd.Timestamp("2020-01-02", tz="UTC"),
        "open": 10.0,
        "high": 12.0,
        "low": 8.0,
        "close": 11.0,
        "volume": 1000,
        "adjOpen": 10.0,
        "adjHigh": 12.0,
        "adjLow": 8.0,
        "adjClose": 11.0,
        "adjVolume": 1000,
        "divCash": 0.0,
        "splitFactor": 1.0,
    }

    # Return the observation as a DataFrame.
    return pd.DataFrame([row])


# Test that valid market data passes validation.
def test_valid_market_data_passes(valid_market_data):
    """Valid market data should pass all validation checks."""

    # Validate the synthetic observation.
    result = validate_ticker_data("TEST", valid_market_data)

    # Confirm that validation succeeds.
    assert result["passed"] is True
    assert result["errors"] == []

# Test that non-numeric adjusted prices are rejected.
def test_non_numeric_adjusted_price_fails(valid_market_data):
    """Non-numeric adjusted prices should fail validation."""

    # Convert the adjusted closing price column to object dtype.
    # This allows the test to represent an invalid string value.
    valid_market_data["adjClose"] = valid_market_data["adjClose"].astype(object)

    # Replace the adjusted closing price with invalid text.
    valid_market_data.loc[0, "adjClose"] = "not-a-number"

    # Validate the modified observation.
    result = validate_ticker_data("TEST", valid_market_data)

    # Confirm that the invalid value is detected.
    assert result["passed"] is False
    assert result["invalid_adjusted_numeric_rows"] == 1


# Test that infinite adjusted prices are rejected.
def test_infinite_adjusted_price_fails(valid_market_data):
    """Infinite adjusted prices should fail validation."""

    # Replace the adjusted closing price with infinity.
    valid_market_data.loc[0, "adjClose"] = float("inf")

    # Validate the modified observation.
    result = validate_ticker_data("TEST", valid_market_data)

    # Confirm that the invalid value is detected.
    assert result["passed"] is False
    assert result["invalid_adjusted_numeric_rows"] == 1


# Test that inconsistent OHLC relationships are rejected.
def test_inconsistent_ohlc_values_fail(valid_market_data):
    """The closing price must not exceed the daily high."""

    # Set the closing price above the daily high.
    valid_market_data.loc[0, "close"] = 13.0

    # Validate the modified observation.
    result = validate_ticker_data("TEST", valid_market_data)

    # Confirm that the inconsistent observation is rejected.
    assert result["passed"] is False
    assert result["invalid_ohlc_rows"] == 1


# Test that duplicate observation dates are rejected.
def test_duplicate_dates_fail(valid_market_data):
    """Duplicate observation dates should fail validation."""

    # Duplicate the existing observation.
    duplicated_data = pd.concat(
        [valid_market_data, valid_market_data],
        ignore_index=True,
    )

    # Validate the duplicated observations.
    result = validate_ticker_data("TEST", duplicated_data)

    # Confirm that the duplicate date is detected.
    assert result["passed"] is False
    assert result["duplicate_dates"] == 1


# Test that missing corporate-action fields generate warnings.
def test_missing_corporate_action_fields_generate_warnings(valid_market_data):
    """Missing corporate-action fields should generate warnings."""

    # Remove the optional corporate-action fields.
    valid_market_data = valid_market_data.drop(
        columns=["divCash", "splitFactor"]
    )

    # Validate the modified observation.
    result = validate_ticker_data("TEST", valid_market_data)

    # Confirm that validation passes with warnings.
    assert result["passed"] is True
    assert result["warnings"]

# Test that HTTP errors are raised and raw data is not written.
def test_http_error_does_not_write_raw_data(tmp_path, monkeypatch):
    """HTTP errors should stop processing before raw data is written."""

    # Create a mock response that represents an unauthorised request.
    response = requests.Response()
    response.status_code = 401
    response.url = "https://api.tiingo.com/tiingo/daily/TEST/prices"

    # Create a session that returns the mock response.
    class MockSession:
        def get(self, *args, **kwargs):
            return response

    # Redirect raw-data output to a temporary directory.
    monkeypatch.setattr(acquisition, "RAW_DATA_DIR", tmp_path)

    # Confirm that the HTTP error is raised.
    with pytest.raises(requests.HTTPError):
        acquisition.download_ticker_data(
            MockSession(),
            "TEST",
            "dummy-test-key",
        )

    # Confirm that no raw data file was created.
    assert list(tmp_path.iterdir()) == []


# Test that a JSON response with the wrong structure is rejected.
@pytest.mark.parametrize(
    "payload",
    [
        {"error": "Unexpected response structure"},
        [],
        ["invalid-row"],
        [{"open": 10.0, "close": 11.0}],
    ],
    ids=[
        "json-object-instead-of-list",
        "empty-response",
        "non-dictionary-row",
        "missing-date-field",
    ],
)
def test_invalid_api_payload_is_rejected(tmp_path, monkeypatch, payload):
    """Malformed API payloads should be rejected before raw data is written."""

    # Create a successful HTTP response with the supplied JSON payload.
    response = requests.Response()
    response.status_code = 200
    response.url = "https://api.tiingo.com/tiingo/daily/TEST/prices"
    response._content = b"{}"

    # Replace the JSON parser with the supplied synthetic payload.
    response.json = lambda: payload

    # Create a session that returns the mock response.
    class MockSession:
        def get(self, *args, **kwargs):
            return response

    # Redirect raw-data output to a temporary directory.
    monkeypatch.setattr(acquisition, "RAW_DATA_DIR", tmp_path)

    # Confirm that malformed responses raise a ValueError.
    with pytest.raises(ValueError):
        acquisition.download_ticker_data(
            MockSession(),
            "TEST",
            "dummy-test-key",
        )

    # Confirm that malformed data was not written to disk.
    assert list(tmp_path.iterdir()) == []

# Test that invalid dates are rejected before raw data is written.
def test_invalid_date_does_not_write_raw_data(tmp_path, monkeypatch):
    """Invalid dates should be rejected before writing raw data."""

    # Create a successful HTTP response with an invalid date.
    response = requests.Response()
    response.status_code = 200
    response.url = "https://api.tiingo.com/tiingo/daily/TEST/prices"

    # Supply a structurally valid response containing an invalid date.
    payload = [
        {
            "date": "not-a-valid-date",
            "open": 10.0,
            "close": 11.0,
        }
    ]
    response.json = lambda: payload

    # Create a session that returns the synthetic response.
    class MockSession:
        def get(self, *args, **kwargs):
            return response

    # Redirect raw-data output to a temporary directory.
    monkeypatch.setattr(acquisition, "RAW_DATA_DIR", tmp_path)

    # Confirm that invalid dates raise a parsing error.
    with pytest.raises((ValueError, TypeError)):
        acquisition.download_ticker_data(
            MockSession(),
            "TEST",
            "dummy-test-key",
        )

    # Confirm that no raw data file was created.
    assert list(tmp_path.iterdir()) == []


# Test that invalid responses do not overwrite existing raw data.
def test_invalid_response_preserves_existing_raw_file(
    tmp_path,
    monkeypatch,
):
    """An invalid response must not overwrite an existing raw file."""

    # Create a raw-data file containing previously saved data.
    existing_file = tmp_path / "test_daily_raw.json"
    original_content = '[{"date": "2020-01-02", "close": 10.0}]'
    existing_file.write_text(original_content, encoding="utf-8")

    # Create a successful HTTP response with a missing date field.
    response = requests.Response()
    response.status_code = 200
    response.url = "https://api.tiingo.com/tiingo/daily/TEST/prices"
    payload = [{"open": 10.0, "close": 11.0}]
    response.json = lambda: payload

    # Create a session that returns the synthetic response.
    class MockSession:
        def get(self, *args, **kwargs):
            return response

    # Redirect raw-data output to the temporary directory.
    monkeypatch.setattr(acquisition, "RAW_DATA_DIR", tmp_path)

    # Confirm that the invalid response is rejected.
    with pytest.raises(ValueError):
        acquisition.download_ticker_data(
            MockSession(),
            "TEST",
            "dummy-test-key",
        )

    # Confirm that the original file remains unchanged.
    assert existing_file.read_text(encoding="utf-8") == original_content

# Test that main exits safely when the API key is missing.
def test_main_exits_when_api_key_is_missing(tmp_path, monkeypatch):
    """Missing credentials should stop the workflow before any requests."""

    # Redirect all output directories to temporary locations.
    monkeypatch.setattr(acquisition, "RAW_DATA_DIR", tmp_path / "raw")
    monkeypatch.setattr(acquisition, "PROCESSED_DATA_DIR", tmp_path / "processed")
    monkeypatch.setattr(acquisition, "REPORT_DIR", tmp_path / "reports")

    # Simulate missing API credentials.
    def raise_missing_api_key():
        raise RuntimeError("TIINGO_API_KEY is not configured.")

    monkeypatch.setattr(acquisition, "get_tiingo_api_key", raise_missing_api_key)

    # Make any attempt to create an HTTP session fail the test.
    def unexpected_session_creation():
        pytest.fail("An HTTP session must not be created without an API key.")

    monkeypatch.setattr(acquisition, "create_http_session", unexpected_session_creation)

    # Run the main workflow.
    exit_code = acquisition.main()

    # Confirm that the workflow exits with the expected error status.
    assert exit_code == 2

    # Confirm that no output directories were created.
    assert not (tmp_path / "raw").exists()
    assert not (tmp_path / "processed").exists()
    assert not (tmp_path / "reports").exists()

# Test that a failed download preserves the existing consolidated dataset.
def test_main_preserves_dataset_when_download_fails(tmp_path, monkeypatch):
    """A failed ticker download must not replace the existing CSV."""

    # Redirect all output directories to temporary locations.
    monkeypatch.setattr(acquisition, "RAW_DATA_DIR", tmp_path / "raw")
    monkeypatch.setattr(acquisition, "PROCESSED_DATA_DIR", tmp_path / "processed")
    monkeypatch.setattr(acquisition, "REPORT_DIR", tmp_path / "reports")

    # Create the temporary output directories.
    acquisition.create_output_directories()

    # Create an existing consolidated dataset.
    existing_csv = tmp_path / "processed" / "candidate_stocks_daily.csv"
    original_content = "ticker,date,close\nTEST,2020-01-02,10.0\n"
    existing_csv.write_text(original_content, encoding="utf-8")

    # Supply a synthetic API key.
    monkeypatch.setattr(
        acquisition,
        "get_tiingo_api_key",
        lambda: "dummy-test-key",
    )

    # Simulate an HTTP session without network access.
    class MockSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    # Replace session creation to prevent real network access.
    monkeypatch.setattr(
        acquisition,
        "create_http_session",
        lambda: MockSession(),
    )

    # Simulate a download failure for every requested ticker.
    def fail_download(session, ticker, api_key):
        raise requests.ConnectionError("Simulated connection failure")

    monkeypatch.setattr(
        acquisition,
        "download_ticker_data",
        fail_download,
    )

    # Run the main workflow.
    exit_code = acquisition.main()

    # Confirm that the workflow reports failure.
    assert exit_code == 1

    # Confirm that the existing consolidated dataset is unchanged.
    assert existing_csv.read_text(encoding="utf-8") == original_content

    # Confirm that no replacement CSV was left behind.
    assert not existing_csv.with_suffix(".csv.tmp").exists()

# Test that failed data validation preserves the existing consolidated dataset.
def test_main_preserves_dataset_when_validation_fails(
    tmp_path,
    monkeypatch,
    valid_market_data,
):
    """Failed validation must not replace the existing consolidated CSV."""

    # Redirect all output directories to temporary locations.
    monkeypatch.setattr(acquisition, "RAW_DATA_DIR", tmp_path / "raw")
    monkeypatch.setattr(acquisition, "PROCESSED_DATA_DIR", tmp_path / "processed")
    monkeypatch.setattr(acquisition, "REPORT_DIR", tmp_path / "reports")

    # Create the temporary output directories.
    acquisition.create_output_directories()

    # Create an existing consolidated dataset.
    existing_csv = tmp_path / "processed" / "candidate_stocks_daily.csv"
    original_content = "ticker,date,close\nTEST,2020-01-02,10.0\n"
    existing_csv.write_text(original_content, encoding="utf-8")

    # Supply a synthetic API key.
    monkeypatch.setattr(
        acquisition,
        "get_tiingo_api_key",
        lambda: "dummy-test-key",
    )

    # Provide a mock HTTP session that never makes network requests.
    class MockSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        acquisition,
        "create_http_session",
        lambda: MockSession(),
    )

    # Prepare a valid observation for each ticker.
    def provide_market_data(session, ticker, api_key):
        data = valid_market_data.copy()
        data["ticker"] = ticker

        # Return data with an intentionally invalid closing price for AAPL.
        if ticker == "AAPL":
            data["close"] = 0.0

        # Return the synthetic data and acquisition metadata.
        raw_path = tmp_path / "raw" / f"{ticker.lower()}_daily_raw.json"
        return data, raw_path, 200

    monkeypatch.setattr(
        acquisition,
        "download_ticker_data",
        provide_market_data,
    )

    # Run the main workflow.
    exit_code = acquisition.main()

    # Confirm that the workflow reports failure.
    assert exit_code == 1

    # Confirm that the existing consolidated dataset is unchanged.
    assert existing_csv.read_text(encoding="utf-8") == original_content

# Test that inconsistent trading dates prevent dataset publication.
def test_main_preserves_dataset_when_trading_dates_differ(
    tmp_path,
    monkeypatch,
    valid_market_data,
):
    """Different trading-date sets must prevent CSV publication."""

    # Redirect output directories to temporary locations.
    monkeypatch.setattr(acquisition, "RAW_DATA_DIR", tmp_path / "raw")
    monkeypatch.setattr(acquisition, "PROCESSED_DATA_DIR", tmp_path / "processed")
    monkeypatch.setattr(acquisition, "REPORT_DIR", tmp_path / "reports")

    # Create the temporary output directories.
    acquisition.create_output_directories()

    # Create an existing consolidated dataset.
    existing_csv = tmp_path / "processed" / "candidate_stocks_daily.csv"
    original_content = "ticker,date,close\nTEST,2020-01-02,10.0\n"
    existing_csv.write_text(original_content, encoding="utf-8")

    # Supply a synthetic API key.
    monkeypatch.setattr(
        acquisition,
        "get_tiingo_api_key",
        lambda: "dummy-test-key",
    )

    # Provide a mock session that cannot make network requests.
    class MockSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        acquisition,
        "create_http_session",
        lambda: MockSession(),
    )

    # Return valid observations with different dates for one ticker.
    def provide_market_data(session, ticker, api_key):
        data = valid_market_data.copy()

        # Give TSLA a different trading date.
        if ticker == "TSLA":
            data["date"] = pd.Timestamp("2020-01-03", tz="UTC")

        # Add the ticker identifier.
        data["ticker"] = ticker

        # Return the synthetic observations and metadata.
        raw_path = tmp_path / "raw" / f"{ticker.lower()}_daily_raw.json"
        return data, raw_path, 200

    monkeypatch.setattr(
        acquisition,
        "download_ticker_data",
        provide_market_data,
    )

    # Run the main workflow.
    exit_code = acquisition.main()

    # Confirm that inconsistent dates prevent publication.
    assert exit_code == 1

    # Confirm that the existing consolidated dataset is unchanged.
    assert existing_csv.read_text(encoding="utf-8") == original_content

# Test that a failed CSV replacement preserves the dataset and generates a report.
def test_main_preserves_dataset_when_csv_replacement_fails(
    tmp_path,
    monkeypatch,
    valid_market_data,
):
    """A failed CSV replacement must preserve the dataset and report the failure."""

    # Redirect output directories to temporary locations.
    monkeypatch.setattr(acquisition, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(acquisition, "RAW_DATA_DIR", tmp_path / "data" / "raw" / "tiingo")
    monkeypatch.setattr(acquisition, "PROCESSED_DATA_DIR", tmp_path / "data" / "processed")
    monkeypatch.setattr(acquisition, "REPORT_DIR", tmp_path / "reports")

    # Create the temporary output directories.
    acquisition.create_output_directories()

    # Create an existing consolidated dataset.
    existing_csv = tmp_path / "data" / "processed" / "candidate_stocks_daily.csv"
    original_content = "ticker,date,close\nTEST,2020-01-02,10.0\n"
    existing_csv.write_text(original_content, encoding="utf-8")

    # Supply a synthetic API key.
    monkeypatch.setattr(
        acquisition,
        "get_tiingo_api_key",
        lambda: "dummy-test-key",
    )

    # Provide a mock session that cannot make network requests.
    class MockSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        acquisition,
        "create_http_session",
        lambda: MockSession(),
    )

    # Return valid synthetic observations for every ticker.
    def provide_market_data(session, ticker, api_key):
        data = valid_market_data.copy()
        data["ticker"] = ticker

        # Return a raw-data path inside the temporary project directory.
        raw_path = (
            tmp_path
            / "data"
            / "raw"
            / "tiingo"
            / f"{ticker.lower()}_daily_raw.json"
        )

        # Return the synthetic data and acquisition metadata.
        return data, raw_path, 200

    monkeypatch.setattr(
        acquisition,
        "download_ticker_data",
        provide_market_data,
    )

    # Simulate a failure when replacing the consolidated CSV.
    original_replace = acquisition.Path.replace

    def fail_csv_replacement(path, target):
        if str(path).endswith(".csv.tmp"):
            raise OSError("Simulated CSV replacement failure")

        return original_replace(path, target)

    monkeypatch.setattr(acquisition.Path, "replace", fail_csv_replacement)

    # Run the workflow and expect a non-zero exit code instead of an exception.
    exit_code = acquisition.main()

    # Confirm that publication failure is reported as a workflow failure.
    assert exit_code == 1

    # Confirm that the existing consolidated dataset remains unchanged.
    assert existing_csv.read_text(encoding="utf-8") == original_content

    # Confirm that the temporary CSV has been removed.
    temporary_csv = existing_csv.with_suffix(".csv.tmp")
    assert not temporary_csv.exists()

    # Confirm that the data-quality report was generated.
    report_path = tmp_path / "reports" / "tiingo_data_quality_report.json"
    assert report_path.exists()

    # Load the report for verification.
    import json

    report = json.loads(report_path.read_text(encoding="utf-8"))

    # Confirm that the report records the unsuccessful publication.
    assert report["consolidated_dataset_saved"] is False
    assert report["consolidated_dataset_path"] is None

# Test that successful validation publishes the consolidated dataset.
def test_main_publishes_dataset_when_all_checks_pass(
    tmp_path,
    monkeypatch,
    valid_market_data,
):
    """All valid ticker datasets with matching dates should be published."""

    # Redirect output directories to temporary locations.
    monkeypatch.setattr(acquisition, "RAW_DATA_DIR", tmp_path / "raw")
    monkeypatch.setattr(acquisition, "PROCESSED_DATA_DIR", tmp_path / "processed")
    monkeypatch.setattr(acquisition, "REPORT_DIR", tmp_path / "reports")

    # Use the temporary directory as the project root for this test.
    monkeypatch.setattr(acquisition, "PROJECT_ROOT", tmp_path)

    # Create the temporary output directories.
    acquisition.create_output_directories()

    # Supply a synthetic API key.
    monkeypatch.setattr(
        acquisition,
        "get_tiingo_api_key",
        lambda: "dummy-test-key",
    )

    # Provide a mock session that cannot make network requests.
    class MockSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        acquisition,
        "create_http_session",
        lambda: MockSession(),
    )

    # Return one valid synthetic observation for each ticker.
    def provide_market_data(session, ticker, api_key):
        data = valid_market_data.copy()
        data["ticker"] = ticker

        # Use a project-relative path for workflow metadata.
        raw_path = (
            acquisition.PROJECT_ROOT
            / "data"
            / "raw"
            / "tiingo"
            / f"{ticker.lower()}_daily_raw.json"
        )

        return data, raw_path, 200

    monkeypatch.setattr(
        acquisition,
        "download_ticker_data",
        provide_market_data,
    )

    # Run the main workflow.
    exit_code = acquisition.main()

    # Confirm that the workflow reports success.
    assert exit_code == 0

    # Confirm that the consolidated CSV was published.
    output_csv = tmp_path / "processed" / "candidate_stocks_daily.csv"
    assert output_csv.exists()

    # Load the published dataset for verification.
    published_data = pd.read_csv(output_csv)

    # Confirm that all four tickers are represented.
    expected_tickers = acquisition.TICKERS
    assert sorted(published_data["ticker"].unique()) == sorted(expected_tickers)

    # Confirm that exactly one observation was published per ticker.
    assert len(published_data) == len(expected_tickers)

    # Confirm that the temporary CSV was removed.
    assert not output_csv.with_suffix(".csv.tmp").exists()

    # Load and verify the data-quality report.
    report_path = tmp_path / "reports" / "tiingo_data_quality_report.json"
    assert report_path.exists()

    import json

    report = json.loads(report_path.read_text(encoding="utf-8"))

    # Confirm that the report records successful publication.
    assert report["all_downloads_completed"] is True
    assert report["all_tickers_passed_validation"] is True
    assert report["date_sets_identical"] is True
    assert report["consolidated_dataset_saved"] is True

def test_main_preserves_success_when_temporary_csv_cleanup_fails(
tmp_path,
monkeypatch,
valid_market_data,
capsys,
):
    """A cleanup failure must not invalidate successful CSV publication."""

    import json

    # Redirect output directories to temporary locations.
    monkeypatch.setattr(acquisition, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        acquisition,
        "RAW_DATA_DIR",
        tmp_path / "data" / "raw" / "tiingo",
    )
    monkeypatch.setattr(
        acquisition,
        "PROCESSED_DATA_DIR",
        tmp_path / "data" / "processed",
    )
    monkeypatch.setattr(
        acquisition,
        "REPORT_DIR",
        tmp_path / "reports",
    )

    # Create the temporary output directories.
    acquisition.create_output_directories()

    # Supply a synthetic API key.
    monkeypatch.setattr(
        acquisition,
        "get_tiingo_api_key",
        lambda: "dummy-test-key",
    )

    # Provide a mock session that cannot make network requests.
    class MockSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        acquisition,
        "create_http_session",
        lambda: MockSession(),
    )

    # Return valid synthetic observations for every ticker.
    def provide_market_data(session, ticker, api_key):
        data = valid_market_data.copy()
        data["ticker"] = ticker

        raw_path = (
            tmp_path
            / "data"
            / "raw"
            / "tiingo"
            / f"{ticker.lower()}_daily_raw.json"
        )

        return data, raw_path, 200

    monkeypatch.setattr(
        acquisition,
        "download_ticker_data",
        provide_market_data,
    )

    # Simulate a cleanup failure for the temporary CSV only.
    original_unlink = acquisition.Path.unlink

    def fail_temporary_csv_cleanup(path, *args, **kwargs):
        if str(path).endswith(".csv.tmp"):
            raise OSError("Simulated temporary CSV cleanup failure")

        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(
        acquisition.Path,
        "unlink",
        fail_temporary_csv_cleanup,
    )

    # Run the workflow.
    exit_code = acquisition.main()

    # Confirm that successful publication remains successful.
    assert exit_code == 0

    output_csv = (
        tmp_path
        / "data"
        / "processed"
        / "candidate_stocks_daily.csv"
    )
    assert output_csv.exists()

    # Confirm that the report records successful publication.
    report_path = (
        tmp_path
        / "reports"
        / "tiingo_data_quality_report.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["consolidated_dataset_saved"] is True
    assert report["consolidated_dataset_path"] is not None
    assert report["publication_error"] is None

    # Confirm that the cleanup warning is reported to standard error.
    captured = capsys.readouterr()
    assert "Temporary CSV cleanup failed (OSError)." in captured.err