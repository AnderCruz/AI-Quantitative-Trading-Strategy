"""Acquire and persist the shared Bank of England nominal gilt yield curve archive."""

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zipfile import BadZipFile, ZipFile
import ctypes
import errno

import requests
import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, Field


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONFIG_PATHS = {
    "UK_GILT_NOMINAL_2Y": (
        PROJECT_ROOT
        / "configs/datasets/uk_interest_rates/gilt_nominal_2y.yaml"
    ),
    "UK_GILT_NOMINAL_10Y": (
        PROJECT_ROOT
        / "configs/datasets/uk_interest_rates/gilt_nominal_10y.yaml"
    ),
}

BOE_ARCHIVE_URL = (
    "https://www.bankofengland.co.uk/-/media/boe/files/"
    "statistics/yield-curves/glcnominalddata.zip"
)

DEFAULT_HTTP_TIMEOUT = 180
ARCHIVE_FILENAME = "original_data.zip"

DATASET_IDS = [
    "UK_GILT_NOMINAL_2Y",
    "UK_GILT_NOMINAL_10Y",
]


# ---------------------------------------------------------------------
# Configuration models
# ---------------------------------------------------------------------


class DatasetConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    dataset_name: str
    description: str


class ProviderConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    source_type: str
    curve_type: str
    measure: str
    maturity_years: int
    source_page: str
    curve_scope: str


class AcquisitionConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str
    preserve_original_values: bool
    preserve_source_dates: bool
    source_format: str
    archive_type: str
    archive_shared_with: list[str]


class StorageConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_directory: str
    dataset_directory: str
    original_archive_required: bool
    manifest_required: bool
    checksum_algorithm: str


class YieldCurveConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset: DatasetConfiguration
    provider: ProviderConfiguration
    data: dict
    acquisition: AcquisitionConfiguration
    temporal: dict
    licensing: dict
    storage: StorageConfiguration


# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------


def calculate_sha256(content: bytes) -> str:
    """Calculate the SHA-256 checksum of binary content."""

    return hashlib.sha256(content).hexdigest()


def write_bytes_durably(path: Path, content: bytes) -> None:
    """Write binary content and synchronise it to disk."""

    with path.open("wb") as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())


def write_text_durably(path: Path, content: str) -> None:
    """Write UTF-8 text and synchronise it to disk."""

    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())


def fsync_directory(directory: Path) -> None:
    """Synchronise directory metadata."""

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_fd = os.open(directory, flags)

    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


# ---------------------------------------------------------------------
# Configuration loading and validation
# ---------------------------------------------------------------------


def load_yield_curve_config(
    config_path: Path,
) -> tuple[YieldCurveConfiguration, str]:
    """Load a yield curve configuration and calculate its SHA-256."""

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    raw_content = config_path.read_bytes()
    config_hash = calculate_sha256(raw_content)

    try:
        raw_config = yaml.safe_load(raw_content.decode("utf-8"))

        if not isinstance(raw_config, dict):
            raise ValueError("Configuration root must be a mapping.")

        config = YieldCurveConfiguration.model_validate(raw_config)

    except (yaml.YAMLError, ValidationError) as exc:
        raise ValueError(
            f"Invalid yield curve configuration: {config_path}: {exc}"
        ) from exc

    return config, config_hash


def load_and_validate_configurations() -> tuple[dict, dict]:
    """Load and validate both configurations as one shared archive."""

    configurations = {}
    hashes = {}

    for expected_id, config_path in CONFIG_PATHS.items():
        config, config_hash = load_yield_curve_config(config_path)

        if config.dataset.dataset_id != expected_id:
            raise ValueError(
                f"Expected {expected_id}, got {config.dataset.dataset_id}."
            )

        configurations[expected_id] = config
        hashes[expected_id] = config_hash

    config_2y = configurations["UK_GILT_NOMINAL_2Y"]
    config_10y = configurations["UK_GILT_NOMINAL_10Y"]

    for config in (config_2y, config_10y):
        if config.provider.name != "bank_of_england":
            raise ValueError("Unexpected provider.")

        if config.provider.source_type != "yield_curve_archive":
            raise ValueError("Unexpected provider source type.")

        if config.provider.curve_type != "nominal_government_liability":
            raise ValueError("Unexpected curve type.")

        if config.provider.measure != "spot":
            raise ValueError("Only spot yield curves are supported.")

        if config.acquisition.mode != "full_historical":
            raise ValueError("Unexpected acquisition mode.")

        if config.acquisition.source_format != "zip":
            raise ValueError("The original source format must be ZIP.")

        if config.acquisition.archive_type != "daily_government_liability_curve":
            raise ValueError("Unexpected archive type.")

        if config.storage.checksum_algorithm != "sha256":
            raise ValueError("Only SHA-256 is supported.")

        if not config.storage.original_archive_required:
            raise ValueError("Original archive preservation is mandatory.")

        if not config.storage.manifest_required:
            raise ValueError("Acquisition manifest is mandatory.")

        if config.licensing.get("commercial_use_approved") is not False:
            raise ValueError("Unexpected commercial-use approval.")

        if config.licensing.get("redistribution_approved") is not False:
            raise ValueError("Unexpected redistribution approval.")

    if config_2y.provider.maturity_years != 2:
        raise ValueError("The 2Y configuration has an incorrect maturity.")

    if config_10y.provider.maturity_years != 10:
        raise ValueError("The 10Y configuration has an incorrect maturity.")

    if config_2y.acquisition.archive_shared_with != [
        "UK_GILT_NOMINAL_10Y"
    ]:
        raise ValueError("The 2Y shared archive declaration is incorrect.")

    if config_10y.acquisition.archive_shared_with != [
        "UK_GILT_NOMINAL_2Y"
    ]:
        raise ValueError("The 10Y shared archive declaration is incorrect.")

    if (
        config_2y.storage.provider_directory
        != config_10y.storage.provider_directory
    ):
        raise ValueError("Provider storage directories do not match.")

    return configurations, hashes


