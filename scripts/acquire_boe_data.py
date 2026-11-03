"""Bank of England data acquisition connector."""

import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
import math
import re

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

import requests
import yaml

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BOE_IADB_ENDPOINT = (
    "https://www.bankofengland.co.uk/"
    "boeapps/database/_iadb-fromshowcolumns.asp"
)

DEFAULT_HTTP_TIMEOUT = 30

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,*/*",
}


# ---------------------------------------------------------------------
# Configuration models
# ---------------------------------------------------------------------


class DatasetMetadata(BaseModel):
    """Dataset identity and descriptive metadata."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    dataset_name: str
    description: str


class ProviderConfiguration(BaseModel):
    """Bank of England IADB provider configuration."""

    model_config = ConfigDict(extra="forbid")

    name: str
    source_type: str
    series_code: str
    source_page: str


class DataConfiguration(BaseModel):
    """Dataset measurement characteristics."""

    model_config = ConfigDict(extra="forbid")

    frequency: str
    unit: str
    currency: str
    observation_type: str
    adjustment: str


class AcquisitionConfiguration(BaseModel):
    """Acquisition behaviour."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["full_historical"]
    preserve_original_values: Literal[True]
    preserve_source_dates: Literal[True]
    source_format: Literal["csv"]


class TemporalConfiguration(BaseModel):
    """Temporal and publication metadata rules."""

    model_config = ConfigDict(extra="forbid")

    observation_date_required: Literal[True]
    publication_date_required: Literal[False]
    publication_date_policy: Literal["capture_when_available"]
    timezone: str
    publication_lag: str | None = None
    availability_timestamp_required: Literal[False]
    availability_timestamp_policy: Literal["capture_when_verifiable"]
    publication_schedule: str | dict[str, str]


class LicensingConfiguration(BaseModel):
    """Dataset licensing restrictions."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["pending_verification"]
    commercial_use_approved: Literal[False]
    redistribution_approved: Literal[False]


class StorageConfiguration(BaseModel):
    """Raw storage requirements."""

    model_config = ConfigDict(extra="forbid")

    provider_directory: str
    dataset_directory: str
    format: list[Literal["csv", "parquet"]]
    manifest_required: Literal[True]
    checksum_algorithm: Literal["sha256"]

    @field_validator("provider_directory", "dataset_directory")
    @classmethod
    def validate_directory_name(cls, value: str) -> str:
        """Reject unsafe or non-portable directory names."""

        import re

        if not isinstance(value, str):
            raise ValueError("Storage directory must be a string.")

        if not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]*",
            value,
        ):
            raise ValueError(
                "Storage directory must contain only letters, "
                "numbers, dots, underscores and hyphens, and must "
                "start with a letter or number."
            )

        if value in {".", ".."}:
            raise ValueError(
                "Relative path components are not allowed."
            )

        return value


class IADBConfiguration(BaseModel):
    """Validated Bank of England IADB dataset configuration."""

    model_config = ConfigDict(extra="forbid")

    dataset: DatasetMetadata
    provider: ProviderConfiguration
    data: DataConfiguration
    acquisition: AcquisitionConfiguration
    temporal: TemporalConfiguration
    licensing: LicensingConfiguration
    storage: StorageConfiguration

    @model_validator(mode="after")
    def validate_iadb_provider(self) -> "IADBConfiguration":
        """Validate that the configuration targets the BoE IADB."""

        if self.provider.name != "bank_of_england":
            raise ValueError(
                "IADB configuration provider must be bank_of_england."
            )

        if self.provider.source_type != "iadb":
            raise ValueError(
                "IADB configuration source_type must be iadb."
            )

        return self


# Backwards compatibility for existing Bank Rate imports.
BankRateConfiguration = IADBConfiguration


# ---------------------------------------------------------------------
# Acquisition manifest models
# ---------------------------------------------------------------------


class AcquiredFileMetadata(BaseModel):
    """Metadata describing the acquired source file."""

    model_config = ConfigDict(extra="forbid")

    file_name: Literal["original_data.csv"]
    format: Literal["csv"]
    size_bytes: int = Field(gt=0)
    sha256: str

    @field_validator("sha256")
    @classmethod
    def validate_file_sha256(cls, value: str) -> str:
        """Validate the acquired file SHA-256 digest."""

        validate_sha256(value, "Acquired file SHA-256")

        return value


class AcquisitionManifest(BaseModel):
    """Audit metadata for a physical data acquisition."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: Literal["1.0"]
    acquisition_id: str
    status: Literal["success"]


    provider: Literal["bank_of_england"]
    dataset_ids: list[str] = Field(min_length=1)
    source_endpoint: str

    @field_validator("dataset_ids")
    @classmethod
    def validate_dataset_ids(cls, value: list[str]) -> list[str]:
        """Reject empty or whitespace-only dataset identifiers."""

        if any(not dataset_id.strip() for dataset_id in value):
            raise ValueError(
                "Dataset identifiers must not be empty or whitespace-only."
            )

        return value

    request_parameters: dict[str, str]

    retrieved_at_utc: datetime

    configuration_sha256: str

    @field_validator("configuration_sha256")
    @classmethod
    def validate_configuration_sha256(cls, value: str) -> str:
        """Validate the configuration SHA-256 digest."""

        validate_sha256(value, "Configuration SHA-256")

        return value


    acquired_file: AcquiredFileMetadata


class AcquisitionCommitDurabilityError(RuntimeError):
    """Raised when an acquisition is committed but durability is unconfirmed."""

    def __init__(self, final_directory: Path) -> None:
        self.final_directory = final_directory

        super().__init__(
            "Acquisition was committed successfully, but directory "
            f"durability could not be confirmed: {final_directory}"
        )


# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------


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


def validate_sha256(value: str, field_name: str) -> None:
    """Validate a hexadecimal SHA-256 digest."""

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a hexadecimal SHA-256 digest."
        )

    if len(value) != 64:
        raise ValueError(
            f"{field_name} must contain exactly 64 hexadecimal characters."
        )

    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be a hexadecimal SHA-256 digest."
        ) from exc


def fsync_directory(directory: Path) -> None:
    """Synchronise directory metadata where supported."""

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_fd = os.open(directory, flags)

    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def write_bytes_durably(file_path: Path, content: bytes) -> None:
    """Write bytes and synchronise the file before returning."""

    with file_path.open("wb") as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())


def write_text_durably(file_path: Path, content: str) -> None:
    """Write UTF-8 text and synchronise the file before returning."""

    with file_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())


def load_iadb_config(
    config_path: Path,
) -> tuple[IADBConfiguration, str]:
    """Load and validate a Bank of England IADB YAML configuration."""

    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    raw_content = config_path.read_bytes()
    config_hash = hashlib.sha256(raw_content).hexdigest()

    try:
        config_data = yaml.safe_load(
            raw_content.decode("utf-8")
        )

        if not isinstance(config_data, dict):
            raise ValueError(
                "Configuration root must be a YAML mapping."
            )

        config = IADBConfiguration.model_validate(config_data)

    except (yaml.YAMLError, ValidationError) as exc:
        raise ValueError(
            f"Invalid IADB configuration: {exc}"
        ) from exc

    return config, config_hash


def load_bank_rate_config(
    config_path: Path,
) -> tuple[IADBConfiguration, str]:
    """Load the Bank Rate configuration using the generic IADB loader."""

    config, config_hash = load_iadb_config(config_path)

    if (
        config.dataset.dataset_id != "UK_BANK_RATE"
        or config.provider.series_code != "IUDBEDR"
    ):
        raise ValueError(
            "Configuration does not identify the approved Bank Rate dataset."
        )

    return config, config_hash


# ---------------------------------------------------------------------
# Bank of England IADB request construction
# ---------------------------------------------------------------------


def build_iadb_request_params(
    series_code: str,
    date_from: date,
    date_to: date | None = None,
) -> dict[str, str]:
    """Build validated parameters for a BoE IADB CSV request."""

    if not isinstance(series_code, str) or not series_code.strip():
        raise ValueError("Series code must be a non-empty string.")

    if isinstance(date_from, datetime) or not isinstance(date_from, date):
        raise ValueError("Start date must be a datetime.date instance.")

    if date_to is not None:
        if isinstance(date_to, datetime) or not isinstance(date_to, date):
            raise ValueError(
                "End date must be a datetime.date instance or None."
            )

        if date_to < date_from:
            raise ValueError(
                "End date cannot be earlier than start date."
            )

    return {
        "csv.x": "yes",
        "Datefrom": date_from.strftime("%d/%b/%Y"),
        "Dateto": (
            date_to.strftime("%d/%b/%Y")
            if date_to is not None
            else "now"
        ),
        "SeriesCodes": series_code.strip(),
        "CSVF": "TN",
        "UsingCodes": "Y",
        "VPD": "N",
    }


# ---------------------------------------------------------------------
# Bank of England IADB HTTP acquisition
# ---------------------------------------------------------------------


def fetch_iadb_csv(
    series_code: str,
    date_from: date,
    date_to: date | None = None,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
) -> bytes:
    """Fetch and validate the original CSV response from the BoE IADB."""

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, int)
        or timeout <= 0
    ):
        raise ValueError("Timeout must be a positive integer.")

    params = build_iadb_request_params(
        series_code=series_code,
        date_from=date_from,
        date_to=date_to,
    )

    try:
        response = requests.get(
            BOE_IADB_ENDPOINT,
            params=params,
            headers=HTTP_HEADERS,
            timeout=timeout,
        )

        response.raise_for_status()

    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            "BoE IADB request timed out."
        ) from exc

    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(
            f"BoE IADB returned an HTTP error: {exc}"
        ) from exc

    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"BoE IADB request failed: {exc}"
        ) from exc

    content = response.content

    if not content:
        raise ValueError("BoE IADB returned an empty response.")

    try:
        decoded_content = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "BoE IADB response is not valid UTF-8."
        ) from exc

    if decoded_content.lstrip().lower().startswith(
        ("<!doctype html", "<html")
    ):
        raise ValueError(
            "BoE IADB returned HTML instead of CSV data."
        )

    try:
        reader = csv.reader(
            io.StringIO(decoded_content),
            strict=True,
        )

        header = next(reader)

        normalised_header = [
            column.strip().upper()
            for column in header
        ]

        if normalised_header.count("DATE") != 1:
            raise ValueError(
                "BoE IADB CSV must contain exactly one DATE column."
            )

        normalised_series = series_code.strip().upper()

        if normalised_header.count(normalised_series) != 1:
            raise ValueError(
                f"BoE IADB CSV must contain exactly one "
                f"{series_code} column."
            )

        date_index = normalised_header.index("DATE")
        series_index = normalised_header.index(normalised_series)

        observation_count = 0
        previous_date = None
        observed_dates = set()

        for row_number, row in enumerate(reader, start=2):

            # Ignore completely blank lines.
            if not row or all(not value.strip() for value in row):
                continue

            if len(row) != len(header):
                raise ValueError(
                    f"BoE IADB CSV contains a malformed CSV row "
                    f"at line {row_number}."
                )

            raw_date = row[date_index].strip()
            raw_value = row[series_index].strip()

            # Validate observation date.
            try:
                observation_date = datetime.strptime(
                    raw_date,
                    "%d %b %Y",
                ).date()

            except ValueError as exc:
                raise ValueError(
                    f"BoE IADB CSV contains an invalid observation "
                    f"date at line {row_number}: {raw_date!r}."
                ) from exc

            # Validate requested date range.
            if observation_date < date_from:
                raise ValueError(
                    "BoE IADB CSV contains an observation outside "
                    "the requested date range."
                )

            if (
                date_to is not None
                and observation_date > date_to
            ):
                raise ValueError(
                    "BoE IADB CSV contains an observation outside "
                    "the requested date range."
                )

            # Reject duplicate dates.
            if observation_date in observed_dates:
                raise ValueError(
                    f"BoE IADB CSV contains a duplicate observation "
                    f"date: {observation_date}."
                )

            # Require chronological ordering.
            if (
                previous_date is not None
                and observation_date < previous_date
            ):
                raise ValueError(
                    "BoE IADB observations are not in chronological order."
                )

            # Validate numerical observations.
            try:
                numeric_value = float(raw_value)

            except ValueError as exc:
                raise ValueError(
                    f"BoE IADB CSV must contain a finite numeric value "
                    f"at line {row_number}."
                ) from exc

            if not math.isfinite(numeric_value):
                raise ValueError(
                    f"BoE IADB CSV must contain a finite numeric value "
                    f"at line {row_number}."
                )

            observed_dates.add(observation_date)
            previous_date = observation_date
            observation_count += 1

    except csv.Error as exc:
        raise ValueError(
            "BoE IADB response does not contain a valid CSV structure."
        ) from exc

    except StopIteration as exc:
        raise ValueError(
            "BoE IADB response does not contain a valid CSV header."
        ) from exc

    if observation_count == 0:
        raise ValueError(
            "BoE IADB CSV contains no valid observations."
        )

    # Preserve the original provider response without modification.
    return content


# ---------------------------------------------------------------------
# Raw acquisition persistence
# ---------------------------------------------------------------------

def validate_persistence_inputs(
    csv_content: bytes,
    config: IADBConfiguration,
    config_hash: str,
    request_params: dict[str, str],
) -> None:
    """Validate all inputs before creating Raw storage."""

    if not isinstance(csv_content, bytes) or not csv_content:
        raise ValueError("CSV content must be non-empty bytes.")

    validate_sha256(
        config_hash,
        "Configuration hash",
    )

    if not isinstance(config, IADBConfiguration):
        raise TypeError(
            "Config must be a validated IADBConfiguration."
        )

    if not isinstance(request_params, dict):
        raise TypeError(
            "Request parameters must be a dictionary."
        )

    if not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in request_params.items()
    ):
        raise ValueError(
            "All request parameter keys and values must be strings."
        )

    required_parameters = {
        "SeriesCodes",
        "Datefrom",
        "Dateto",
    }

    missing_parameters = required_parameters - request_params.keys()

    if missing_parameters:
        raise ValueError(
            "Missing required request parameters: "
            f"{sorted(missing_parameters)}"
        )

    date_pattern = (
        r"(0[1-9]|[12][0-9]|3[01])/"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/"
        r"[0-9]{4}"
    )

    for parameter in ("Datefrom", "Dateto"):
        if not re.fullmatch(date_pattern, request_params[parameter]):
            raise ValueError(
                f"{parameter} must use the strict DD/Mon/YYYY format."
            )

    try:
        date_from = datetime.strptime(
            request_params["Datefrom"],
            "%d/%b/%Y",
        ).date()

        date_to = datetime.strptime(
            request_params["Dateto"],
            "%d/%b/%Y",
        ).date()

    except ValueError as exc:
        raise ValueError(
            "Request dates must be valid calendar dates in DD/Mon/YYYY format."
        ) from exc

    if date_from > date_to:
        raise ValueError(
            "Request Datefrom must not be later than Dateto."
        )

    expected_series = config.provider.series_code

    if request_params["SeriesCodes"].strip().upper() != expected_series.upper():
        raise ValueError(
            "Request series code does not match the dataset configuration."
        )

    if config.provider.name != "bank_of_england":
        raise ValueError(
            "Provider identity does not match the Bank of England."
        )

    if config.provider.source_type != "iadb":
        raise ValueError(
            "Provider source type must be iadb."
        )

    if not config.dataset.dataset_id.strip():
        raise ValueError("Dataset ID cannot be empty.")

    if not config.storage.provider_directory.strip():
        raise ValueError("Provider storage directory cannot be empty.")

    if not config.storage.dataset_directory.strip():
        raise ValueError("Dataset storage directory cannot be empty.")

    if config.acquisition.source_format != "csv":
        raise ValueError("IADB acquisition source format must be CSV.")

    if "csv" not in config.storage.format:
        raise ValueError(
            "Storage configuration must allow CSV format."
        )


def persist_iadb_acquisition(
    csv_content: bytes,
    config: IADBConfiguration,
    config_hash: str,
    request_params: dict[str, str],
) -> Path:
    """Persist an immutable IADB acquisition atomically."""

    validate_persistence_inputs(
        csv_content=csv_content,
        config=config,
        config_hash=config_hash,
        request_params=request_params,
    )

    retrieved_at = datetime.now(timezone.utc)

    timestamp = retrieved_at.strftime("%Y%m%dT%H%M%SZ")
    acquisition_id = f"{timestamp}_{uuid4().hex[:8]}"

    storage_root = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "macro"
        / config.storage.provider_directory
        / "uk_interest_rates"
        / config.storage.dataset_directory
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
        original_file = temporary_directory / "original_data.csv"

        write_bytes_durably(
            original_file,
            csv_content,
        )

        file_metadata = AcquiredFileMetadata(
            file_name="original_data.csv",
            format="csv",
            size_bytes=len(csv_content),
            sha256=calculate_sha256(original_file),
        )

        manifest = AcquisitionManifest(
            manifest_version="1.0",
            acquisition_id=acquisition_id,
            status="success",
            provider=config.provider.name,
            dataset_ids=[config.dataset.dataset_id],
            source_endpoint=BOE_IADB_ENDPOINT,
            request_parameters=request_params,
            retrieved_at_utc=retrieved_at,
            configuration_sha256=config_hash,
            acquired_file=file_metadata,
        )

        manifest_path = temporary_directory / "manifest.json"

        manifest_content = json.dumps(
            manifest.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )

        write_text_durably(
            manifest_path,
            manifest_content,
        )

        fsync_directory(temporary_directory)

        os.rename(
            temporary_directory,
            final_directory,
        )
        commit_completed = True

        try:
            fsync_directory(storage_root)
        except Exception as exc:
            raise AcquisitionCommitDurabilityError(
                final_directory
            ) from exc

    except AcquisitionCommitDurabilityError:
        # The directory has already been renamed into its final location.
        # Preserve it and report that durability could not be confirmed.
        raise

    except Exception:
        # Cleanup is safe only before the atomic rename has committed.
        if not commit_completed and temporary_directory.exists():
            shutil.rmtree(temporary_directory)

        raise

    return final_directory