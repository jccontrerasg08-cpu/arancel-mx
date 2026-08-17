from importlib.resources import files

import pytest

from arancel_mx.sources.registry import (
    classify_candidate,
    classify_corpus_candidate,
    load_source_registry,
    registered_direct_document,
)

OFFICIAL_HOSTS = {
    "www.diputados.gob.mx",
    "diputados.gob.mx",
    "www.snice.gob.mx",
    "snice.gob.mx",
    "www.dof.gob.mx",
    "dof.gob.mx",
}
FORBIDDEN_REGISTRY_FRAGMENTS = (
    "sat.gob.mx",
    "wcoomd.org",
    "siicex",
    "openai",
    "caaarem",
    "tigiex",
)


def test_packaged_registry_loads_official_https_sources():
    registry = load_source_registry()

    assert registry
    for key, entry in registry.items():
        assert entry.dataset_key == key
        assert entry.canonical_page.startswith("https://")


def test_nico_snapshot_requires_its_authoritative_page():
    entry = load_source_registry()["nico"]
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    assert (
        classify_candidate(
            entry,
            entry.canonical_page,
            "NICO-ABRIL24-LIGIE_20240415-20240415.XLSX",
            media_type,
        )
        == "nico_snapshot"
    )
    assert (
        classify_candidate(
            entry,
            "https://www.snice.gob.mx/ligie.info22.html",
            "NICO-MAYO99-LIGIE_20990501-20990501.XLSX",
            media_type,
        )
        is None
    )


def test_nico_corpus_promotion_is_limited_to_the_registered_index():
    entry = load_source_registry()["nico"]
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    corpus = entry.corpus_index_pages[0]
    href = "NICO-MAYO26-LIGIE_20260501-20260501.XLSX"

    assert classify_candidate(entry, corpus, href, media_type) is None
    assert classify_corpus_candidate(entry, corpus, href, media_type) == "nico_snapshot"
    assert (
        classify_corpus_candidate(
            entry,
            "https://www.snice.gob.mx/~oracle/other-index/",
            href,
            media_type,
        )
        is None
    )


def test_registry_keeps_legal_proposals_and_analytics_distinct():
    registry = load_source_registry()

    assert registry["ligie"].authoritative_for_tariff
    assert not registry["nico_proposals"].authoritative_for_tariff
    assert not registry["weighted_tariff_indicators"].authoritative_for_tariff
    assert registry["diputados_ligie"].legal_publication_authority == "DOF"


def test_diputados_consolidated_text_is_an_explicit_registered_document():
    entry = load_source_registry()["diputados_ligie"]

    url = registered_direct_document(entry, "consolidated_text")

    assert url == "https://www.diputados.gob.mx/LeyesBiblio/pdf/LIGIE_2022.pdf"


def test_national_notes_are_captured_from_the_registered_dof_publication():
    entry = load_source_registry()["national_notes"]

    url = registered_direct_document(entry, "national_notes")

    assert url == "https://dof.gob.mx/nota_detalle.php?codigo=5673161&fecha=02/12/2022"


def test_missing_direct_document_fails_closed():
    entry = load_source_registry()["ligie"]

    with pytest.raises(ValueError, match="registered direct document"):
        registered_direct_document(entry, "consolidated_text")


def test_registry_excludes_unofficial_compiled_tigie_hosts() -> None:
    hosts = {
        host
        for entry in load_source_registry().values()
        for host in entry.allowed_hosts
    }
    assert "siicex-caaarem.org.mx" not in hosts
    assert "www.siicex-caaarem.org.mx" not in hosts
    assert hosts <= OFFICIAL_HOSTS


def test_registry_json_excludes_sat_wco_and_unofficial_tigie_hosts() -> None:
    text = files("arancel_mx.sources").joinpath("source_registry.json").read_text(
        encoding="utf-8"
    ).lower()
    present = [fragment for fragment in FORBIDDEN_REGISTRY_FRAGMENTS if fragment in text]
    assert present == []