# ---------------------------------------------------------------------
# Archive acquisition and validation
# ---------------------------------------------------------------------


def validate_zip_archive(content: bytes) -> list[str]:
    """Validate the ZIP archive and all contained workbook entries."""

    if not isinstance(content, bytes) or not content:
        raise ValueError("The archive response is empty.")

    if not content.startswith(b"PK"):
        raise ValueError("The response does not have a ZIP signature.")

    try:
        import io

        with ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()

            if not members:
                raise ValueError("The ZIP archive contains no files.")

            excel_files = [
                member.filename
                for member in members
                if member.filename.lower().endswith((".xlsx", ".xls"))
            ]

            if not excel_files:
                raise ValueError("No Excel workbooks were found.")

            unsafe_members = [
                member.filename
                for member in members
                if (
                    Path(member.filename).is_absolute()
                    or ".." in Path(member.filename).parts
                )
            ]

            if unsafe_members:
                raise ValueError(
                    f"Unsafe archive paths detected: {unsafe_members}"
                )

            corrupted_member = archive.testzip()

            if corrupted_member is not None:
                raise ValueError(
                    f"Corrupted ZIP member: {corrupted_member}"
                )

            return excel_files

    except BadZipFile as exc:
        raise ValueError("The response is not a valid ZIP archive.") from exc


def fetch_yield_curve_archive(
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> bytes:
    """Download and validate the original BoE ZIP archive."""

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, int)
        or timeout <= 0
    ):
        raise ValueError("Timeout must be a positive integer.")

    try:
        response = requests.get(
            BOE_ARCHIVE_URL,
            headers={
                "User-Agent": "QuantitativeTradingResearch/1.0",
                "Accept": "application/zip,application/octet-stream,*/*",
            },
            timeout=timeout,
        )

        response.raise_for_status()

    except requests.exceptions.Timeout as exc:
        raise RuntimeError("BoE archive request timed out.") from exc

    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(
            f"BoE archive returned an HTTP error: {exc}"
        ) from exc

    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"BoE archive request failed: {exc}"
        ) from exc

    content = response.content

    validate_zip_archive(content)

    return content

def rename_directory_noreplace(source: Path, destination: Path) -> None:
    """Atomically rename a directory without replacing an existing destination.

    This implementation requires Linux renameat2 with RENAME_NOREPLACE.
    It deliberately fails closed when the operation is unavailable.
    """

    libc = ctypes.CDLL(None, use_errno=True)

    try:
        renameat2 = libc.renameat2
    except AttributeError as exc:
        raise OSError(
            errno.ENOSYS,
            "renameat2 is not available on this system.",
        ) from exc

    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int

    at_fdcwd = -100
    rename_noreplace = 1

    result = renameat2(
        at_fdcwd,
        os.fsencode(source),
        at_fdcwd,
        os.fsencode(destination),
        rename_noreplace,
    )

    if result != 0:
        error_code = ctypes.get_errno()

        raise OSError(
            error_code,
            os.strerror(error_code),
            str(destination),
        )


# ---------------------------------------------------------------------
# Raw acquisition persistence
# ---------------------------------------------------------------------


