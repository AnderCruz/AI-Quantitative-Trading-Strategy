# Import JSON-compatible configuration utilities.
from copy import deepcopy

# Import the YAML parser.
import yaml

# Import pytest for automated testing.
import pytest

# Import the configuration module.
from src.config import (
    ASSET_CONFIG_PATH,
    load_asset_config,
)


def test_default_configuration_loads_successfully():
    """Verify that the project's default configuration is valid."""

    # Load the project configuration.
    config = load_asset_config()

    # Check the configured pilot asset.
    assert config["asset"]["ticker"] == "LLOY.L"
    assert config["asset"]["exchange"] == "LSE"
    assert config["asset"]["country"] == "UK"
    assert config["asset"]["currency"] == "GBP"

    # Check the data source and forecasting horizons.
    assert config["data"]["provider"] == "yfinance"
    assert config["forecasting"]["horizons"] == [1, 5, 10]

    # Check the evaluation and portfolio settings.
    assert config["evaluation"]["method"] == "walk_forward"
    assert config["evaluation"]["prevent_data_leakage"] is True
    assert config["portfolio"]["initial_capital"] == 1000
    assert config["portfolio"]["currency"] == "GBP"


def test_configuration_file_exists():
    """Verify that the default configuration file exists."""

    # Check the default configuration path.
    assert ASSET_CONFIG_PATH.is_file()


def test_missing_configuration_file_raises_error(tmp_path):
    """Verify that a missing configuration file raises an error."""

    # Define a path that does not exist.
    missing_path = tmp_path / "missing_config.yaml"

    # Confirm that loading the missing file fails clearly.
    with pytest.raises(FileNotFoundError):
        load_asset_config(missing_path)


def test_empty_yaml_configuration_raises_error(tmp_path):
    """Verify that an empty YAML document is rejected."""

    # Create an empty YAML file.
    config_path = tmp_path / "empty_config.yaml"
    config_path.write_text("", encoding="utf-8")

    # Confirm that an empty configuration is rejected.
    with pytest.raises(ValueError, match="YAML mapping"):
        load_asset_config(config_path)


def test_missing_required_section_raises_error(tmp_path):
    """Verify that required configuration sections are checked."""

    # Create a configuration missing required sections.
    config_path = tmp_path / "incomplete_config.yaml"
    config_path.write_text(
        yaml.safe_dump({"asset": {}}),
        encoding="utf-8",
    )

    # Confirm that missing sections are reported.
    with pytest.raises(ValueError, match="Missing required configuration sections"):
        load_asset_config(config_path)


def test_empty_ticker_raises_error(tmp_path):
    """Verify that an empty ticker is rejected."""

    # Load the valid configuration.
    config = deepcopy(load_asset_config())

    # Replace the ticker with an invalid value.
    config["asset"]["ticker"] = " "

    # Write the modified configuration to a temporary file.
    config_path = tmp_path / "invalid_ticker.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    # Confirm that the invalid ticker is rejected.
    with pytest.raises(ValueError, match="asset.ticker"):
        load_asset_config(config_path)


def test_unsupported_data_provider_raises_error(tmp_path):
    """Verify that an unsupported data provider is rejected."""

    # Load the valid configuration.
    config = deepcopy(load_asset_config())

    # Set an unsupported data provider.
    config["data"]["provider"] = "unsupported_provider"

    # Write the modified configuration.
    config_path = tmp_path / "invalid_provider.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    # Confirm that the unsupported provider is rejected.
    with pytest.raises(ValueError, match="data.provider"):
        load_asset_config(config_path)


def test_invalid_forecasting_horizons_raise_error(tmp_path):
    """Verify that invalid forecasting horizons are rejected."""

    # Load the valid configuration.
    config = deepcopy(load_asset_config())

    # Include a zero-length forecasting horizon.
    config["forecasting"]["horizons"] = [1, 0, 5]

    # Write the modified configuration.
    config_path = tmp_path / "invalid_horizons.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    # Confirm that invalid horizons are rejected.
    with pytest.raises(ValueError, match="forecasting.horizons"):
        load_asset_config(config_path)


def test_data_leakage_protection_must_be_enabled(tmp_path):
    """Verify that data leakage protection cannot be disabled."""

    # Load the valid configuration.
    config = deepcopy(load_asset_config())

    # Disable the data leakage safeguard.
    config["evaluation"]["prevent_data_leakage"] = False

    # Write the modified configuration.
    config_path = tmp_path / "data_leakage_disabled.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    # Confirm that the invalid setting is rejected.
    with pytest.raises(ValueError, match="prevent_data_leakage"):
        load_asset_config(config_path)


def test_non_positive_initial_capital_raises_error(tmp_path):
    """Verify that non-positive initial capital is rejected."""

    # Load the valid configuration.
    config = deepcopy(load_asset_config())

    # Set an invalid initial capital.
    config["portfolio"]["initial_capital"] = 0

    # Write the modified configuration.
    config_path = tmp_path / "invalid_capital.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    # Confirm that the invalid capital is rejected.
    with pytest.raises(ValueError, match="initial_capital"):
        load_asset_config(config_path)
