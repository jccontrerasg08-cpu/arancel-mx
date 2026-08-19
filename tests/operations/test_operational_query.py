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
    connection = Connection(Cursor(many=[(payload, True, "2026.08.18")]))

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


def test_active_release_search_rejects_a_record_from_another_dataset_version():
    from arancel_mx.operational.query import search_active_release

    connection = Connection(
        Cursor(
            many=[
                (
                    {
                        "code": "85171301",
                        "dataset_version": "2026.08.15",
                    },
                    True,
                    "2026.08.18",
                )
            ]
        )
    )

    try:
        search_active_release(connection, "85171301")
    except ValueError as exc:
        assert str(exc) == "operational record dataset_version does not match active release"
    else:
        raise AssertionError("expected a mismatched release payload to be rejected")


def test_lookup_active_release_adapts_the_existing_public_tariff_shape():
    from arancel_mx.operational.query import lookup_active_release

    payload = {
        "code": "85171301",
        "level": "fraccion8",
        "description": "Teléfonos inteligentes.",
        "unit_name": "Pza",
        "igi_text": "Ex.",
        "igi_kind": "exento",
        "igi_value": "0.000000",
        "ige_text": "Ex.",
        "ige_kind": "exento",
        "ige_value": "0.000000",
        "schema_version": "2",
        "is_current": True,
        "hs2": "85",
        "hs4": "8517",
        "hs6": "851713",
        "fraccion8": "85171301",
        "nico2": None,
        "nico10": None,
        "ligie_version": "LIGIE-2022",
        "validity_basis": "observed_snapshot",
        "dataset_version": "2026.08.18",
    }
    connection = Connection(Cursor(many=[(payload, "2026.08.18")]))

    assert lookup_active_release(connection, "8517.13.01") == {
        "code": "85171301",
        "level": "fraccion8",
        "description": "Teléfonos inteligentes.",
        "unit_name": "Pza",
        "igi": {"text": "Ex.", "kind": "exento", "value": 0.0},
        "ige": {"text": "Ex.", "kind": "exento", "value": 0.0},
        "parent_code": "851713",
        "dataset_version": "2026.08.18",
        "schema_version": "2",
        "effective_from": None,
        "effective_to": None,
        "is_current": True,
        "hierarchy": {
            "hs2": "85",
            "hs4": "8517",
            "hs6": "851713",
            "fraccion8": "85171301",
            "nico2": None,
            "nico10": None,
        },
        "ligie_version": "LIGIE-2022",
        "validity_basis": "observed_snapshot",
    }
    assert connection.values == ("85171301",)


def test_national_notes_active_release_reads_only_active_snapshot_evidence():
    from arancel_mx.operational.query import national_notes_active_release

    evidence = {
        "source_documents": [],
        "record_provenance": [],
        "national_notes": [
            {
                "chapter": "85",
                "note_number": "1",
                "text": "Texto oficial.",
                "source_document_id": "dof-1",
                "scope_type": "chapter",
                "scope_value": "85",
                "applicability_basis": "explicit",
            },
            {
                "chapter": "84",
                "note_number": "1",
                "text": "No debe aparecer.",
                "source_document_id": "dof-1",
                "scope_type": "chapter",
                "scope_value": "84",
                "applicability_basis": "explicit",
            },
        ],
    }
    connection = Connection(Cursor(one=(evidence,)))

    assert national_notes_active_release(connection, "85") == [evidence["national_notes"][0]]
