"""Tests for Bank of England Raw acquisition persistence."""

import hashlib
import json
import os

from unittest.mock import patch

import pytest

import scripts.acquire_boe_data as boe

from scripts.acquire_boe_data import (
    PROJECT_ROOT,
    AcquisitionCommitDurabilityError,
    AcquisitionManifest,
    load_bank_rate_config,
    persist_iadb_acquisition,
    load_iadb_config,
)


VALID_REQUEST_PARAMS = {
    "SeriesCodes": "IUDBEDR",
    "Datefrom": "01/Jan/2025",
    "Dateto": "31/Jan/2025",
}


@pytest.fixture
def bank_rate_config():
    """Load the validated Bank Rate dataset configuration."""

    config_path = (
        PROJECT_ROOT
        / "configs/datasets/uk_interest_rates/bank_rate.yaml"
    )

    return load_bank_rate_config(config_path)

@pytest.fixture
def sonia_config():
    """Load the validated SONIA dataset configuration."""

    config_path = (
        PROJECT_ROOT
        / "configs/datasets/uk_interest_rates/sonia.yaml"
    )

    return load_iadb_config(config_path)

@pytest.fixture
def sample_csv():
    """Provide sample original CSV content."""

    return (
        b"DATE,IUDBEDR\n"
        b"02 Jan 2025,4.75\n"
        b"03 Jan 2025,4.75\n"
    )

@pytest.fixture
def sonia_sample_csv():
    """Provide synthetic SONIA CSV content."""

    return (
        b"DATE,IUDSOIA\n"
        b"02 Jan 2025,4.45\n"
        b"03 Jan 2025,4.46\n"
    )

@pytest.mark.parametrize(
    "dataset_ids",
    [
        [],
        [""],
        ["   "],
        ["UK_BANK_RATE", ""],
        ["UK_BANK_RATE", "   "],
    ],
)
def test_acquisition_manifest_rejects_invalid_dataset_ids(dataset_ids):
    """Reject empty or whitespace-only dataset identifiers."""

    with pytest.raises(ValueError):
        AcquisitionManifest(
            manifest_version="1.0",
            acquisition_id="20261103T120000Z_12345678",
            status="success",
            provider="bank_of_england",
            dataset_ids=dataset_ids,
            source_endpoint=boe.BOE_IADB_ENDPOINT,
            request_parameters=VALID_REQUEST_PARAMS,
            retrieved_at_utc=boe.datetime.now(boe.timezone.utc),
            configuration_sha256="a" * 64,
            acquired_file={
                "file_name": "original_data.csv",
                "format": "csv",
                "size_bytes": 100,
                "sha256": "b" * 64,
            },
        )


def test_acquisition_manifest_accepts_multiple_dataset_ids():
    """Accept multiple valid dataset identifiers."""

    manifest = AcquisitionManifest(
        manifest_version="1.0",
        acquisition_id="20261103T120000Z_12345678",
        status="success",
        provider="bank_of_england",
        dataset_ids=["UK_BANK_RATE", "UK_SONIA"],
        source_endpoint=boe.BOE_IADB_ENDPOINT,
        request_parameters=VALID_REQUEST_PARAMS,
        retrieved_at_utc=boe.datetime.now(boe.timezone.utc),
        configuration_sha256="a" * 64,
        acquired_file={
            "file_name": "original_data.csv",
            "format": "csv",
            "size_bytes": 100,
            "sha256": "b" * 64,
        },
    )

    assert manifest.dataset_ids == ["UK_BANK_RATE", "UK_SONIA"]



def test_persist_iadb_acquisition_creates_expected_files(
    tmp_path,
    monkeypatch,
    bank_rate_config,
    sample_csv,
):
    """Verify that the acquisition files are created."""

    monkeypatch.setattr(boe, "PROJECT_ROOT", tmp_path)

    config, config_hash = bank_rate_config

    acquisition_directory = persist_iadb_acquisition(
        csv_content=sample_csv,
        config=config,
        config_hash=config_hash,
        request_params=VALID_REQUEST_PARAMS,
    )

    assert acquisition_directory.is_dir()
    assert (acquisition_directory / "original_data.csv").is_file()
    assert (acquisition_directory / "manifest.json").is_file()


