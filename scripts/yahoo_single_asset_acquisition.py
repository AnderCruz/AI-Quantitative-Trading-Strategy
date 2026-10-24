"""Acquire and validate daily data for the configured asset."""

# Import standard library modules.
import logging
import sys
from pathlib import Path

# Define the project root before importing local project modules.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Add the project root to the module search path for direct script execution.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import third-party libraries.
import pandas as pd
import yfinance as yf

# Import the central configuration loader.
from src.config import load_asset_config


# Define project paths.
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "yahoo" / "configured"

# Define the required market-data columns.
PRICE_COLUMNS = ("Open", "High", "Low", "Close", "Adj Close", "Volume")
ACTION_COLUMNS = ("Dividends", "Stock Splits")

# Configure logging.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def download_asset_data(config: dict) -> pd.DataFrame:
    """Download daily market data using the central asset configuration."""

    # Read acquisition parameters from the validated configuration.
    asset = config["asset"]
    data_config = config["data"]

    ticker = asset["ticker"].strip().upper()
    start_date = data_config["start_date"]
    end_date = data_config["end_date"]
    interval = data_config["interval"]

    # Request market data without automatic price adjustment.
    data = yf.download(
        ticker,
        start=start_date,
        end=end_date,
        interval=interval,
        auto_adjust=False,
        actions=True,
        repair=False,
        keepna=True,
        progress=False,
        threads=False,
        timeout=30,
        multi_level_index=False,
    )

    # Reject empty responses.
    if data.empty:
        raise RuntimeError(f"No historical data returned for {ticker}.")

    # Flatten multi-level columns if returned by the provider.
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [
            "_".join(
                str(part)
                for part in column
                if part not in ("", ticker)
            )
            for column in data.columns
        ]

    # Check that all expected price columns are available.
    missing_columns = [
        column for column in PRICE_COLUMNS
        if column not in data.columns
    ]

    if missing_columns:
        raise RuntimeError(
            f"{ticker}: missing required columns: {missing_columns}"
        )

    # Add corporate-action columns if they are absent.
    for column in ACTION_COLUMNS:
        if column not in data.columns:
            data[column] = 0.0

    # Normalise the date index and create an explicit date column.
    data.index = pd.to_datetime(data.index, utc=True)
    data.index.name = "date"
    data = data.reset_index()
    data["ticker"] = ticker

    # Select a consistent output column order.
    columns = [
        "date",
        "Open",
        "High",
        "Low",
        "Close",
        "Adj Close",
        "Volume",
        "Dividends",
        "Stock Splits",
        "ticker",
    ]

    result = data[columns].copy()

    # Validate the downloaded observations before returning them.
    validate_asset_data(
        result,
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
    )

    return result


