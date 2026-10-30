import json

import pytest

from arancel_mx.pipeline.description_corrections import (
    apply_description_corrections,
    load_corrections,
)


def _registry(*corrections):
    return json.dumps(
        {"kind": "test", "version": "test", "corrections": list(corrections)}
    ).encode()


TYPO = {
    "level": "fraccion8",
    "code": "03048902",
    "snapshot": "Totoabas de manejo intesivo.",
    "corrected": "Totoabas de manejo intensivo.",
    "evidence": "DOF",
    "source_url": "https://www.diputados.gob.mx/ref01.pdf",
    "sha256": "a" * 64,
}


def test_corrects_the_exact_snapshot_text_and_reports_it() -> None:
    rows = [
        {
            "level": "fraccion8",
            "code": "03048902",
            "description": "Totoabas de manejo intesivo.",
        },
        {
            "level": "fraccion8",
            "code": "03048901",
            "description": "Totoabas en vida libre.",
        },
    ]

    report = apply_description_corrections(rows, _registry(TYPO))

    assert rows[0]["description"] == "Totoabas de manejo intensivo."
    assert rows[1]["description"] == "Totoabas en vida libre."
    assert [item["code"] for item in report["applied"]] == ["03048902"]
    assert report["stale"] == []


def test_new_official_text_wins_and_the_correction_is_reported_stale() -> None:
    rows = [
        {
            "level": "fraccion8",
            "code": "03048902",
            "description": "Totoabas de cultivo.",
        }
    ]

    report = apply_description_corrections(rows, _registry(TYPO))

    assert rows[0]["description"] == "Totoabas de cultivo."
    assert report["applied"] == []
    assert report["stale"] == ["03048902"]


def test_corrections_only_apply_to_their_level() -> None:
    rows = [
        {
            "level": "nico10",
            "code": "03048902",
            "description": "Totoabas de manejo intesivo.",
        }
    ]

    apply_description_corrections(rows, _registry(TYPO))

    assert rows[0]["description"] == "Totoabas de manejo intesivo."


@pytest.mark.parametrize(
    "corrections",
    [(TYPO, TYPO), ({**TYPO, "corrected": TYPO["snapshot"]},)],
)
def test_registry_rejects_duplicates_and_no_op_corrections(corrections) -> None:
    with pytest.raises(ValueError):
        load_corrections(_registry(*corrections))


def test_packaged_corrections_only_fix_typos() -> None:
    _, corrections = load_corrections()

    assert {item["code"] for item in corrections} == {"03048902", "39079908"}
    for item in corrections:
        snapshot, corrected = item["snapshot"].split(), item["corrected"].split()
        # Same words except for the misspelled ones: a typo, never a rewrite.
        assert len(snapshot) == len(corrected)
        assert sum(a != b for a, b in zip(snapshot, corrected)) == 1
        assert len(item["sha256"]) == 64
        assert item["source_url"].startswith("https://www.diputados.gob.mx/")