def test_persist_iadb_acquisition_preserves_original_bytes(
    tmp_path,
    monkeypatch,
    bank_rate_config,
    sample_csv,
):
    """Verify that the original CSV bytes remain unchanged."""

    monkeypatch.setattr(boe, "PROJECT_ROOT", tmp_path)

    config, config_hash = bank_rate_config

    acquisition_directory = persist_iadb_acquisition(
        csv_content=sample_csv,
        config=config,
        config_hash=config_hash,
        request_params=VALID_REQUEST_PARAMS,
    )

    stored_content = (
        acquisition_directory / "original_data.csv"
    ).read_bytes()

    assert stored_content == sample_csv


def test_persist_iadb_acquisition_records_correct_sha256(
    tmp_path,
    monkeypatch,
    bank_rate_config,
    sample_csv,
):
    """Verify that the manifest contains the correct checksum."""

    monkeypatch.setattr(boe, "PROJECT_ROOT", tmp_path)

    config, config_hash = bank_rate_config

    acquisition_directory = persist_iadb_acquisition(
        csv_content=sample_csv,
        config=config,
        config_hash=config_hash,
        request_params=VALID_REQUEST_PARAMS,
    )

    manifest = json.loads(
        (acquisition_directory / "manifest.json").read_text(
            encoding="utf-8"
        )
    )

    expected_hash = hashlib.sha256(sample_csv).hexdigest()

    assert manifest["acquired_file"]["sha256"] == expected_hash
    assert manifest["acquired_file"]["size_bytes"] == len(sample_csv)


