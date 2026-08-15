from __future__ import annotations

import json
from pathlib import Path
import socket

import pytest
import requests

from arancel_mx.cli import main
import arancel_mx.consumer.manager as manager_module
from tests.fixtures.consumer.create_consumer_fixture import create_consumer_release_fixture


TAG = "data-2026.08.11"


def _json_stdout(capsys) -> object:
    captured = capsys.readouterr()
    assert captured.err == ""
    return json.loads(captured.out)


def test_full_consumer_cli_sequence_survives_strict_offline_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    fixture_root = tmp_path / "fixture source ñ"
    release, files = create_consumer_release_fixture(fixture_root, tag=TAG)

    class ReleaseClient:
        def __init__(self, session, *, timeout: float) -> None:
            self.session = session
            self.timeout = timeout

        def latest(self):
            return release

        def version(self, tag: str):
            assert tag == TAG
            return release

        def list(self):
            return (release,)

    download_calls: list[str] = []

    def fake_download(session, url: str, destination: Path, *, timeout: float) -> int:
        name = url.rstrip("/").split("/")[-1]
        download_calls.append(name)
        body = files[name]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(body)
        return len(body)

    monkeypatch.setattr(manager_module, "GitHubReleaseClient", ReleaseClient)
    monkeypatch.setattr(manager_module, "stream_download", fake_download)
    cache_dir = tmp_path / "cache with spaces ñ"
    monkeypatch.setenv("ARANCEL_MX_CACHE_DIR", str(cache_dir))
    monkeypatch.delenv("ARANCEL_MX_OFFLINE", raising=False)

    assert main([
        "data",
        "download",
        "--dataset",
        TAG,
        "--format",
        "json",
    ]) == 0
    downloaded = _json_stdout(capsys)
    assert downloaded["status"] == "verified"
    assert Path(downloaded["path"]).is_file()
    assert download_calls == ["manifest.json", "SHA256SUMS", "arancel_mx.duckdb"]

    monkeypatch.setenv("ARANCEL_MX_OFFLINE", "1")

    def forbidden_request(*args: object, **kwargs: object) -> object:
        raise AssertionError("requests network call attempted in strict offline sequence")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("socket connection attempted in strict offline sequence")

    monkeypatch.setattr(requests.Session, "request", forbidden_request)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    assert main(["data", "status", "--dataset", TAG, "--format", "json"]) == 0
    status = _json_stdout(capsys)
    assert status["offline"] is True
    assert status["selected"] == TAG
    assert status["local_latest"] == TAG
    assert status["remote_latest"] is None

    assert main(["data", "verify", "--dataset", TAG, "--format", "json"]) == 0
    verified = _json_stdout(capsys)
    assert verified["release_verified"] is True
    assert verified["dataset_version"] == "2026.08.11"

    assert main(["lookup", "01012101", "--dataset", TAG, "--format", "json"]) == 0
    lookup = _json_stdout(capsys)
    assert lookup["code"] == "01012101"
    assert lookup["level"] == "fraccion8"

    assert main([
        "search",
        "raza pura",
        "--dataset",
        TAG,
        "--format",
        "json",
    ]) == 0
    search = _json_stdout(capsys)
    assert search[0]["record"]["code"] == "010121"

    assert main(["parent", "01012101", "--dataset", TAG, "--format", "json"]) == 0
    parent = _json_stdout(capsys)
    assert parent["code"] == "010121"

    assert main(["children", "010121", "--dataset", TAG, "--format", "json"]) == 0
    children = _json_stdout(capsys)
    assert [row["code"] for row in children] == ["01012101"]

    assert main(["provenance", "01012101", "--dataset", TAG, "--format", "json"]) == 0
    provenance = _json_stdout(capsys)
    assert provenance[0]["source_document_id"] == "fixture-source"
    assert provenance[0]["is_primary"] is True

    assert main(["ficha", "01012101", "--dataset", TAG, "--format", "json"]) == 0
    card = _json_stdout(capsys)
    assert card["formatted_code"] == "0101.21.01"
    assert card["record"]["code"] == "01012101"
    assert card["section"]["roman"] == "I"
    assert card["section"]["source"] == "hs_section_grouping"
    assert [node["code"] for node in card["hierarchy"]] == [
        "01",
        "0101",
        "010121",
        "01012101",
    ]
    assert [child["code"] for child in card["children"]] == ["0101210100"]

    assert main(["suggest", "reproductores", "--dataset", TAG]) == 0
    suggest = capsys.readouterr()
    assert suggest.err == ""
    assert suggest.out.startswith(
        "This is not a classification. Retrieve-only matches from the official dataset."
    )
    assert "--- 1/1  01012101  score=330  confidence=1.0  scorer=1 ---" in suggest.out
    assert "Código      0101.21.01" in suggest.out
    assert "Notas nacionales  (none)" in suggest.out
    assert "WCO support  " in suggest.out
    assert "01_2022e.pdf" in suggest.out

    assert main(["chapters", "--dataset", TAG, "--format", "json"]) == 0
    chapters = _json_stdout(capsys)
    assert [row["code"] for row in chapters] == ["01"]

    assert main(["data", "path", "--dataset", TAG]) == 0
    path_capture = capsys.readouterr()
    assert path_capture.err == ""
    path = Path(path_capture.out.strip())
    assert path.is_file()
    assert "cache with spaces ñ" in str(path)

    assert main(["doctor", "--dataset", TAG, "--json"]) == 0
    doctor = _json_stdout(capsys)
    assert doctor["status"] == "HEALTHY"
    assert doctor["exit_code"] == 0
    doctor_checks = {item["name"]: item for item in doctor["checks"]}
    assert doctor_checks["verified_dataset"]["status"] == "pass"
    assert doctor_checks["duckdb_query"]["status"] == "pass"
    assert doctor_checks["offline_readiness"]["status"] == "pass"
    assert doctor_checks["network_release"]["status"] == "skip"
