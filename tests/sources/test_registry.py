from arancel_mx.sources.registry import classify_candidate, load_source_registry


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


def test_registry_keeps_legal_proposals_and_analytics_distinct():
    registry = load_source_registry()

    assert registry["ligie"].authoritative_for_tariff
    assert not registry["nico_proposals"].authoritative_for_tariff
    assert not registry["weighted_tariff_indicators"].authoritative_for_tariff
    assert registry["diputados_ligie"].legal_publication_authority == "DOF"
