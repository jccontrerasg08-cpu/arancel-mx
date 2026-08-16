from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_spanish_readme_documents_public_api_without_inventing_hostname() -> None:
    text = _text("README.md")
    lowered = text.lower()

    required = (
        "API HTTP pública",
        "GET-only",
        "read-only",
        "sin API key",
        "/v1",
        "/docs",
        "/readyz",
        "/v1/meta",
        "ARANCEL_MX_API_DATASET=data-2026.08.15",
        "8517130100",
    )
    for token in required:
        assert token in text
    assert "no clasifica" in lowered
    assert "asesoría legal" in lowered


def test_english_readme_documents_same_public_api_boundary() -> None:
    text = _text("README.en.md")
    lowered = text.lower()

    required = (
        "public HTTP API",
        "GET-only",
        "read-only",
        "no API key",
        "/v1",
        "/docs",
        "/readyz",
        "/v1/meta",
        "ARANCEL_MX_API_DATASET=data-2026.08.15",
        "8517130100",
    )
    for token in required:
        assert token in text
    assert "does not classify" in lowered
    assert "legal advice" in lowered


def test_external_consumption_guide_documents_unhosted_url_placeholder_and_versions() -> None:
    text = _text("docs/external-consumption.md")
    lowered = text.lower()

    required = (
        "ARANCEL_MX_API_URL",
        "ARANCEL_MX_API_DATASET=data-2026.08.15",
        "/v1/lookup/8517130100",
        "API v1",
        "package 0.3.3",
        "dataset data-2026.08.15",
    )
    for token in required:
        assert token in text
    assert "api rest hospedada" not in lowered
    assert "actualización, reconciliación ni publicación" in lowered


def test_changelog_records_fastapi_v1_without_claiming_a_live_hostname() -> None:
    text = _text("CHANGELOG.md")

    assert "FastAPI" in text
    assert "ARANCEL_MX_API_DATASET" in text
    assert "data-2026.08.15" in text
