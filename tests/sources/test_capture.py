import json

from arancel_mx.sources.capture import can_reuse_parse, capture_document


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


def test_parse_reuse_requires_the_complete_identity():
    previous = {
        "source_sha256": "abc",
        "parser_version": "1",
        "schema_version": "1",
        "registry_version": "1",
    }

    assert can_reuse_parse(previous, "abc", "1", "1", "1")
    assert not can_reuse_parse(previous, "def", "1", "1", "1")
    assert not can_reuse_parse(previous, "abc", "2", "1", "1")
    assert not can_reuse_parse(previous, "abc", "1", "2", "1")
    assert not can_reuse_parse(previous, "abc", "1", "1", "2")
