from __future__ import annotations


class Cursor:
    def __init__(self, *, one=None, many=None):
        self.one = one
        self.many = many or []

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.many


class Connection:
    def __init__(self, cursor: Cursor):
        self.cursor = cursor
        self.statement = ""
        self.values = None

    def execute(self, statement, values=None):
        self.statement = statement
        self.values = values
        return self.cursor


def test_active_release_metadata_exposes_only_the_verified_serving_identity():
    from arancel_mx.operational.query import active_release_metadata

    connection = Connection(
        Cursor(one=("data-2026.08.18", "2026.08.18", "2", "2026-08-18T12:00:00+00:00"))
    )

    assert active_release_metadata(connection) == {
        "dataset_tag": "data-2026.08.18",
        "dataset_version": "2026.08.18",
        "schema_version": "2",
        "release_published_at": "2026-08-18T12:00:00+00:00",
        "release_verified": True,
        "structural_valid": True,
        "read_only": True,
    }
    assert "operational_active_release" in connection.statement


def test_active_release_search_returns_public_payloads_and_never_uses_inactive_versions():
    from arancel_mx.operational.query import search_active_release

    payload = {
        "code": "85171301",
        "level": "fraccion8",
        "description": "Teléfonos inteligentes.",
        "dataset_version": "2026.08.18",
    }
    connection = Connection(Cursor(many=[(payload, True)]))

    assert search_active_release(connection, "85171301", limit=8) == [
        {
            "record": payload,
            "match_kind": "exact_code",
            "score": 100,
            "confidence": 1.0,
        }
    ]
    assert "current_operational_record" in connection.statement
    assert connection.values == ("85171301", "85171301", "%85171301%", 8)
