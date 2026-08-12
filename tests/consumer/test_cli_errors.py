from __future__ import annotations

import json

import pytest
import requests

from arancel_mx import cli
from arancel_mx.consumer.errors import DatasetDownloadError, DatasetIntegrityError
import arancel_mx.consumer.cli as consumer_cli


def test_public_consumer_error_is_exit_two_without_traceback(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "run_consumer",
        lambda namespace: (_ for _ in ()).throw(DatasetIntegrityError("verified cache checksum mismatch")),
    )

    assert cli.main(["lookup", "01012101"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: verified cache checksum mismatch\n"
    assert "Traceback" not in captured.err


def test_unexpected_consumer_value_error_is_not_hidden(monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "run_consumer",
        lambda namespace: (_ for _ in ()).throw(ValueError("programming invariant broke")),
    )

    with pytest.raises(ValueError, match="programming invariant broke"):
        cli.main(["lookup", "01012101"])


def test_chained_requests_error_is_not_exposed_as_primary_contract(monkeypatch, capsys) -> None:
    def fail(namespace):
        cause = requests.ConnectionError("low-level socket detail")
        raise DatasetDownloadError("failed to query public data release metadata") from cause

    monkeypatch.setattr(cli, "run_consumer", fail)

    assert cli.main(["data", "status", "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert "failed to query public data release metadata" in captured.err
    assert "low-level socket detail" not in captured.err
    assert "ConnectionError" not in captured.err


def test_chained_json_error_is_not_exposed_as_primary_contract(monkeypatch, capsys) -> None:
    def fail(namespace):
        cause = json.JSONDecodeError("internal parser detail", "{", 0)
        raise DatasetIntegrityError("manifest contains invalid JSON") from cause

    monkeypatch.setattr(cli, "run_consumer", fail)

    assert cli.main(["data", "verify", "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert "manifest contains invalid JSON" in captured.err
    assert "internal parser detail" not in captured.err
    assert "JSONDecodeError" not in captured.err


def test_invalid_consumer_environment_is_mapped_to_actionable_public_error(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        consumer_cli,
        "resolve_config",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("ARANCEL_MX_TIMEOUT must be greater than zero")),
    )

    assert cli.main(["data", "status", "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid consumer configuration" in captured.err
    assert "ARANCEL_MX_TIMEOUT" in captured.err


def test_invalid_consumer_environment_is_mapped_for_query_commands(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        consumer_cli,
        "resolve_config",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("ARANCEL_MX_TIMEOUT must be greater than zero")),
    )
    monkeypatch.setattr(
        consumer_cli.Dataset,
        "latest",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("dataset access must follow validated config")),
    )

    assert cli.main(["lookup", "01012101"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid consumer configuration" in captured.err
    assert "ARANCEL_MX_TIMEOUT" in captured.err


def test_negative_search_limit_is_rejected_by_parser_before_dataset_access(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        consumer_cli,
        "Dataset",
        object(),
    )
    assert cli.main(["search", "raza", "--limit", "0"]) == 2
    captured = capsys.readouterr()
    assert "--limit" in captured.err
    assert "greater than zero" in captured.err
