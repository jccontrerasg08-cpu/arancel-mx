from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RFC = ROOT / "docs" / "rfcs" / "notebooklm-2026"
RESEARCH = ROOT / "docs" / "research"


def test_feature_registry_complete_and_referentially_sound() -> None:
    registry = json.loads((RFC / "feature-coverage-2026-11-21.json").read_text(encoding="utf-8"))
    inventory = json.loads((RESEARCH / "notebooklm-source-inventory-2026-11-21.json").read_text(encoding="utf-8"))
    features = registry["features"]
    sources = registry["source_bindings"]
    requirements = registry["requirements"]

    assert len(features) == 12
    assert len(requirements) == 28
    assert len(sources) == len(inventory["sources"]) == 42
    assert registry["notebook_unique_titles"] == 41
    ids = {feature["id"] for feature in features}
    assert len(ids) == 12
    assert len({feature["pr_number"] for feature in features}) == 12
    assert len({feature["rfc_path"] for feature in features}) == 12

    for feature in features:
        assert feature["pr_url"] == (
            "https://github.com/jccontrerasg08-cpu/arancel-mx/pull/"
            + str(feature["pr_number"])
        )
        assert feature["state"] == "draft_specification_no_code"
        assert feature["rfc_path"].startswith("docs/rfcs/notebooklm-2026/")
        assert feature["capabilities"]

    assert len({r["id"] for r in requirements}) == len(requirements)
    assert all(r["feature_id"] in ids for r in requirements)
    assert {r["feature_id"] for r in requirements} == ids
    assert [s["entry_id"] for s in sources] == list(range(1, 43))
    for source, original in zip(sources, inventory["sources"], strict=True):
        assert source["title"] == original["title"]
        assert source["link"] == original["url"]
        assert source["feature_ids"]
        assert set(source["feature_ids"]) <= ids
        assert source["relation"] == "thematic_cross_reference_not_legal_applicability"
        assert source["notebook_original_url_known"] == (
            original["link_basis"] == "shown_literal_in_notebook"
        )


def test_studio_and_video_claims_are_not_pretended_as_verified() -> None:
    registry = json.loads((RFC / "feature-coverage-2026-11-21.json").read_text(encoding="utf-8"))
    assert len(registry["studio_assets"]) == 6
    assert all(s["internal_content_reviewed"] is False for s in registry["studio_assets"])
    assert len(registry["video_claims"]) == 11
    assert all(v["full_video_reviewed"] is False for v in registry["video_claims"])
    assert all(v["video_url_verified"] is False for v in registry["video_claims"])
    assert len(registry["gemini_claims_requiring_correction"]) == 8
    assert all(not c["accepted_as_verified_fact"] for c in registry["gemini_claims_requiring_correction"])
    roadmap = (RFC / "README.md").read_text(encoding="utf-8")
    documentation_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "42 fuentes" in roadmap or "42 entradas" in roadmap
    assert "rfcs/notebooklm-2026/README.md" in documentation_index
