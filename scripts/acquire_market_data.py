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

import pandas as pd
import yfinance as yf


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_ROOT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "market"
    / "yahoo_finance"
)

PARAMETERS = {
    "period": "max",
    "interval": "1d",
    "auto_adjust": False,
    "actions": True,
    "repair": False,
    "keepna": True,
    "prepost": False,
    "rounding": False,
    "progress": False,
    "threads": False,
}

REQUIRED_COLUMNS = [
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
]


def calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 checksum of a file."""

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def normalise_columns(data: pd.DataFrame) -> pd.DataFrame:
    """Handle simple and MultiIndex column representations."""

    if isinstance(data.columns, pd.MultiIndex):
        if data.columns.nlevels > 1:
            data.columns = data.columns.get_level_values(0)

    return data


def acquire_market_data(ticker: str) -> Path:
    """Download and preserve historical market data."""

    retrieved_at = datetime.now(timezone.utc)

    acquisition_id = (
        retrieved_at.strftime("%Y%m%dT%H%M%SZ")
        + "_"
        + uuid.uuid4().hex[:8]
    )

    asset_directory = RAW_ROOT / ticker
    asset_directory.mkdir(parents=True, exist_ok=True)

    temporary_directory = (
        asset_directory / f".temporary_{acquisition_id}"
    )

    final_directory = (
        asset_directory / f"acquisition_{acquisition_id}"
    )

    temporary_directory.mkdir()

    logging.info("Starting acquisition for %s", ticker)
    logging.info("Acquisition ID: %s", acquisition_id)

    try:
        # Capture warnings emitted during the provider request.
        with warning_module.catch_warnings(
            record=True
        ) as captured_warnings:

            warning_module.simplefilter("always")

            data = yf.download(
                tickers=ticker,
                **PARAMETERS,
            )

        if data is None or data.empty:
            raise RuntimeError(
                f"No historical data returned for {ticker}"
            )

        warnings = [
            (
                f"{item.category.__name__}: "
                f"{item.message}"
            )
            for item in captured_warnings
        ]

        data = normalise_columns(data)

        missing_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in data.columns
        ]

        if missing_columns:
            raise RuntimeError(
                f"Missing required columns: {missing_columns}"
            )

        if "Adj Close" not in data.columns:
            warnings.append(
                "Adjusted Close column not returned."
            )

        if "Dividends" not in data.columns:
            warnings.append(
                "Dividends column not returned."
            )

        if "Stock Splits" not in data.columns:
            warnings.append(
                "Stock Splits column not returned."
            )

        if data.index.has_duplicates:
            warnings.append(
                "Duplicate observation dates detected."
            )

        if not data.index.is_monotonic_increasing:
            warnings.append(
                "Observation dates are not sorted."
            )

        csv_path = temporary_directory / f"{ticker}.csv"
        parquet_path = temporary_directory / f"{ticker}.parquet"

        data.to_csv(csv_path, index_label="Date")
        data.to_parquet(parquet_path, index=True)

        file_metadata = {}

        for file_path in [csv_path, parquet_path]:
            file_metadata[file_path.name] = {
                "size_bytes": file_path.stat().st_size,
                "sha256": calculate_sha256(file_path),
            }

        manifest = {
            "acquisition_id": acquisition_id,
            "status": (
                "success_with_warnings"
                if warnings
                else "success"
            ),
            "provider": "Yahoo Finance",
            "library": "yfinance",
            "ticker": ticker,
            "retrieved_at_utc": retrieved_at.isoformat(),
            "period_requested": PARAMETERS["period"],
            "frequency": PARAMETERS["interval"],
            "currency": "GBP",
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
            "parameters": PARAMETERS,
            "software_versions": {
                "python": platform.python_version(),
                "yfinance": version("yfinance"),
                "pandas": version("pandas"),
                "pyarrow": version("pyarrow"),
            },
            "files": file_metadata,
            "warnings": warnings,
            "licensing_note": (
                "Research and exploratory use only. "
                "Redistribution and commercial use require "
                "separate licensing assessment."
            ),
        }

        manifest_path = temporary_directory / "manifest.json"

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

        temporary_directory.rename(final_directory)

        logging.info("Acquisition completed.")
        logging.info("Records: %s", len(data))
        logging.info("Output: %s", final_directory)

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
        description="Acquire historical market data."
    )

    parser.add_argument(
        "--ticker",
        required=True,
        help="Yahoo Finance ticker symbol.",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    output_directory = acquire_market_data(args.ticker)

    print("\nAcquisition summary")
    print("-------------------")
    print(f"Ticker: {args.ticker}")
    print(f"Output: {output_directory}")


if __name__ == "__main__":
    main()