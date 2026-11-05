"""Unit tests for the ONS CSV acquisition connector."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
import yaml

from scripts import acquire_ons_data as ons


@pytest.fixture
def project_root():
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def configs(project_root):
    inflation, inflation_hash = ons.load_ons_config(
        project_root / ons.CONFIG_PATHS["inflation"]
    )
    gdp, gdp_hash = ons.load_ons_config(project_root / ons.CONFIG_PATHS["gdp"])
    ons.validate_ons_config(inflation, "inflation")
    ons.validate_ons_config(gdp, "gdp")
    return {
        "inflation": (inflation, inflation_hash),
        "gdp": (gdp, gdp_hash),
    }


@pytest.fixture
def valid_csv():
    return (
        b"Date,Title,UK CPI ANNUAL RATE 00: ALL ITEMS 2015=100\n"
        b"2024 JAN,Jan 2024,4.0\n"
        b"2024 FEB,Feb 2024,3.8\n"
    )


@pytest.fixture
def mock_response(valid_csv):
    response = Mock()
    response.content = valid_csv
    response.raise_for_status.return_value = None
    return response


def test_load_both_approved_configurations(configs):
    inflation, _ = configs["inflation"]
    gdp, _ = configs["gdp"]

    assert set(inflation.dataset.dataset_ids) == {
        "UK_CPI", "UK_CORE_CPI", "UK_CPIH"
    }
    assert {item.series_code for item in inflation.series} == {
        "D7G7", "DKO8", "L55O"
    }
    assert set(gdp.dataset.dataset_ids) == {"UK_REAL_GDP", "UK_GDP_GROWTH"}
    assert {item.series_code for item in gdp.series} == {"ABMI", "IHYQ"}


@pytest.mark.parametrize(
    ("group", "expected_code", "expected_rows"),
    [
        ("inflation", "MM23", 3),
        ("gdp", "QNA", 2),
    ],
)
def test_group_configuration_is_validated(configs, group, expected_code, expected_rows):
    config, digest = configs[group]
    assert config.provider.dataset_code == expected_code
    assert len(config.series) == expected_rows
    assert len(digest) == 64


def test_configuration_loader_rejects_unknown_fields(tmp_path, project_root):
    source = project_root / ons.CONFIG_PATHS["inflation"]
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    data["unexpected"] = "not allowed"
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid ONS configuration"):
        ons.load_ons_config(path)


def test_configuration_loader_rejects_non_mapping_root(tmp_path):
    path = tmp_path / "invalid.yaml"
    path.write_text("- item\n", encoding="utf-8")

    with pytest.raises(ValueError, match="root must be a YAML mapping"):
        ons.load_ons_config(path)


def test_group_validation_rejects_wrong_group(configs):
    config, _ = configs["inflation"]
    with pytest.raises(ValueError, match="Unexpected ONS dataset code"):
        ons.validate_ons_config(config, "gdp")


def test_configuration_rejects_mismatched_series_mapping(project_root, tmp_path):
    source = project_root / ons.CONFIG_PATHS["inflation"]
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    data["series"][0]["dataset_id"] = "UK_NOT_APPROVED"
    path = tmp_path / "invalid_mapping.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid ONS configuration"):
        ons.load_ons_config(path)


def test_csv_validation_returns_header_and_row_counts(valid_csv):
    assert ons.validate_csv_content(valid_csv, "MM23") == (3, 2)


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"<!doctype html><html><body>Unavailable</body></html>",
        b"\xff\xfe\x00",
        b"OnlyOneColumn\nvalue\n",
        b"Date,Value\n",
    ],
)
def test_csv_validation_rejects_invalid_content(content):
    with pytest.raises(ValueError):
        ons.validate_csv_content(content, "MM23")


def test_fetch_csv_success(monkeypatch, mock_response):
    get = Mock(return_value=mock_response)
    monkeypatch.setattr(ons.requests, "get", get)

    content = ons.fetch_ons_csv("https://example.test/mm23.csv", "MM23")

    assert content == mock_response.content
    get.assert_called_once()
    assert get.call_args.kwargs["timeout"] == ons.DEFAULT_HTTP_TIMEOUT


@pytest.mark.parametrize("timeout", [0, -1, True, 1.5, "30"])
def test_fetch_csv_rejects_invalid_timeout(timeout):
    with pytest.raises(ValueError, match="Timeout"):
        ons.fetch_ons_csv("https://example.test/mm23.csv", "MM23", timeout)


def test_fetch_csv_handles_http_error(monkeypatch):
    response = Mock()
    response.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
    monkeypatch.setattr(ons.requests, "get", Mock(return_value=response))

    with pytest.raises(RuntimeError, match="HTTP error"):
        ons.fetch_ons_csv("https://example.test/mm23.csv", "MM23")


def test_fetch_csv_handles_timeout(monkeypatch):
    monkeypatch.setattr(
        ons.requests,
        "get",
        Mock(side_effect=requests.exceptions.Timeout("timeout")),
    )
    with pytest.raises(RuntimeError, match="timed out"):
        ons.fetch_ons_csv("https://example.test/mm23.csv", "MM23")


def test_persistence_writes_original_csv_and_manifest(
    monkeypatch, tmp_path, configs, valid_csv
):
    monkeypatch.setattr(ons, "PROJECT_ROOT", tmp_path)
    config, config_hash = configs["inflation"]

    destination = ons.persist_ons_acquisition(valid_csv, config, config_hash)

    assert destination.is_dir()
    assert (destination / "original_data.csv").read_bytes() == valid_csv
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["provider"] == "office_for_national_statistics"
    assert manifest["source_dataset_code"] == "MM23"
    assert set(manifest["dataset_ids"]) == {
        "UK_CPI", "UK_CORE_CPI", "UK_CPIH"
    }
    assert manifest["acquired_file"]["size_bytes"] == len(valid_csv)
    assert manifest["acquired_file"]["sha256"] == ons.calculate_sha256(valid_csv)
    assert manifest["transformation_performed"] is False


def test_persistence_rejects_invalid_configuration_hash(
    monkeypatch, tmp_path, configs, valid_csv
):
    monkeypatch.setattr(ons, "PROJECT_ROOT", tmp_path)
    config, _ = configs["inflation"]

    with pytest.raises(ValueError, match="configuration SHA-256"):
        ons.persist_ons_acquisition(valid_csv, config, "invalid")


def test_persistence_cleans_temporary_directory_after_write_failure(
    monkeypatch, tmp_path, configs, valid_csv
):
    monkeypatch.setattr(ons, "PROJECT_ROOT", tmp_path)
    config, config_hash = configs["inflation"]

    def fail_write(*args, **kwargs):
        raise OSError("simulated write failure")

    monkeypatch.setattr(ons, "write_bytes_durably", fail_write)

    with pytest.raises(OSError, match="simulated write failure"):
        ons.persist_ons_acquisition(valid_csv, config, config_hash)

    storage_root = (
        tmp_path / "data" / "raw" / "macro" / "ons" / "inflation"
    )
    assert list(storage_root.iterdir()) == []


def test_cli_default_mode_does_not_fetch_or_persist(monkeypatch):
    monkeypatch.setattr(
        ons,
        "load_group",
        lambda group: (Mock(
            provider=Mock(dataset_code="MM23"),
            dataset=Mock(dataset_ids=["UK_CPI"]),
            series=[],
        ), "a" * 64),
    )
    fetch = Mock(side_effect=AssertionError("network must not be called"))
    monkeypatch.setattr(ons, "fetch_ons_csv", fetch)
    monkeypatch.setattr("sys.argv", ["acquire_ons_data.py", "--group", "inflation"])

    ons.main()

    fetch.assert_not_called()


def test_cli_rejects_fetch_and_persist_together(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["acquire_ons_data.py", "--fetch", "--persist"],
    )
    with pytest.raises(SystemExit) as exc:
        ons.main()
    assert exc.value.code == 2
