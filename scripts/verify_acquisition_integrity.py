"""Verify the integrity and consistency of historical market data acquisitions."""

import hashlib
import json
import logging
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ACQUISITIONS = {
    "SSE.L": (
        PROJECT_ROOT
        / "data/raw/market/yahoo_finance/SSE.L/"
        "acquisition_20261103T002507Z_de101edb"
    ),
    "SVT.L": (
        PROJECT_ROOT
        / "data/raw/market/yahoo_finance/SVT.L/"
        "acquisition_20261103T002515Z_fdac38df"
    ),
    "^FTSE": (
        PROJECT_ROOT
        / "data/raw/market/yahoo_finance/^FTSE/"
        "acquisition_20261103T002524Z_9c7eb120"
    ),
}

# Floating-point comparison tolerances
RELATIVE_TOLERANCE = 1e-10
ABSOLUTE_TOLERANCE = 1e-12

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------

def calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 checksum of a file."""

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def load_manifest(manifest_path: Path) -> dict:
    """Load an acquisition manifest."""

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Manifest not found: {manifest_path}"
        )

    with manifest_path.open(encoding="utf-8") as file:
        return json.load(file)


def verify_file_integrity(
    file_path: Path,
    manifest: dict,
) -> None:
    """Verify file existence, size and SHA-256 checksum."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    expected_metadata = manifest["files"].get(file_path.name)

    if expected_metadata is None:
        raise AssertionError(
            f"File metadata missing from manifest: {file_path.name}"
        )

    # Verify file size
    actual_size = file_path.stat().st_size
    expected_size = expected_metadata["size_bytes"]

    assert actual_size == expected_size, (
        f"File size mismatch for {file_path.name}: "
        f"expected {expected_size}, got {actual_size}"
    )

    # Verify SHA-256
    actual_hash = calculate_sha256(file_path)
    expected_hash = expected_metadata["sha256"]

    assert actual_hash == expected_hash, (
        f"SHA-256 mismatch for {file_path.name}"
    )

    print(
        f"{file_path.name}: SIZE OK | SHA-256 OK"
    )


def load_market_data(
    csv_path: Path,
    parquet_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load CSV and Parquet market data."""

    csv_data = pd.read_csv(
        csv_path,
        index_col=0,
        parse_dates=True,
    )

    parquet_data = pd.read_parquet(parquet_path)

    return csv_data, parquet_data


def normalise_dataframe_metadata(
    csv_data: pd.DataFrame,
    parquet_data: pd.DataFrame,
) -> None:
    """
    Normalise representation metadata for comparison.

    This operation only affects in-memory DataFrames.
    Original Raw files remain unchanged.
    """

    # Normalise datetime precision
    csv_data.index = pd.DatetimeIndex(
        csv_data.index
    ).as_unit("ns")

    parquet_data.index = pd.DatetimeIndex(
        parquet_data.index
    ).as_unit("ns")

    # Normalise index metadata
    csv_data.index.name = None
    parquet_data.index.name = None

    # Normalise column metadata
    csv_data.columns.name = None
    parquet_data.columns.name = None


def verify_dataframe_consistency(
    ticker: str,
    csv_data: pd.DataFrame,
    parquet_data: pd.DataFrame,
    manifest: dict,
) -> None:
    """Compare CSV and Parquet representations."""

    # Normalise representation metadata
    normalise_dataframe_metadata(
        csv_data,
        parquet_data,
    )

    # Verify dimensions
    assert csv_data.shape == parquet_data.shape, (
        f"Shape mismatch for {ticker}: "
        f"CSV={csv_data.shape}, "
        f"Parquet={parquet_data.shape}"
    )

    # Verify columns
    assert list(csv_data.columns) == list(
        parquet_data.columns
    ), f"Column mismatch for {ticker}"

    # Verify observation dates
    assert csv_data.index.equals(
        parquet_data.index
    ), f"Datetime index mismatch for {ticker}"

    # Verify values
    assert_frame_equal(
        csv_data,
        parquet_data,
        check_dtype=False,
        check_names=False,
        check_freq=False,
        check_exact=False,
        rtol=RELATIVE_TOLERANCE,
        atol=ABSOLUTE_TOLERANCE,
    )

    # Verify manifest record count
    expected_records = manifest["record_count"]

    assert len(csv_data) == expected_records, (
        f"Record count mismatch for {ticker}: "
        f"expected {expected_records}, "
        f"got {len(csv_data)}"
    )

    # Verify observation start and end dates
    actual_start = str(csv_data.index.min())
    actual_end = str(csv_data.index.max())

    assert actual_start == manifest["observation_start"], (
        f"Observation start mismatch for {ticker}"
    )

    assert actual_end == manifest["observation_end"], (
        f"Observation end mismatch for {ticker}"
    )

    # Verify column metadata against manifest
    assert list(csv_data.columns) == manifest["columns"], (
        f"Manifest column mismatch for {ticker}"
    )

    print("CSV / Parquet: MATCH")
    print(f"Records: {len(csv_data):,}")
    print(f"Columns: {len(csv_data.columns)}")
    print(f"Date range: {actual_start} -> {actual_end}")
    print("MANIFEST CONSISTENCY: OK")


# ---------------------------------------------------------------------
# Main verification process
# ---------------------------------------------------------------------

def verify_acquisition(
    ticker: str,
    acquisition_directory: Path,
) -> None:
    """Verify one complete acquisition."""

    print("\n" + "=" * 65)
    print(f"ASSET: {ticker}")

    if not acquisition_directory.exists():
        raise FileNotFoundError(
            f"Acquisition directory not found: "
            f"{acquisition_directory}"
        )

    manifest_path = acquisition_directory / "manifest.json"

    csv_path = acquisition_directory / f"{ticker}.csv"
    parquet_path = acquisition_directory / f"{ticker}.parquet"

    # Load manifest
    manifest = load_manifest(manifest_path)

    # Verify acquisition identity
    assert manifest["ticker"] == ticker, (
        f"Ticker mismatch: expected {ticker}, "
        f"got {manifest['ticker']}"
    )

    # Verify file integrity
    verify_file_integrity(
        csv_path,
        manifest,
    )

    verify_file_integrity(
        parquet_path,
        manifest,
    )

    # Load market data
    csv_data, parquet_data = load_market_data(
        csv_path,
        parquet_path,
    )

    # Compare representations and manifest
    verify_dataframe_consistency(
        ticker,
        csv_data,
        parquet_data,
        manifest,
    )


def main() -> None:
    """Run integrity verification for all configured acquisitions."""

    successful_assets = []

    try:
        for ticker, directory in ACQUISITIONS.items():

            verify_acquisition(
                ticker,
                directory,
            )

            successful_assets.append(ticker)

    except Exception:
        logger.exception(
            "Acquisition integrity verification failed."
        )

        raise

    print("\n" + "=" * 65)
    print("ALL INTEGRITY CHECKS PASSED")
    print(
        f"Verified assets: {', '.join(successful_assets)}"
    )
    print(
        f"Total assets verified: {len(successful_assets)}"
    )


if __name__ == "__main__":
    main()