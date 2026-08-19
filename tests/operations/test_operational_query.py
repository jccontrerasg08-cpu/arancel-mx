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


def test_lookup_active_release_hides_rates_for_a_nico():
    from arancel_mx.operational.query import lookup_active_release

    payload = {
        "code": "8517130100",
        "level": "nico10",
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
        "nico2": "00",
        "nico10": "8517130100",
        "ligie_version": "LIGIE-2022",
        "validity_basis": "observed_snapshot",
        "dataset_version": "2026.08.18",
    }
    connection = Connection(Cursor(many=[(payload, "2026.08.18")]))

    record = lookup_active_release(connection, "8517.13.01.00")

    assert record is not None
    assert record["hierarchy"]["fraccion8"] == "85171301"
    assert record["igi"] is None
    assert record["ige"] is None


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


class ActiveReleaseConnection:
    def __init__(self, payloads, evidence):
        self.payloads = {payload["code"]: payload for payload in payloads}
        self.evidence = evidence

    def execute(self, statement, values=None):
        active_version = "2026.08.18"
        if "evidence_json" in statement:
            return Cursor(one=(self.evidence,))
        if "WHERE record.code = %s" in statement:
            payload = self.payloads.get(values[0])
            return Cursor(many=[] if payload is None else [(payload, active_version)])
        if "record.level = 'hs2'" in statement:
            return Cursor(
                many=[
                    (payload, active_version)
                    for payload in self.payloads.values()
                    if payload["level"] == "hs2"
                ]
            )
        if "WHERE record.level = %s" in statement:
            level, prefix, width = values
            return Cursor(
                many=[
                    (payload, active_version)
                    for payload in self.payloads.values()
                    if payload["level"] == level
                    and payload["code"].startswith(prefix.removesuffix("%"))
                    and len(payload["code"]) == width
                ]
            )
        if "FROM current_operational_record" in statement:
            return Cursor(many=[(payload, active_version) for payload in self.payloads.values()])
        raise AssertionError(f"unexpected statement: {statement}")


def test_active_release_public_workflow_preserves_search_hierarchy_and_evidence():
    from arancel_mx.operational.query import (
        chapters_active_release,
        children_active_release,
        ficha_active_release,
        parent_active_release,
        provenance_active_release,
        search_public_active_release,
        sections_active_release,
        suggest_active_release,
    )

    def payload(code, level, description):
        return {
            "code": code,
            "level": level,
            "description": description,
            "unit_name": None,
            "igi_text": "Ex.",
            "igi_kind": "exento",
            "igi_value": "0",
            "ige_text": "Ex.",
            "ige_kind": "exento",
            "ige_value": "0",
            "dataset_version": "2026.08.18",
            "schema_version": "2",
            "is_current": True,
            "hs2": "85",
            "hs4": "8517" if len(code) >= 4 else None,
            "hs6": "851713" if len(code) >= 6 else None,
            "fraccion8": code if len(code) == 8 else None,
            "nico2": None,
            "nico10": None,
            "ligie_version": "LIGIE-2022",
            "validity_basis": "observed_snapshot",
        }

    records = [
        payload("85", "hs2", "Máquinas y aparatos eléctricos."),
        payload("8517", "hs4", "Aparatos telefónicos."),
        payload("851713", "hs6", "Teléfonos inteligentes."),
        payload("85171301", "fraccion8", "Teléfonos inteligentes."),
    ]
    evidence = {
        "source_documents": [
            {
                "source_document_id": "dof-1",
                "authority": "DOF",
                "publication_venue": "Diario Oficial",
                "title": "Decreto",
                "source_url": "https://dof.example/decreto",
                "sha256": "a" * 64,
            }
        ],
        "record_provenance": [
            {"code": "85171301", "source_document_id": "dof-1", "role": "base", "is_primary": True}
        ],
        "national_notes": [
            {"chapter": "85", "note_number": "1", "text": "Texto oficial.", "source_document_id": "dof-1"}
        ],
    }
    connection = ActiveReleaseConnection(records, evidence)

    assert [item["code"] for item in chapters_active_release(connection)] == ["85"]
    assert parent_active_release(connection, "85171301")["code"] == "851713"
    assert [item["code"] for item in children_active_release(connection, "851713")] == ["85171301"]
    assert ficha_active_release(connection, "85171301")["formatted_code"] == "85.17.13.01"
    assert search_public_active_release(connection, "telefonos", limit=5)[0]["record"]["code"] == "851713"
    suggestion = suggest_active_release(connection, "telefonos", limit=1)[0]
    assert suggestion["ficha"]["record"]["code"] == "85171301"
    assert suggestion["national_notes"] == evidence["national_notes"]
    assert provenance_active_release(connection, "85171301")[0]["authority"] == "DOF"
    assert sections_active_release()[0]["roman"] == "I"
