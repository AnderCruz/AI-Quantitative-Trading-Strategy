"""Tests for the Bank of England gilt yield curve archive connector."""

import threading
from concurrent.futures import ThreadPoolExecutor
import io
import json
import sys
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from scripts import acquire_boe_yield_curves as module


# ---------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------


@pytest.fixture
def valid_zip():
    """Create a small valid ZIP archive containing Excel workbooks."""

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("workbook_1979_1984.xlsx", b"workbook data 1")
        archive.writestr("workbook_1985_1989.xlsx", b"workbook data 2")

    return buffer.getvalue()


@pytest.fixture
def configurations():
    """Load the approved project configurations."""

    configs, hashes = module.load_and_validate_configurations()
    return configs, hashes


@pytest.fixture
def mocked_response(valid_zip):
    response = Mock()
    response.content = valid_zip
    response.raise_for_status.return_value = None
    return response


# ---------------------------------------------------------------------
# Configuration loading and validation
# ---------------------------------------------------------------------


def test_load_both_approved_configurations(configurations):
    configs, hashes = configurations

    assert set(configs) == set(module.DATASET_IDS)
    assert set(hashes) == set(module.DATASET_IDS)


def test_configuration_hashes_are_sha256(configurations):
    _, hashes = configurations

    for digest in hashes.values():
        assert len(digest) == 64
        assert all(character in "0123456789abcdef" for character in digest.lower())


def test_2y_configuration_has_correct_identity(configurations):
    configs, _ = configurations

    config = configs["UK_GILT_NOMINAL_2Y"]

    assert config.dataset.dataset_id == "UK_GILT_NOMINAL_2Y"
    assert config.provider.maturity_years == 2


def test_10y_configuration_has_correct_identity(configurations):
    configs, _ = configurations

    config = configs["UK_GILT_NOMINAL_10Y"]

    assert config.dataset.dataset_id == "UK_GILT_NOMINAL_10Y"
    assert config.provider.maturity_years == 10


def test_both_configurations_share_provider_directory(configurations):
    configs, _ = configurations

    assert (
        configs["UK_GILT_NOMINAL_2Y"].storage.provider_directory
        == configs["UK_GILT_NOMINAL_10Y"].storage.provider_directory
    )


def test_configuration_loader_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        module.load_yield_curve_config(tmp_path / "missing.yaml")


