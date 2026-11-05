"""Office for National Statistics CSV acquisition connector.

Original CSV files are preserved without transformation.
"""
from __future__ import annotations

import argparse
import csv
import ctypes
import errno
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

import requests
import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HTTP_TIMEOUT = 30
CONFIG_PATHS = {
    "inflation": Path("configs/datasets/uk_macro/inflation.yaml"),
    "gdp": Path("configs/datasets/uk_macro/gdp.yaml"),
}
EXPECTED = {
    "inflation": {
        "code": "MM23",
        "ids": {"UK_CPI", "UK_CORE_CPI", "UK_CPIH"},
        "series": {"D7G7", "DKO8", "L55O"},
        "directory": "inflation",
        "endpoint": "mm23.csv",
    },
    "gdp": {
        "code": "QNA",
        "ids": {"UK_REAL_GDP", "UK_GDP_GROWTH"},
        "series": {"ABMI", "IHYQ"},
        "directory": "gdp",
        "endpoint": "qna.csv",
    },
}
HTTP_HEADERS = {
    "User-Agent": "QuantitativeTradingResearch/1.0",
    "Accept": "text/csv,text/plain,application/octet-stream,*/*",
}


class DatasetMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_ids: list[str] = Field(min_length=1)
    dataset_name: str
    description: str

    @field_validator("dataset_ids")
    @classmethod
    def unique_nonempty_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)) or any(not item.strip() for item in value):
            raise ValueError("Dataset IDs must be unique and non-empty.")
        return value


class ProviderConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Literal["office_for_national_statistics"]
    source_type: Literal["published_dataset_csv"]
    dataset_code: Literal["MM23", "QNA"]
    source_page: HttpUrl
    source_endpoint: HttpUrl


class SeriesConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    series_code: str
    dataset_id: str
    description: str
    frequency: Literal["monthly", "quarterly"]
    unit: str

    @field_validator("series_code", "dataset_id")
    @classmethod
    def nonempty_identifier(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Identifiers must be non-empty.")
        return value


class AcquisitionConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["full_historical"]
    preserve_original_values: Literal[True]
    preserve_source_dates: Literal[True]
    source_format: Literal["csv"]


class TemporalConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observation_date_required: Literal[True]
    publication_date_required: Literal[False]
    publication_date_policy: Literal["capture_when_available"]
    timezone: Literal["Europe/London"]
    availability_timestamp_required: Literal[False]
    availability_timestamp_policy: Literal["capture_when_verifiable"]


class LicensingConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["pending_verification"]
    commercial_use_approved: Literal[False]
    redistribution_approved: Literal[False]


class StorageConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_directory: Literal["ons"]
    dataset_directory: Literal["inflation", "gdp"]
    format: list[Literal["csv"]]
    manifest_required: Literal[True]
    checksum_algorithm: Literal["sha256"]

    @field_validator("format")
    @classmethod
    def csv_required(cls, value: list[str]) -> list[str]:
        if "csv" not in value:
            raise ValueError("CSV must be included in Raw storage formats.")
        return value


class ONSConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: DatasetMetadata
    provider: ProviderConfiguration
    series: list[SeriesConfiguration] = Field(min_length=1)
    acquisition: AcquisitionConfiguration
    temporal: TemporalConfiguration
    licensing: LicensingConfiguration
    storage: StorageConfiguration

    @model_validator(mode="after")
    def validate_series_mapping(self) -> "ONSConfiguration":
        ids = [item.dataset_id for item in self.series]
        codes = [item.series_code for item in self.series]
        if len(ids) != len(set(ids)) or len(codes) != len(set(codes)):
            raise ValueError("Dataset IDs and series codes must be unique.")
        if set(ids) != set(self.dataset.dataset_ids):
            raise ValueError("Dataset IDs do not match the series mapping.")
        required_frequency = "monthly" if self.provider.dataset_code == "MM23" else "quarterly"
        if any(item.frequency != required_frequency for item in self.series):
            raise ValueError(f"{self.provider.dataset_code} series must be {required_frequency}.")
        return self


def calculate_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fsync_directory(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_bytes_durably(path: Path, content: bytes) -> None:
    with path.open("wb") as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())


def write_text_durably(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())


def rename_directory_noreplace(source: Path, destination: Path) -> None:
    """Linux atomic directory rename that refuses to replace a destination."""
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        renameat2 = libc.renameat2
    except AttributeError as exc:
        raise OSError(errno.ENOSYS, "renameat2 is unavailable.") from exc
    renameat2.argtypes = [
        ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(-100, os.fsencode(source), -100, os.fsencode(destination), 1)
    if result != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(destination))


def load_ons_config(path: Path) -> tuple[ONSConfiguration, str]:
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    raw = path.read_bytes()
    try:
        parsed = yaml.safe_load(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("Configuration root must be a YAML mapping.")
        config = ONSConfiguration.model_validate(parsed)
    except (UnicodeDecodeError, yaml.YAMLError, ValidationError) as exc:
        raise ValueError(f"Invalid ONS configuration {path}: {exc}") from exc
    return config, calculate_sha256(raw)


def validate_ons_config(config: ONSConfiguration, group: str) -> None:
    if group not in EXPECTED:
        raise ValueError(f"Unknown ONS group: {group}")
    expected = EXPECTED[group]
    if config.provider.dataset_code != expected["code"]:
        raise ValueError(f"Unexpected ONS dataset code for {group}.")
    if set(config.dataset.dataset_ids) != expected["ids"]:
        raise ValueError(f"Unexpected dataset IDs for {group}.")
    if {item.series_code for item in config.series} != expected["series"]:
        raise ValueError(f"Unexpected series codes for {group}.")
    if config.storage.dataset_directory != expected["directory"]:
        raise ValueError(f"Unexpected storage directory for {group}.")
    if not str(config.provider.source_endpoint).lower().endswith(expected["endpoint"]):
        raise ValueError(f"Unexpected source endpoint for {group}.")


def validate_csv_content(content: bytes, dataset_code: str) -> tuple[int, int]:
    """Check encoding, HTML rejection, header and non-empty data rows."""
    if not isinstance(content, bytes) or not content:
        raise ValueError(f"ONS {dataset_code} returned an empty response.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"ONS {dataset_code} response is not valid UTF-8.") from exc
    if text.lstrip().lower().startswith(("<!doctype html", "<html")):
        raise ValueError(f"ONS {dataset_code} returned HTML instead of CSV.")
    try:
        reader = csv.reader(io.StringIO(text))
        header = next(reader, None)
        if header is None or len(header) < 2 or not any(cell.strip() for cell in header):
            raise ValueError(f"ONS {dataset_code} CSV has an invalid header.")
        count = sum(1 for row in reader if row and any(cell.strip() for cell in row))
    except csv.Error as exc:
        raise ValueError(f"ONS {dataset_code} response is not valid CSV.") from exc
    if count == 0:
        raise ValueError(f"ONS {dataset_code} CSV contains no data rows.")
    return len(header), count


def fetch_ons_csv(endpoint: str, dataset_code: str, timeout: int = DEFAULT_HTTP_TIMEOUT) -> bytes:
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise ValueError("Timeout must be a positive integer.")
    try:
        response = requests.get(endpoint, headers=HTTP_HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(f"ONS {dataset_code} request timed out.") from exc
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"ONS {dataset_code} returned an HTTP error: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"ONS {dataset_code} request failed: {exc}") from exc
    content = response.content
    validate_csv_content(content, dataset_code)
    return content


def persist_ons_acquisition(
    content: bytes, config: ONSConfiguration, config_hash: str
) -> Path:
    """Persist one immutable original CSV shared by its logical dataset IDs."""
    validate_csv_content(content, config.provider.dataset_code)
    if not re.fullmatch(r"[a-fA-F0-9]{64}", config_hash):
        raise ValueError("Invalid configuration SHA-256 digest.")

    retrieved = datetime.now(timezone.utc)
    acquisition_id = f"{retrieved.strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"
    root = (
        PROJECT_ROOT / "data" / "raw" / "macro"
        / config.storage.provider_directory / config.storage.dataset_directory
    )
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"acquisition_{acquisition_id}"
    temporary = Path(tempfile.mkdtemp(prefix=".acquisition_tmp_", dir=root))
    committed = False
    try:
        write_bytes_durably(temporary / "original_data.csv", content)
        manifest = {
            "manifest_version": "1.0",
            "acquisition_id": acquisition_id,
            "status": "success",
            "provider": "office_for_national_statistics",
            "source_dataset_code": config.provider.dataset_code,
            "dataset_ids": config.dataset.dataset_ids,
            "source_page": str(config.provider.source_page),
            "source_endpoint": str(config.provider.source_endpoint),
            "retrieved_at_utc": retrieved.isoformat(),
            "configuration_sha256": config_hash,
            "acquisition_scope": "one_physical_csv_shared_by_multiple_logical_datasets",
            "transformation_performed": False,
            "acquired_file": {
                "file_name": "original_data.csv",
                "format": "csv",
                "size_bytes": len(content),
                "sha256": calculate_sha256(content),
            },
        }
        write_text_durably(
            temporary / "manifest.json",
            json.dumps(manifest, indent=2, ensure_ascii=False),
        )
        fsync_directory(temporary)
        rename_directory_noreplace(temporary, destination)
        committed = True
        try:
            fsync_directory(root)
        except Exception as exc:
            raise RuntimeError(
                f"ONS acquisition committed but durability is unconfirmed: {destination}"
            ) from exc
    except Exception:
        if not committed and temporary.exists():
            shutil.rmtree(temporary)
        raise
    return destination


def load_group(group: str) -> tuple[ONSConfiguration, str]:
    config, digest = load_ons_config(CONFIG_PATHS[group])
    validate_ons_config(config, group)
    return config, digest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and acquire original ONS macroeconomic CSV files."
    )
    parser.add_argument("--group", choices=("inflation", "gdp", "all"), default="all")
    parser.add_argument(
        "--fetch", action="store_true",
        help="Download and validate files without persisting them.",
    )
    parser.add_argument(
        "--persist", action="store_true",
        help="Download, validate and persist immutable Raw acquisitions.",
    )
    args = parser.parse_args()
    if args.fetch and args.persist:
        parser.error("--fetch and --persist cannot be combined.")

    groups = ("inflation", "gdp") if args.group == "all" else (args.group,)
    for group in groups:
        config, digest = load_group(group)
        print(f"[VALID] {group}: {config.provider.dataset_code}")
        print(f"  Dataset IDs: {', '.join(config.dataset.dataset_ids)}")
        print(f"  Series: {', '.join(item.series_code for item in config.series)}")
        print(f"  Configuration SHA-256: {digest}")
        if args.fetch or args.persist:
            raw = fetch_ons_csv(str(config.provider.source_endpoint), config.provider.dataset_code)
            columns, rows = validate_csv_content(raw, config.provider.dataset_code)
            print(f"[FETCHED] {len(raw):,} bytes; {rows:,} rows; {columns} columns")
            if args.persist:
                path = persist_ons_acquisition(raw, config, digest)
                print(f"[PERSISTED] {path.relative_to(PROJECT_ROOT)}")
            else:
                print("[DRY RUN] Download validated; nothing persisted.")
        else:
            print("[DRY RUN] Config validated; no network request or persistence.")


if __name__ == "__main__":
    main()
