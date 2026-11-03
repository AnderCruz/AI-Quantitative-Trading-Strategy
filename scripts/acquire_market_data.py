"""Acquire historical market data from Yahoo Finance."""

import argparse
import hashlib
import json
import logging
import platform
import shutil
import uuid
import warnings as warning_module

from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Literal

import pandas as pd
import yaml
import yfinance as yf

from pydantic import BaseModel, ConfigDict, Field, ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_ROOT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "market"
    / "yahoo_finance"
)

CONFIG_ROOT = PROJECT_ROOT / "configs" / "assets"

BASE_REQUIRED_COLUMNS = [
    "Open",
    "High",
    "Low",
    "Close",
]

EQUITY_REQUIRED_COLUMNS = [
    "Volume",
]


class AssetConfiguration(BaseModel):
    """Validate asset-specific configuration."""

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1)
    name: str = Field(min_length=1)
    instrument_type: Literal["equity", "index"]
    exchange: str = Field(min_length=1)
    currency: str = Field(min_length=1)
    sector: str | None = None
    market_timezone: str = Field(min_length=1)


class ProviderConfiguration(BaseModel):
    """Validate provider configuration."""

    model_config = ConfigDict(extra="forbid")

    name: Literal["yahoo_finance"]
    symbol: str = Field(min_length=1)


class AcquisitionConfiguration(BaseModel):
    """Validate acquisition parameters."""

    model_config = ConfigDict(extra="forbid")

    frequency: Literal["1d"]
    period: Literal["max"]
    auto_adjust: bool
    actions: bool
    repair: bool
    keepna: bool
    prepost: bool
    rounding: bool
    progress: bool
    threads: bool


class AssetConfig(BaseModel):
    """Validate the complete asset configuration."""

    model_config = ConfigDict(extra="forbid")

    asset: AssetConfiguration
    provider: ProviderConfiguration
    acquisition: AcquisitionConfiguration


def calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 checksum of a file."""

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            sha256.update(chunk)

    return sha256.hexdigest()


def load_asset_config(config_path: Path) -> tuple[AssetConfig, str]:
    """Load and validate an asset configuration."""

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    raw_config = config_path.read_bytes()

    config_hash = hashlib.sha256(raw_config).hexdigest()

    config_data = yaml.safe_load(
        raw_config.decode("utf-8")
    )

    validated_config = AssetConfig.model_validate(
        config_data
    )

    if (
        validated_config.asset.ticker
        != validated_config.provider.symbol
    ):
        raise ValueError(
            "Asset ticker and provider symbol do not match."
        )

    return validated_config, config_hash


def normalise_columns(
    data: pd.DataFrame,
    provider_symbol: str,
) -> pd.DataFrame:
    """Normalise simple and MultiIndex provider columns."""

    if not isinstance(data.columns, pd.MultiIndex):
        return data

    matching_levels = []

    for level in range(data.columns.nlevels):
        values = set(
            data.columns.get_level_values(level)
        )

        if provider_symbol in values:
            matching_levels.append(level)

    if matching_levels:
        selected_level = matching_levels[-1]

        data.columns = (
            data.columns.get_level_values(
                1 - selected_level
                if data.columns.nlevels == 2
                else 0
            )
            if data.columns.nlevels == 2
            else data.columns.get_level_values(0)
        )

    else:
        available_levels = [
            set(data.columns.get_level_values(level))
            for level in range(data.columns.nlevels)
        ]

        selected_level = next(
            (
                index
                for index, values in enumerate(available_levels)
                if "Open" in values
            ),
            None,
        )

        if selected_level is None:
            raise RuntimeError(
                "Unable to identify OHLC columns "
                "in the provider response."
            )

        data.columns = data.columns.get_level_values(
            selected_level
        )

    return data


def validate_market_data(
    data: pd.DataFrame,
    instrument_type: str,
) -> list[str]:
    """Validate the returned data structure."""

    warnings = []

    required_columns = list(BASE_REQUIRED_COLUMNS)

    if instrument_type == "equity":
        required_columns.extend(EQUITY_REQUIRED_COLUMNS)

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise RuntimeError(
            f"Missing required columns: {missing_columns}"
        )

    optional_columns = [
        "Adj Close",
        "Dividends",
        "Stock Splits",
    ]

    if instrument_type == "index":
        optional_columns.append("Volume")

    for column in optional_columns:
        if column not in data.columns:
            warnings.append(
                f"Optional column not returned: {column}"
            )

    if data.index.has_duplicates:
        warnings.append(
            "Duplicate observation dates detected."
        )

    if not data.index.is_monotonic_increasing:
        warnings.append(
            "Observation dates are not sorted."
        )

    if data.isna().all(axis=1).any():
        warnings.append(
            "Rows containing only missing values detected."
        )

    return warnings


def build_manifest(
    data: pd.DataFrame,
    config: AssetConfig,
    config_path: Path,
    config_hash: str,
    acquisition_id: str,
    retrieved_at: datetime,
    files: dict,
    warnings: list[str],
) -> dict:
    """Build acquisition metadata."""

    asset = config.asset
    provider = config.provider

    return {
        "acquisition_id": acquisition_id,
        "status": (
            "success_with_warnings"
            if warnings
            else "success"
        ),
        "provider": "Yahoo Finance",
        "provider_id": provider.name,
        "library": "yfinance",
        "ticker": asset.ticker,
        "asset_name": asset.name,
        "instrument_type": asset.instrument_type,
        "exchange": asset.exchange,
        "currency": asset.currency,
        "currency_status": "configured_assumption",
        "sector": asset.sector,
        "market_timezone": asset.market_timezone,
        "configuration": {
            "path": str(
                config_path.relative_to(PROJECT_ROOT)
            ),
            "sha256": config_hash,
        },
        "retrieved_at_utc": retrieved_at.isoformat(),
        "period_requested": config.acquisition.period,
        "frequency": config.acquisition.frequency,
        "source_representation": (
            "DataFrame returned by yfinance"
        ),
        "observation_start": str(data.index.min()),
        "observation_end": str(data.index.max()),
        "record_count": len(data),
        "columns": [
            str(column)
            for column in data.columns
        ],
        "index_timezone": str(
            getattr(data.index, "tz", None)
        ),
        "parameters": config.acquisition.model_dump(),
        "software_versions": {
            "python": platform.python_version(),
            "yfinance": version("yfinance"),
            "pandas": version("pandas"),
            "pyarrow": version("pyarrow"),
            "pydantic": version("pydantic"),
            "PyYAML": version("PyYAML"),
        },
        "files": files,
        "warnings": warnings,
        "licensing_note": (
            "Research and exploratory use only. "
            "Redistribution and commercial use require "
            "separate licensing assessment."
        ),
    }


def acquire_market_data(
    config_path: Path,
) -> Path:
    """Download and preserve historical market data."""

    config, config_hash = load_asset_config(config_path)

    asset = config.asset
    provider = config.provider
    acquisition = config.acquisition

    retrieved_at = datetime.now(timezone.utc)

    acquisition_id = (
        retrieved_at.strftime("%Y%m%dT%H%M%SZ")
        + "_"
        + uuid.uuid4().hex[:8]
    )

    asset_directory = RAW_ROOT / asset.ticker

    asset_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_directory = (
        asset_directory / f".temporary_{acquisition_id}"
    )

    final_directory = (
        asset_directory / f"acquisition_{acquisition_id}"
    )

    temporary_directory.mkdir()

    logging.info(
        "Starting acquisition for %s",
        asset.ticker,
    )

    logging.info(
        "Instrument type: %s",
        asset.instrument_type,
    )

    logging.info(
        "Acquisition ID: %s",
        acquisition_id,
    )

    try:
        with warning_module.catch_warnings(
            record=True
        ) as captured_warnings:

            warning_module.simplefilter("always")

            data = yf.download(
                tickers=provider.symbol,
                interval=acquisition.frequency,
                period=acquisition.period,
                auto_adjust=acquisition.auto_adjust,
                actions=acquisition.actions,
                repair=acquisition.repair,
                keepna=acquisition.keepna,
                prepost=acquisition.prepost,
                rounding=acquisition.rounding,
                progress=acquisition.progress,
                threads=acquisition.threads,
            )

        if data is None or data.empty:
            raise RuntimeError(
                f"No historical data returned for {asset.ticker}"
            )

        warnings = [
            (
                f"{item.category.__name__}: "
                f"{item.message}"
            )
            for item in captured_warnings
        ]

        data = normalise_columns(
            data,
            provider.symbol,
        )

        warnings.extend(
            validate_market_data(
                data,
                asset.instrument_type,
            )
        )

        csv_path = (
            temporary_directory / f"{asset.ticker}.csv"
        )

        parquet_path = (
            temporary_directory / f"{asset.ticker}.parquet"
        )

        data.to_csv(
            csv_path,
            index_label="Date",
        )

        data.to_parquet(
            parquet_path,
            index=True,
        )

        file_metadata = {}

        for file_path in [csv_path, parquet_path]:
            file_metadata[file_path.name] = {
                "size_bytes": file_path.stat().st_size,
                "sha256": calculate_sha256(file_path),
            }

        manifest = build_manifest(
            data=data,
            config=config,
            config_path=config_path,
            config_hash=config_hash,
            acquisition_id=acquisition_id,
            retrieved_at=retrieved_at,
            files=file_metadata,
            warnings=warnings,
        )

        manifest_path = (
            temporary_directory / "manifest.json"
        )

        with manifest_path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                manifest,
                file,
                indent=4,
                ensure_ascii=False,
            )

        temporary_directory.rename(
            final_directory
        )

        logging.info(
            "Acquisition completed for %s",
            asset.ticker,
        )

        logging.info(
            "Records: %s",
            len(data),
        )

        logging.info(
            "Output: %s",
            final_directory,
        )

        for warning in warnings:
            logging.warning(warning)

        return final_directory

    except Exception:
        if temporary_directory.exists():
            shutil.rmtree(temporary_directory)

        raise


def main():
    """Run the market data acquisition process."""

    parser = argparse.ArgumentParser(
        description=(
            "Acquire historical market data "
            "using an asset YAML configuration."
        )
    )

    parser.add_argument(
        "--config",
        required=True,
        help="Path to the asset YAML configuration.",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    config_path = Path(args.config)

    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    output_directory = acquire_market_data(
        config_path
    )

    print("\nAcquisition summary")
    print("-------------------")
    print(f"Configuration: {args.config}")
    print(f"Output: {output_directory}")


if __name__ == "__main__":
    main()