def test_configuration_loader_rejects_invalid_yaml(tmp_path):
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text("dataset: [invalid", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid yield curve configuration"):
        module.load_yield_curve_config(config_path)


def test_configuration_loader_rejects_non_mapping_root(tmp_path):
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text("- item_one\n- item_two\n", encoding="utf-8")

    with pytest.raises(ValueError, match="root must be a mapping"):
        module.load_yield_curve_config(config_path)


def test_configuration_loader_rejects_unknown_fields(tmp_path):
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text(
        """
dataset:
  dataset_id: TEST
  dataset_name: Test
  description: Test
  unexpected_field: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid yield curve configuration"):
        module.load_yield_curve_config(config_path)


def test_configuration_loader_rejects_wrong_dataset_identity(
    monkeypatch,
    tmp_path,
):
    configs = list(module.CONFIG_PATHS.values())

    monkeypatch.setattr(
        module,
        "CONFIG_PATHS",
        {
            "WRONG_DATASET_ID": configs[0],
        },
    )

    with pytest.raises(ValueError, match="Expected WRONG_DATASET_ID"):
        module.load_and_validate_configurations()


# ---------------------------------------------------------------------
# ZIP archive validation
# ---------------------------------------------------------------------


def test_valid_zip_archive_returns_excel_workbooks(valid_zip):
    result = module.validate_zip_archive(valid_zip)

    assert len(result) == 2
    assert all(name.endswith(".xlsx") for name in result)


@pytest.mark.parametrize("content", [b"", None])
def test_zip_validation_rejects_empty_content(content):
    with pytest.raises(ValueError, match="empty"):
        module.validate_zip_archive(content)


def test_zip_validation_rejects_invalid_signature():
    with pytest.raises(ValueError, match="ZIP signature"):
        module.validate_zip_archive(b"NOT_A_ZIP_FILE")


def test_zip_validation_rejects_corrupted_archive():
    with pytest.raises(ValueError, match="valid ZIP"):
        module.validate_zip_archive(b"PK\x03\x04corrupted content")


def test_zip_validation_rejects_archive_without_excel_files():
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("readme.txt", "No workbooks")

    with pytest.raises(ValueError, match="No Excel workbooks"):
        module.validate_zip_archive(buffer.getvalue())


@pytest.mark.parametrize(
    "member_name",
    [
        "../outside.xlsx",
        "folder/../../outside.xlsx",
        "/absolute/path.xlsx",
    ],
)
def test_zip_validation_rejects_unsafe_member_paths(member_name):
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member_name, b"workbook")

    with pytest.raises(ValueError, match="Unsafe archive paths"):
        module.validate_zip_archive(buffer.getvalue())


def test_zip_validation_rejects_corrupted_member():
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("workbook.xlsx", b"original workbook content")

    corrupted = bytearray(buffer.getvalue())
    content_position = corrupted.find(b"original workbook content")
    corrupted[content_position] ^= 0xFF

    with pytest.raises(ValueError, match="Corrupted ZIP member"):
        module.validate_zip_archive(bytes(corrupted))


# ---------------------------------------------------------------------
# HTTP acquisition
# ---------------------------------------------------------------------


def test_fetch_archive_success(monkeypatch, mocked_response, valid_zip):
    get_mock = Mock(return_value=mocked_response)
    monkeypatch.setattr(module.requests, "get", get_mock)

    result = module.fetch_yield_curve_archive(timeout=30)

    assert result == valid_zip

    get_mock.assert_called_once()

    args, kwargs = get_mock.call_args

    assert args[0] == module.BOE_ARCHIVE_URL
    assert kwargs["timeout"] == 30
    assert "User-Agent" in kwargs["headers"]


@pytest.mark.parametrize("timeout", [0, -1, True, 1.5, "30"])
def test_fetch_archive_rejects_invalid_timeout(timeout):
    with pytest.raises(ValueError, match="positive integer"):
        module.fetch_yield_curve_archive(timeout=timeout)


def test_fetch_archive_handles_timeout(monkeypatch):
    monkeypatch.setattr(
        module.requests,
        "get",
        Mock(side_effect=requests.exceptions.Timeout),
    )

    with pytest.raises(RuntimeError, match="timed out"):
        module.fetch_yield_curve_archive()


def test_fetch_archive_handles_http_error(monkeypatch):
    response = Mock()
    response.raise_for_status.side_effect = requests.exceptions.HTTPError("404")

    monkeypatch.setattr(module.requests, "get", Mock(return_value=response))

    with pytest.raises(RuntimeError, match="HTTP error"):
        module.fetch_yield_curve_archive()


def test_fetch_archive_handles_connection_error(monkeypatch):
    monkeypatch.setattr(
        module.requests,
        "get",
        Mock(side_effect=requests.exceptions.ConnectionError("Connection failed")),
    )

    with pytest.raises(RuntimeError, match="request failed"):
        module.fetch_yield_curve_archive()


def test_fetch_archive_rejects_invalid_download(monkeypatch):
    response = Mock()
    response.content = b"invalid content"
    response.raise_for_status.return_value = None

    monkeypatch.setattr(module.requests, "get", Mock(return_value=response))

    with pytest.raises(ValueError, match="ZIP signature"):
        module.fetch_yield_curve_archive()


# ---------------------------------------------------------------------
# SHA-256 and file integrity
# ---------------------------------------------------------------------


def test_calculate_sha256_matches_standard_library():
    import hashlib

    content = b"test content"

    assert module.calculate_sha256(content) == hashlib.sha256(content).hexdigest()


def test_calculate_sha256_returns_64_character_digest():
    digest = module.calculate_sha256(b"yield curve archive")

    assert len(digest) == 64


# ---------------------------------------------------------------------
# Raw persistence
# ---------------------------------------------------------------------


def test_persistence_creates_shared_archive_and_manifest(
    monkeypatch,
    tmp_path,
    configurations,
    valid_zip,
):
    configs, hashes = configurations

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    result = module.persist_yield_curve_archive(
        valid_zip,
        configs,
        hashes,
    )

    assert result.is_dir()
    assert (result / module.ARCHIVE_FILENAME).is_file()
    assert (result / "manifest.json").is_file()

    assert (result / module.ARCHIVE_FILENAME).read_bytes() == valid_zip


def test_persistence_manifest_contains_both_datasets(
    monkeypatch,
    tmp_path,
    configurations,
    valid_zip,
):
    configs, hashes = configurations

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    result = module.persist_yield_curve_archive(valid_zip, configs, hashes)

    manifest = json.loads((result / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["dataset_ids"] == module.DATASET_IDS
    assert manifest["configuration_sha256"] == hashes
    assert manifest["provider"] == "bank_of_england"
    assert manifest["status"] == "success"


def test_persistence_manifest_preserves_original_archive_metadata(
    monkeypatch,
    tmp_path,
    configurations,
    valid_zip,
):
    configs, hashes = configurations

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    result = module.persist_yield_curve_archive(valid_zip, configs, hashes)

    manifest = json.loads((result / "manifest.json").read_text(encoding="utf-8"))
    metadata = manifest["acquired_file"]

    assert metadata["file_name"] == "original_data.zip"
    assert metadata["format"] == "zip"
    assert metadata["size_bytes"] == len(valid_zip)
    assert metadata["sha256"] == module.calculate_sha256(valid_zip)
    assert metadata["workbook_count"] == 2
    assert manifest["transformation_performed"] is False


def test_persistence_uses_one_shared_acquisition_directory(
    monkeypatch,
    tmp_path,
    configurations,
    valid_zip,
):
    configs, hashes = configurations

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    result = module.persist_yield_curve_archive(valid_zip, configs, hashes)

    assert result.parent == (
        tmp_path
        / "data"
        / "raw"
        / "macro"
        / configs["UK_GILT_NOMINAL_2Y"].storage.provider_directory
        / "yield_curve_archive"
    )


def test_persistence_rejects_missing_dataset_configuration(
    monkeypatch,
    tmp_path,
    configurations,
    valid_zip,
):
    configs, hashes = configurations

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    incomplete_configs = {
        "UK_GILT_NOMINAL_2Y": configs["UK_GILT_NOMINAL_2Y"]
    }

    with pytest.raises(ValueError, match="Both approved dataset configurations"):
        module.persist_yield_curve_archive(valid_zip, incomplete_configs, hashes)


def test_persistence_rejects_missing_configuration_hash(
    monkeypatch,
    tmp_path,
    configurations,
    valid_zip,
):
    configs, hashes = configurations

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    incomplete_hashes = {
        "UK_GILT_NOMINAL_2Y": hashes["UK_GILT_NOMINAL_2Y"]
    }

    with pytest.raises(ValueError, match="Both configuration hashes"):
        module.persist_yield_curve_archive(valid_zip, configs, incomplete_hashes)


@pytest.mark.parametrize(
    "invalid_hash",
    [
        "",
        "invalid",
        "a" * 63,
        "g" * 64,
    ],
)
def test_persistence_rejects_invalid_configuration_hash(
    monkeypatch,
    tmp_path,
    configurations,
    valid_zip,
    invalid_hash,
):
    configs, hashes = configurations

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    invalid_hashes = hashes.copy()
    invalid_hashes["UK_GILT_NOMINAL_2Y"] = invalid_hash

    with pytest.raises(ValueError, match="Invalid configuration SHA-256"):
        module.persist_yield_curve_archive(valid_zip, configs, invalid_hashes)


def test_persistence_rejects_configuration_identity_mismatch(
    monkeypatch,
    tmp_path,
    configurations,
    valid_zip,
):
    configs, hashes = configurations

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    mismatched = configs.copy()
    mismatched["UK_GILT_NOMINAL_2Y"] = configs["UK_GILT_NOMINAL_10Y"]

    with pytest.raises(ValueError, match="Configuration identity mismatch"):
        module.persist_yield_curve_archive(valid_zip, mismatched, hashes)


def test_persistence_cleans_temporary_directory_on_write_failure(
    monkeypatch,
    tmp_path,
    configurations,
    valid_zip,
):
    configs, hashes = configurations

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    def fail_write(*args, **kwargs):
        raise OSError("Simulated write failure")

    monkeypatch.setattr(module, "write_bytes_durably", fail_write)

    with pytest.raises(OSError, match="Simulated write failure"):
        module.persist_yield_curve_archive(valid_zip, configs, hashes)

    storage_root = (
        tmp_path
        / "data"
        / "raw"
        / "macro"
        / configs["UK_GILT_NOMINAL_2Y"].storage.provider_directory
        / "yield_curve_archive"
    )

    assert storage_root.is_dir()
    assert list(storage_root.iterdir()) == []

def test_persistence_cleans_temporary_directory_on_commit_failure(
    monkeypatch,
    tmp_path,
    configurations,
    valid_zip,
):
    configs, hashes = configurations

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    def fail_commit(source, destination):
        raise OSError(5, "Simulated commit failure")

    monkeypatch.setattr(
        module,
        "rename_directory_noreplace",
        fail_commit,
    )

    with pytest.raises(OSError, match="Simulated commit failure"):
        module.persist_yield_curve_archive(valid_zip, configs, hashes)

    storage_root = (
        tmp_path
        / "data"
        / "raw"
        / "macro"
        / configs["UK_GILT_NOMINAL_2Y"].storage.provider_directory
        / "yield_curve_archive"
    )

    assert storage_root.is_dir()
    assert list(storage_root.iterdir()) == []


def test_rename_directory_noreplace_rejects_existing_destination(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"

    source.mkdir()
    destination.mkdir()

    (source / "source.txt").write_text("new data", encoding="utf-8")
    (destination / "original.txt").write_text(
        "original data",
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError):
        module.rename_directory_noreplace(source, destination)

    assert source.is_dir()
    assert (source / "source.txt").read_text(encoding="utf-8") == "new data"

    assert destination.is_dir()
    assert (destination / "original.txt").read_text(
        encoding="utf-8"
    ) == "original data"


def test_persistence_preserves_destination_created_during_commit(
    monkeypatch,
    tmp_path,
    configurations,
    valid_zip,
):
    configs, hashes = configurations

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    def simulate_collision(source, destination):
        destination.mkdir()
        (destination / "original.txt").write_text(
            "original data",
            encoding="utf-8",
        )

        module.rename_directory_noreplace(source, destination)

    monkeypatch.setattr(
        module,
        "rename_directory_noreplace",
        simulate_collision,
    )

    with pytest.raises(FileExistsError):
        module.persist_yield_curve_archive(valid_zip, configs, hashes)

    storage_root = (
        tmp_path
        / "data"
        / "raw"
        / "macro"
        / configs["UK_GILT_NOMINAL_2Y"].storage.provider_directory
        / "yield_curve_archive"
    )

    committed_directories = list(storage_root.glob("acquisition_*"))

    assert len(committed_directories) == 1

    destination = committed_directories[0]

    assert (destination / "original.txt").read_text(
        encoding="utf-8"
    ) == "original data"

    assert not (destination / module.ARCHIVE_FILENAME).exists()

    temporary_directories = list(
        storage_root.glob(".acquisition_tmp_*")
    )

    assert temporary_directories == []


def test_concurrent_directory_commits_allow_only_one_winner(tmp_path):
    source_a = tmp_path / "source_a"
    source_b = tmp_path / "source_b"
    destination = tmp_path / "destination"

    source_a.mkdir()
    source_b.mkdir()

    (source_a / "origin.txt").write_text("A", encoding="utf-8")
    (source_b / "origin.txt").write_text("B", encoding="utf-8")

    barrier = threading.Barrier(2)

    def attempt_commit(source):
        barrier.wait()

        try:
            module.rename_directory_noreplace(source, destination)
            return "success"
        except FileExistsError:
            return "collision"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                attempt_commit,
                [source_a, source_b],
            )
        )

    assert results.count("success") == 1
    assert results.count("collision") == 1

    assert destination.is_dir()

    committed_origin = (destination / "origin.txt").read_text(
        encoding="utf-8"
    )

    assert committed_origin in {"A", "B"}

    remaining_sources = [
        source
        for source in (source_a, source_b)
        if source.exists()
    ]

    assert len(remaining_sources) == 1


def test_persistence_reports_post_commit_durability_failure(
    monkeypatch,
    tmp_path,
    configurations,
    valid_zip,
):
    configs, hashes = configurations

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    calls = {"count": 0}

    def fail_second_fsync(directory):
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("Simulated directory fsync failure")

    monkeypatch.setattr(module, "fsync_directory", fail_second_fsync)

    with pytest.raises(RuntimeError, match="committed"):
        module.persist_yield_curve_archive(valid_zip, configs, hashes)

    storage_root = (
        tmp_path
        / "data"
        / "raw"
        / "macro"
        / configs["UK_GILT_NOMINAL_2Y"].storage.provider_directory
        / "yield_curve_archive"
    )

    committed_directories = list(storage_root.glob("acquisition_*"))

    assert len(committed_directories) == 1
    assert (committed_directories[0] / module.ARCHIVE_FILENAME).is_file()


# ---------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------


def test_cli_dry_run_does_not_persist(monkeypatch, capsys, valid_zip):
    configs = {"config": "loaded"}
    hashes = {"hash": "loaded"}

    monkeypatch.setattr(sys, "argv", ["acquire_boe_yield_curves.py"])
    monkeypatch.setattr(
        module,
        "load_and_validate_configurations",
        Mock(return_value=(configs, hashes)),
    )
    monkeypatch.setattr(
        module,
        "fetch_yield_curve_archive",
        Mock(return_value=valid_zip),
    )

    persist_mock = Mock()
    monkeypatch.setattr(module, "persist_yield_curve_archive", persist_mock)

    module.main()

    output = capsys.readouterr().out

    assert "DRY RUN COMPLETED" in output
    assert "No files were written to Raw." in output
    persist_mock.assert_not_called()


def test_cli_persist_flag_calls_persistence(
    monkeypatch,
    capsys,
    valid_zip,
    tmp_path,
):
    configs = {"config": "loaded"}
    hashes = {"hash": "loaded"}

    monkeypatch.setattr(
        sys,
        "argv",
        ["acquire_boe_yield_curves.py", "--persist"],
    )
    monkeypatch.setattr(
        module,
        "load_and_validate_configurations",
        Mock(return_value=(configs, hashes)),
    )
    monkeypatch.setattr(
        module,
        "fetch_yield_curve_archive",
        Mock(return_value=valid_zip),
    )

    persist_mock = Mock(return_value=tmp_path / "acquisition_test")
    monkeypatch.setattr(module, "persist_yield_curve_archive", persist_mock)

    module.main()

    output = capsys.readouterr().out

    assert "PERSISTENCE COMPLETED" in output
    persist_mock.assert_called_once_with(
        content=valid_zip,
        configurations=configs,
        configuration_hashes=hashes,
    )


# ---------------------------------------------------------------------
# IADB connector regression
# ---------------------------------------------------------------------


def test_iadb_connector_module_remains_importable():
    from scripts import acquire_boe_data

    assert hasattr(acquire_boe_data, "fetch_iadb_csv")
    assert hasattr(acquire_boe_data, "persist_iadb_acquisition")
    assert hasattr(acquire_boe_data, "load_iadb_config")
