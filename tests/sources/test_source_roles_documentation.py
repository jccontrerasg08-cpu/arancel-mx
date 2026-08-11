from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_source_docs_keep_official_roles_distinct_and_vucem_pre_registry():
    text = (ROOT / "docs" / "sources.md").read_text(encoding="utf-8").lower()
    required = (
        "diputados.gob.mx",
        "dof.gob.mx",
        "snice.gob.mx",
        "ventanillaunica.gob.mx",
        "cross-check operativo independiente",
        "vucem no forma parte del `source_registry`",
        "authoritative_for_tariff",
        "publication_gate",
        "100+",
        "schema_fingerprint",
        "update lag",
        "registry_review_ready=true",
    )
    assert [value for value in required if value not in text] == []


def test_source_docs_do_not_promote_vucem_into_production_authority():
    text = (ROOT / "docs" / "sources.md").read_text(encoding="utf-8").lower()
    forbidden = (
        "vucem es authoritative_for_tariff",
        "vucem bloquea la publicación",
        "vucem forma parte del source_registry",
    )
    assert [value for value in forbidden if value in text] == []