def validate_asset_data(
    data: pd.DataFrame,
    ticker: str,
    start_date: str,
    end_date: str,
) -> None:
    """Validate dates, prices, volume and corporate-action fields."""

    # Reject empty datasets.
    if data.empty:
        raise ValueError("The downloaded dataset is empty.")

    # Confirm that all rows belong to the requested asset.
    if data["ticker"].nunique() != 1 or data["ticker"].iloc[0] != ticker:
        raise ValueError(f"{ticker}: inconsistent ticker identifiers.")

    # Reject duplicate dates and unordered observations.
    if data["date"].duplicated().any():
        raise ValueError(f"{ticker}: duplicate dates detected.")

    if not data["date"].is_monotonic_increasing:
        raise ValueError(f"{ticker}: dates are not chronologically ordered.")

    # Enforce the configured start date and exclusive end date.
    dates = data["date"]

    if dates.min() < pd.Timestamp(start_date, tz="UTC"):
        raise ValueError(f"{ticker}: data begins before the requested period.")

    if dates.max() >= pd.Timestamp(end_date, tz="UTC"):
        raise ValueError(f"{ticker}: data extends beyond the requested period.")

    # Reject missing values in required market-data fields.
    if data[list(PRICE_COLUMNS)].isna().any().any():
        raise ValueError(f"{ticker}: missing values in required price fields.")

    # Reject non-positive prices and negative trading volume.
    price_columns = ("Open", "High", "Low", "Close", "Adj Close")

    if (data[list(price_columns)] <= 0).any().any():
        raise ValueError(f"{ticker}: non-positive prices detected.")

    if (data["Volume"] < 0).any():
        raise ValueError(f"{ticker}: negative volume detected.")

    # Check consistency of daily price ranges.
    if (data["High"] < data["Low"]).any():
        raise ValueError(f"{ticker}: High is below Low.")

    # Document the two approved historical OHLC exceptions.
    known_ohlc_exceptions = {
        pd.Timestamp("2015-03-31", tz="UTC"),
        pd.Timestamp("2024-05-01", tz="UTC"),
    }

    # Identify closing prices outside the daily High-Low range.
    invalid_close = (
        (data["Close"] > data["High"])
        | (data["Close"] < data["Low"])
    )

    # Preserve the original values and log known exceptions.
    exception_rows = data.loc[
        invalid_close & data["date"].isin(known_ohlc_exceptions)
    ]

    for _, row in exception_rows.iterrows():
        logger.warning(
            "%s: preserving known OHLC inconsistency on %s "
            "(Low=%.6f, High=%.6f, Close=%.6f).",
            ticker,
            row["date"].date(),
            row["Low"],
            row["High"],
            row["Close"],
        )

    # Reject OHLC inconsistencies on all other dates.
    unexpected_invalid = invalid_close & ~data["date"].isin(
        known_ohlc_exceptions
    )

    if unexpected_invalid.any():
        invalid_dates = data.loc[unexpected_invalid, "date"].dt.strftime(
            "%Y-%m-%d"
        ).tolist()

        raise ValueError(
            f"{ticker}: Close is outside the High-Low range "
            f"on unexpected dates: {invalid_dates}"
        )

    # Reject invalid corporate-action values.
    if (data[list(ACTION_COLUMNS)] < 0).any().any():
        raise ValueError(f"{ticker}: negative corporate-action values detected.")


def main() -> int:
    """Acquire, validate and safely save the configured asset."""

    # Load the central project configuration.
    config = load_asset_config()

    # Construct a separate output path to protect historical datasets.
    ticker = config["asset"]["ticker"].strip().upper()
    output_path = OUTPUT_DIR / f"{ticker}.csv"

    # Never overwrite an existing file.
    if output_path.exists():
        logger.error(
            "Output already exists. Refusing to overwrite: %s",
            output_path,
        )
        return 1

    # Download and validate the configured asset.
    logger.info("Starting acquisition for %s.", ticker)
    result = download_asset_data(config)

    # Create the output directory only after validation succeeds.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Recheck the destination immediately before writing.
    if output_path.exists():
        logger.error(
            "Output appeared during acquisition. Refusing to overwrite: %s",
            output_path,
        )
        return 1

    # Write to a temporary file before publishing the result.
    temporary_path = output_path.with_suffix(".csv.tmp")

    try:
        if temporary_path.exists():
            raise FileExistsError(
                f"Temporary output already exists: {temporary_path}"
            )

        result.to_csv(temporary_path, index=False)

        # Recheck the final destination before publishing.
        if output_path.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing output: {output_path}"
            )

        temporary_path.replace(output_path)

    finally:
        # Remove a temporary file if publication did not complete.
        temporary_path.unlink(missing_ok=True)

    # Report the completed acquisition.
    logger.info("Saved %s observations to %s.", len(result), output_path)
    logger.info(
        "Date coverage: %s to %s.",
        result["date"].min(),
        result["date"].max(),
    )

    return 0


if __name__ == "__main__":
    # Execute acquisition only when this script is run directly.
    raise SystemExit(main())