def persist_yield_curve_archive(
    content: bytes,
    configurations: dict,
    configuration_hashes: dict,
) -> Path:
    """Persist one immutable archive shared by both logical datasets."""

    excel_files = validate_zip_archive(content)

    if set(configurations) != set(DATASET_IDS):
        raise ValueError("Both approved dataset configurations are required.")

    if set(configuration_hashes) != set(DATASET_IDS):
        raise ValueError("Both configuration hashes are required.")

    for dataset_id, config in configurations.items():
        if config.dataset.dataset_id != dataset_id:
            raise ValueError("Configuration identity mismatch.")

        digest = configuration_hashes[dataset_id]

        if not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
            raise ValueError(
                f"Invalid configuration SHA-256 for {dataset_id}."
            )

    retrieved_at = datetime.now(timezone.utc)
    timestamp = retrieved_at.strftime("%Y%m%dT%H%M%SZ")
    acquisition_id = f"{timestamp}_{uuid4().hex[:8]}"

    provider_directory = configurations[
        "UK_GILT_NOMINAL_2Y"
    ].storage.provider_directory

    storage_root = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "macro"
        / provider_directory
        / "yield_curve_archive"
    )

    storage_root.mkdir(parents=True, exist_ok=True)

    final_directory = storage_root / f"acquisition_{acquisition_id}"

    if final_directory.exists():
        raise FileExistsError(
            f"Acquisition directory already exists: {final_directory}"
        )

    temporary_directory = Path(
        tempfile.mkdtemp(
            prefix=".acquisition_tmp_",
            dir=storage_root,
        )
    )

    commit_completed = False

    try:
        archive_path = temporary_directory / ARCHIVE_FILENAME

        write_bytes_durably(archive_path, content)

        file_metadata = {
            "file_name": ARCHIVE_FILENAME,
            "format": "zip",
            "size_bytes": len(content),
            "sha256": calculate_sha256(content),
            "workbook_count": len(excel_files),
            "workbooks": excel_files,
        }

        manifest = {
            "manifest_version": "1.0",
            "acquisition_id": acquisition_id,
            "status": "success",
            "provider": "bank_of_england",
            "dataset_ids": DATASET_IDS,
            "source_endpoint": BOE_ARCHIVE_URL,
            "retrieved_at_utc": retrieved_at.isoformat(),
            "configuration_sha256": configuration_hashes,
            "acquired_file": file_metadata,
            "acquisition_scope": "one_physical_archive_shared_by_two_datasets",
            "transformation_performed": False,
        }

        manifest_path = temporary_directory / "manifest.json"

        write_text_durably(
            manifest_path,
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
            ),
        )

        fsync_directory(temporary_directory)

        rename_directory_noreplace(
            temporary_directory,
            final_directory,
        )

        commit_completed = True

        try:
            fsync_directory(storage_root)
        except Exception as exc:
            raise RuntimeError(
                "Archive was committed, but directory durability "
                f"could not be confirmed: {final_directory}"
            ) from exc

    except Exception:
        if not commit_completed and temporary_directory.exists():
            shutil.rmtree(temporary_directory)

        raise

    return final_directory


# ---------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acquire the shared Bank of England gilt yield curve archive."
    )

    parser.add_argument(
        "--persist",
        action="store_true",
        help="Persist the validated original ZIP archive into immutable Raw storage.",
    )

    args = parser.parse_args()

    print("Loading and validating 2Y and 10Y configurations...")

    configurations, hashes = load_and_validate_configurations()

    print("CONFIGURATIONS VALIDATED")
    print(f"Datasets: {', '.join(DATASET_IDS)}")

    for dataset_id, digest in hashes.items():
        print(f"{dataset_id} configuration SHA-256: {digest}")

    print("\nDownloading the shared BoE historical archive...")

    content = fetch_yield_curve_archive()

    excel_files = validate_zip_archive(content)

    print("\nARCHIVE VALIDATION PASSED")
    print(f"Downloaded bytes: {len(content):,}")
    print(f"SHA-256: {calculate_sha256(content)}")
    print(f"Excel workbooks: {len(excel_files)}")

    for filename in excel_files:
        print(f"  - {filename}")

    if not args.persist:
        print("\nDRY RUN COMPLETED")
        print("No files were written to Raw.")
        print("No acquisition manifest was created.")
        print("No watermark was updated.")
        print("\nUse --persist only after explicit persistence approval.")
        return

    print("\nPersisting the shared original archive...")

    acquisition_directory = persist_yield_curve_archive(
        content=content,
        configurations=configurations,
        configuration_hashes=hashes,
    )

    print("\nPERSISTENCE COMPLETED")
    print(f"Acquisition directory: {acquisition_directory}")
    print(f"Datasets: {', '.join(DATASET_IDS)}")
    print("One original ZIP and one shared manifest were persisted.")
    print("No workbook extraction or transformation was performed.")
    print("No watermark was updated.")


if __name__ == "__main__":
    main()
