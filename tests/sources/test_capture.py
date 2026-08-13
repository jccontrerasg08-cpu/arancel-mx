import json

from arancel_mx.sources.capture import capture_document


META = {
    "source_id": "snice-nico",
    "kind": "nico_current",
    "observed_at": "2026-08-09",
    "source_url": "https://www.snice.gob.mx/nico.xlsx",
    "filename": "nico.xlsx",
}


def test_changed_bytes_create_distinct_captures(tmp_path):
    first = capture_document(b"one", META, tmp_path)
    second = capture_document(b"two", META, tmp_path)

    assert first.path != second.path
    assert first.path.exists() and second.path.exists()
    assert json.loads(first.manifest_path.read_text("utf-8"))["sha256"] == first.sha256


def test_identical_capture_is_idempotent(tmp_path):
    assert capture_document(b"one", META, tmp_path) == capture_document(
        b"one", META, tmp_path
    )


def test_identical_capture_ignores_retrieved_at_drift(tmp_path):
    first = capture_document(b"one", {**META, "retrieved_at": "2026-08-09T12:00:00Z"}, tmp_path)
    second = capture_document(b"one", {**META, "retrieved_at": "2026-08-09T18:00:00Z"}, tmp_path)

    assert first.path == second.path
    assert first.sha256 == second.sha256
    assert first.metadata["retrieved_at"] == "2026-08-09T12:00:00Z"
    assert second.metadata["retrieved_at"] == "2026-08-09T12:00:00Z"
