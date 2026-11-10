"""Contracts for the citation, parity, and treaty-spike notes."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_english_readme_does_not_advertise_an_unshipped_diagnostic() -> None:
    readme = _text("README.en.md")
    assert "data nico-coverage" not in readme
    assert "How to cite" in readme
    assert "release_verified" not in readme or "data-2026.11.09" in readme


def test_hub_citation_uses_meta_identity_fields() -> None:
    guide = _text("docs/hub-citation-guidance.md")
    for field in ("dataset_tag", "dataset_version", "schema_version", "release_verified"):
        assert field in guide
    assert "SHA256SUMS" in guide
    assert "Copy citation" in guide


def test_treaty_spike_stays_out_of_the_general_rate() -> None:
    spike = _text("docs/research/treaty-preferences-spike.md")
    assert "Not implemented" in spike
    assert "igi_text" in spike
    assert "proof_required" in spike


def test_static_api_parity_names_the_locking_test() -> None:
    note = _text("docs/static-api-parity.md")
    assert "test_browser_client_matches_python_reference" in note
    assert "SCORER_VERSION" in note
    assert "frontend/src/static-api.js" in note