def test_persist_iadb_acquisition_records_correct_manifest_metadata(
    tmp_path,
    monkeypatch,
    bank_rate_config,
    sample_csv,
):
    """Verify the acquisition manifest metadata."""

    monkeypatch.setattr(boe, "PROJECT_ROOT", tmp_path)

    config, config_hash = bank_rate_config

    acquisition_directory = persist_iadb_acquisition(
        csv_content=sample_csv,
        config=config,
        config_hash=config_hash,
        request_params=VALID_REQUEST_PARAMS,
    )

    manifest = json.loads(
        (acquisition_directory / "manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["manifest_version"] == "1.0"
    assert manifest["status"] == "success"
    assert manifest["provider"] == "bank_of_england"
    assert manifest["dataset_ids"] == ["UK_BANK_RATE"]
    assert manifest["request_parameters"] == VALID_REQUEST_PARAMS
    assert manifest["configuration_sha256"] == config_hash
    assert manifest["acquisition_id"] in acquisition_directory.name


def test_persist_iadb_acquisition_does_not_overwrite_existing_directory(
    tmp_path,
    monkeypatch,
    bank_rate_config,
    sample_csv,
):
    """Verify that an existing acquisition cannot be overwritten."""

    monkeypatch.setattr(boe, "PROJECT_ROOT", tmp_path)

    config, config_hash = bank_rate_config

    with patch("scripts.acquire_boe_data.uuid4") as mock_uuid:
        mock_uuid.return_value.hex = "12345678abcdef00"

        first_directory = persist_iadb_acquisition(
            csv_content=sample_csv,
            config=config,
            config_hash=config_hash,
            request_params=VALID_REQUEST_PARAMS,
        )

        with pytest.raises(FileExistsError):
            persist_iadb_acquisition(
                csv_content=sample_csv,
                config=config,
                config_hash=config_hash,
                request_params=VALID_REQUEST_PARAMS,
            )

    assert first_directory.is_dir()
    assert (
        first_directory / "original_data.csv"
    ).read_bytes() == sample_csv


def test_persist_iadb_acquisition_cleans_temporary_directory_on_failure(
    tmp_path,
    monkeypatch,
    bank_rate_config,
    sample_csv,
):
    """Verify temporary directory cleanup after a failed atomic rename."""

    monkeypatch.setattr(boe, "PROJECT_ROOT", tmp_path)

    config, config_hash = bank_rate_config

    with patch(
        "scripts.acquire_boe_data.os.rename",
        side_effect=OSError("Simulated commit failure"),
    ):
        with pytest.raises(OSError, match="Simulated commit failure"):
            persist_iadb_acquisition(
                csv_content=sample_csv,
                config=config,
                config_hash=config_hash,
                request_params=VALID_REQUEST_PARAMS,
            )

    storage_root = (
        tmp_path
        / "data"
        / "raw"
        / "macro"
        / "bank_of_england"
        / "uk_interest_rates"
        / "bank_rate"
    )

    temporary_directories = list(
        storage_root.glob(".acquisition_tmp_*")
    )

    assert temporary_directories == []


def test_persist_iadb_acquisition_preserves_committed_directory_when_fsync_fails(
    tmp_path,
    monkeypatch,
    bank_rate_config,
    sample_csv,
):
    """Preserve committed files if parent-directory fsync fails."""

    monkeypatch.setattr(boe, "PROJECT_ROOT", tmp_path)

    config, config_hash = bank_rate_config

    storage_root = (
        tmp_path
        / "data"
        / "raw"
        / "macro"
        / "bank_of_england"
        / "uk_interest_rates"
        / "bank_rate"
    )

    real_fsync_directory = boe.fsync_directory
    real_rename = os.rename

    def fail_on_storage_root(directory):
        if directory == storage_root:
            raise OSError("Simulated parent directory fsync failure")

        real_fsync_directory(directory)

    with (
        patch.object(
            boe,
            "fsync_directory",
            side_effect=fail_on_storage_root,
        ),
        patch.object(
            boe.os,
            "rename",
            wraps=real_rename,
        ) as mock_rename,
    ):
        with pytest.raises(
            AcquisitionCommitDurabilityError,
            match="durability could not be confirmed",
        ) as exc_info:
            persist_iadb_acquisition(
                csv_content=sample_csv,
                config=config,
                config_hash=config_hash,
                request_params=VALID_REQUEST_PARAMS,
            )

    final_directory = exc_info.value.final_directory

    assert mock_rename.call_count == 1
    assert final_directory.parent == storage_root
    assert final_directory.is_dir()
    assert (
        final_directory / "original_data.csv"
    ).read_bytes() == sample_csv
    assert (final_directory / "manifest.json").is_file()

    manifest = json.loads(
        (final_directory / "manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["status"] == "success"
    assert manifest["dataset_ids"] == ["UK_BANK_RATE"]

    temporary_directories = list(
        storage_root.glob(".acquisition_tmp_*")
    )

    assert temporary_directories == []


def test_persist_iadb_acquisition_rejects_invalid_sha256(
    bank_rate_config,
    sample_csv,
):
    """Reject a configuration hash containing invalid characters."""

    config, _ = bank_rate_config

    with pytest.raises(ValueError, match="hexadecimal SHA-256"):
        persist_iadb_acquisition(
            csv_content=sample_csv,
            config=config,
            config_hash="z" * 64,
            request_params=VALID_REQUEST_PARAMS,
        )


def test_persist_iadb_acquisition_rejects_wrong_series_code(
    bank_rate_config,
    sample_csv,
):
    """Reject request parameters for a different series."""

    config, config_hash = bank_rate_config

    request_params = {
        **VALID_REQUEST_PARAMS,
        "SeriesCodes": "IUDSOIA",
    }

    with pytest.raises(ValueError, match="does not match"):
        persist_iadb_acquisition(
            csv_content=sample_csv,
            config=config,
            config_hash=config_hash,
            request_params=request_params,
        )


def test_persist_iadb_acquisition_rejects_missing_request_parameters(
    bank_rate_config,
    sample_csv,
):
    """Reject request parameters without required date fields."""

    config, config_hash = bank_rate_config

    with pytest.raises(ValueError, match="Missing required"):
        persist_iadb_acquisition(
            csv_content=sample_csv,
            config=config,
            config_hash=config_hash,
            request_params={"SeriesCodes": "IUDBEDR"},
        )

@pytest.mark.parametrize(
    "request_params",
    [
        {
            "SeriesCodes": "IUDBEDR",
            "Dateto": "31/Jan/2025",
        },
        {
            "SeriesCodes": "IUDBEDR",
            "Datefrom": "01/Jan/2025",
        },
        {
            "SeriesCodes": "IUDBEDR",
            "Datefrom": "01/Jan/2025",
            "Dateto": "now",
        },
    ],
    ids=[
        "missing-date-from",
        "missing-date-to",
        "dateto-now",
    ],
)
def test_persist_iadb_acquisition_rejects_missing_or_non_explicit_dates(
    bank_rate_config,
    sample_csv,
    request_params,
):
    """Reject missing dates and non-explicit end dates."""

    config, config_hash = bank_rate_config

    with pytest.raises(ValueError):
        persist_iadb_acquisition(
            csv_content=sample_csv,
            config=config,
            config_hash=config_hash,
            request_params=request_params,
        )

def test_persist_iadb_acquisition_rejects_non_string_parameters(
    bank_rate_config,
    sample_csv,
):
    """Reject request parameters containing non-string values."""

    config, config_hash = bank_rate_config

    request_params = {
        **VALID_REQUEST_PARAMS,
        "Datefrom": 20250101,
    }

    with pytest.raises(ValueError, match="must be strings"):
        persist_iadb_acquisition(
            csv_content=sample_csv,
            config=config,
            config_hash=config_hash,
            request_params=request_params,
        )


def test_persist_iadb_acquisition_calls_fsync(
    tmp_path,
    monkeypatch,
    bank_rate_config,
    sample_csv,
):
    """Verify that files and directories are synchronised."""

    monkeypatch.setattr(boe, "PROJECT_ROOT", tmp_path)

    config, config_hash = bank_rate_config

    with patch(
        "scripts.acquire_boe_data.os.fsync",
        wraps=os.fsync,
    ) as mock_fsync:
        persist_iadb_acquisition(
            csv_content=sample_csv,
            config=config,
            config_hash=config_hash,
            request_params=VALID_REQUEST_PARAMS,
        )

    assert mock_fsync.call_count >= 4

def test_persist_iadb_acquisition_supports_sonia(
    tmp_path,
    monkeypatch,
    sonia_config,
    sonia_sample_csv,
):
    """Verify that SONIA acquisitions use their configured identity."""

    monkeypatch.setattr(boe, "PROJECT_ROOT", tmp_path)

    config, config_hash = sonia_config

    request_params = {
        "SeriesCodes": "IUDSOIA",
        "Datefrom": "01/Jan/2025",
        "Dateto": "31/Jan/2025",
    }

    acquisition_directory = persist_iadb_acquisition(
        csv_content=sonia_sample_csv,
        config=config,
        config_hash=config_hash,
        request_params=request_params,
    )

    expected_directory = (
        tmp_path
        / "data"
        / "raw"
        / "macro"
        / "bank_of_england"
        / "uk_interest_rates"
        / "sonia"
    )

    assert acquisition_directory.parent == expected_directory
    assert acquisition_directory.is_dir()

    original_file = acquisition_directory / "original_data.csv"
    manifest_file = acquisition_directory / "manifest.json"

    assert original_file.read_bytes() == sonia_sample_csv

    manifest = json.loads(manifest_file.read_text())

    assert manifest["provider"] == "bank_of_england"
    assert manifest["dataset_ids"] == ["UK_SONIA"]
    assert manifest["request_parameters"]["SeriesCodes"] == "IUDSOIA"


def test_persist_iadb_acquisition_records_sonia_sha256(
    tmp_path,
    monkeypatch,
    sonia_config,
    sonia_sample_csv,
):
    """Verify the SHA-256 checksum of the persisted SONIA CSV."""

    monkeypatch.setattr(boe, "PROJECT_ROOT", tmp_path)

    config, config_hash = sonia_config

    request_params = {
        "SeriesCodes": "IUDSOIA",
        "Datefrom": "01/Jan/2025",
        "Dateto": "31/Jan/2025",
    }

    acquisition_directory = persist_iadb_acquisition(
        csv_content=sonia_sample_csv,
        config=config,
        config_hash=config_hash,
        request_params=request_params,
    )

    original_file = acquisition_directory / "original_data.csv"
    manifest_file = acquisition_directory / "manifest.json"

    manifest = json.loads(manifest_file.read_text())

    expected_sha256 = hashlib.sha256(
        sonia_sample_csv
    ).hexdigest()

    assert manifest["acquired_file"]["sha256"] == expected_sha256
    assert hashlib.sha256(original_file.read_bytes()).hexdigest() == expected_sha256

@pytest.mark.parametrize(
    "size_bytes",
    [0, -1, -100],
)
def test_acquired_file_metadata_rejects_invalid_size(size_bytes):
    """Reject zero or negative acquired file sizes."""

    with pytest.raises(ValueError):
        boe.AcquiredFileMetadata(
            file_name="original_data.csv",
            format="csv",
            size_bytes=size_bytes,
            sha256="a" * 64,
        )


@pytest.mark.parametrize(
    "sha256",
    [
        "",
        "a" * 63,
        "a" * 65,
        "g" * 64,
        "z" * 64,
    ],
)
def test_acquired_file_metadata_rejects_invalid_sha256(sha256):
    """Reject invalid SHA-256 digests."""

    with pytest.raises(ValueError):
        boe.AcquiredFileMetadata(
            file_name="original_data.csv",
            format="csv",
            size_bytes=100,
            sha256=sha256,
        )


def test_acquired_file_metadata_accepts_valid_metadata():
    """Accept valid acquired file metadata."""

    metadata = boe.AcquiredFileMetadata(
        file_name="original_data.csv",
        format="csv",
        size_bytes=100,
        sha256="a" * 64,
    )

    assert metadata.size_bytes == 100
    assert metadata.sha256 == "a" * 64


@pytest.mark.parametrize(
    "configuration_sha256",
    [
        "",
        "a" * 63,
        "a" * 65,
        "g" * 64,
        "z" * 64,
    ],
)
def test_acquisition_manifest_rejects_invalid_configuration_sha256(
    configuration_sha256,
):
    """Reject invalid configuration SHA-256 digests."""

    with pytest.raises(ValueError):
        boe.AcquisitionManifest(
            manifest_version="1.0",
            acquisition_id="20261103T120000Z_12345678",
            status="success",
            provider="bank_of_england",
            dataset_ids=["UK_BANK_RATE"],
            source_endpoint=boe.BOE_IADB_ENDPOINT,
            request_parameters=VALID_REQUEST_PARAMS,
            retrieved_at_utc=boe.datetime.now(boe.timezone.utc),
            configuration_sha256=configuration_sha256,
            acquired_file={
                "file_name": "original_data.csv",
                "format": "csv",
                "size_bytes": 100,
                "sha256": "b" * 64,
            },
        )


def test_acquisition_manifest_accepts_valid_configuration_sha256():
    """Accept a valid configuration SHA-256 digest."""

    manifest = boe.AcquisitionManifest(
        manifest_version="1.0",
        acquisition_id="20261103T120000Z_12345678",
        status="success",
        provider="bank_of_england",
        dataset_ids=["UK_BANK_RATE"],
        source_endpoint=boe.BOE_IADB_ENDPOINT,
        request_parameters=VALID_REQUEST_PARAMS,
        retrieved_at_utc=boe.datetime.now(boe.timezone.utc),
        configuration_sha256="a" * 64,
        acquired_file={
            "file_name": "original_data.csv",
            "format": "csv",
            "size_bytes": 100,
            "sha256": "b" * 64,
        },
    )

    assert manifest.configuration_sha256 == "a" * 64

@pytest.mark.parametrize(
    ("date_from", "date_to"),
    [
        ("2025-01-01", "31/Jan/2025"),
        ("01/Jan/2025", "2025-01-31"),
        ("31/Feb/2025", "01/Mar/2025"),
        ("01/Jan/2025", "29/Feb/2025"),
        ("32/Jan/2025", "01/Feb/2025"),
        ("01/Jan/2025", "31/Apr/2025"),
        ("01/Jan/2025", "01/Jan/25"),
    ],
)
def test_persist_iadb_acquisition_rejects_invalid_date_parameters(
    bank_rate_config,
    sample_csv,
    date_from,
    date_to,
):
    """Reject invalid or incorrectly formatted request dates."""

    config, config_hash = bank_rate_config

    request_params = {
        "SeriesCodes": "IUDBEDR",
        "Datefrom": date_from,
        "Dateto": date_to,
    }

    with pytest.raises(ValueError):
        persist_iadb_acquisition(
            csv_content=sample_csv,
            config=config,
            config_hash=config_hash,
            request_params=request_params,
        )


def test_persist_iadb_acquisition_rejects_date_from_after_date_to(
    bank_rate_config,
    sample_csv,
):
    """Reject a request whose start date follows its end date."""

    config, config_hash = bank_rate_config

    request_params = {
        "SeriesCodes": "IUDBEDR",
        "Datefrom": "02/Feb/2025",
        "Dateto": "01/Feb/2025",
    }

    with pytest.raises(ValueError):
        persist_iadb_acquisition(
            csv_content=sample_csv,
            config=config,
            config_hash=config_hash,
            request_params=request_params,
        )


def test_persist_iadb_acquisition_rejects_single_digit_day(
    bank_rate_config,
    sample_csv,
):
    """Reject dates that do not use a two-digit day."""

    config, config_hash = bank_rate_config

    request_params = {
        "SeriesCodes": "IUDBEDR",
        "Datefrom": "1/Jan/2025",
        "Dateto": "31/Jan/2025",
    }

    with pytest.raises(ValueError):
        persist_iadb_acquisition(
            csv_content=sample_csv,
            config=config,
            config_hash=config_hash,
            request_params=request_params,
        )


def test_persist_iadb_acquisition_accepts_equal_dates(
    bank_rate_config,
    sample_csv,
):
    """Accept a request whose start and end dates are identical."""

    config, config_hash = bank_rate_config

    request_params = {
        "SeriesCodes": "IUDBEDR",
        "Datefrom": "01/Jan/2025",
        "Dateto": "01/Jan/2025",
    }

    result = persist_iadb_acquisition(
        csv_content=sample_csv,
        config=config,
        config_hash=config_hash,
        request_params=request_params,
    )

    assert result is not None