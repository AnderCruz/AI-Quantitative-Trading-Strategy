# Import environment and path utilities.
from pathlib import Path
from typing import Any

# Import YAML parsing and dotenv support.
import yaml
from dotenv import load_dotenv


# Define the project root directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Define the path to the project configuration file.
ASSET_CONFIG_PATH = PROJECT_ROOT / "config" / "asset_config.yaml"

# Load environment variables from the project-root .env file if present.
# Existing environment variables are not overwritten by default.
load_dotenv(PROJECT_ROOT / ".env")


def load_asset_config(config_path: Path | str = ASSET_CONFIG_PATH) -> dict[str, Any]:
    """Load and validate the asset configuration from a YAML file."""

    # Convert the supplied path to a Path object.
    path = Path(config_path)

    # Fail clearly if the configuration file does not exist.
    if not path.is_file():
        raise FileNotFoundError(
            f"Asset configuration file was not found: {path}"
        )

    # Read and parse the YAML configuration.
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # Ensure the YAML document contains a mapping.
    if not isinstance(config, dict):
        raise ValueError("The asset configuration must be a YAML mapping.")

    # Check the required configuration sections.
    required_sections = {
        "asset",
        "data",
        "forecasting",
        "models",
        "evaluation",
        "portfolio",
    }

    missing_sections = required_sections.difference(config)

    if missing_sections:
        missing = ", ".join(sorted(missing_sections))
        raise ValueError(
            f"Missing required configuration sections: {missing}"
        )

    # Validate the asset configuration.
    asset = config["asset"]

    if not isinstance(asset, dict):
        raise ValueError("'asset' must be a mapping.")

    for field in ("ticker", "exchange", "country", "currency"):
        value = asset.get(field)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"'asset.{field}' must be a non-empty string."
            )

    # Validate the historical data configuration.
    data = config["data"]

    if not isinstance(data, dict):
        raise ValueError("'data' must be a mapping.")

    if data.get("provider") != "yfinance":
        raise ValueError(
            "'data.provider' must be 'yfinance' for this configuration."
        )

    if not isinstance(data.get("start_date"), str) or not data["start_date"]:
        raise ValueError("'data.start_date' must be a non-empty string.")

    if not isinstance(data.get("end_date"), str) or not data["end_date"]:
        raise ValueError("'data.end_date' must be a non-empty string.")

    # Validate the forecasting horizons.
    forecasting = config["forecasting"]

    if not isinstance(forecasting, dict):
        raise ValueError("'forecasting' must be a mapping.")

    horizons = forecasting.get("horizons")

    if (
        not isinstance(horizons, list)
        or not horizons
        or any(type(horizon) is not int or horizon <= 0 for horizon in horizons)
    ):
        raise ValueError(
            "'forecasting.horizons' must be a non-empty list of positive integers."
        )

    # Validate the evaluation configuration.
    evaluation = config["evaluation"]

    if not isinstance(evaluation, dict):
        raise ValueError("'evaluation' must be a mapping.")

    if evaluation.get("method") != "walk_forward":
        raise ValueError(
            "'evaluation.method' must be 'walk_forward'."
        )

    if evaluation.get("prevent_data_leakage") is not True:
        raise ValueError(
            "'evaluation.prevent_data_leakage' must be true."
        )

    # Validate the initial portfolio capital.
    portfolio = config["portfolio"]

    if not isinstance(portfolio, dict):
        raise ValueError("'portfolio' must be a mapping.")

    capital = portfolio.get("initial_capital")

    if (
        isinstance(capital, bool)
        or not isinstance(capital, (int, float))
        or capital <= 0
    ):
        raise ValueError(
            "'portfolio.initial_capital' must be a positive number."
        )

    currency = portfolio.get("currency")

    if not isinstance(currency, str) or not currency.strip():
        raise ValueError(
            "'portfolio.currency' must be a non-empty string."
        )

    # Return the validated configuration.
    return config
