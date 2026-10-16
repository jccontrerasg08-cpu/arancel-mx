from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_ORIGIN = "https://arancel-mx.vercel.app"


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_spanish_readme_documents_current_public_api_front_door() -> None:
    text = _text("README.md")
    lowered = text.lower()

    required = (
        "API HTTP pública",
        "GET-only",
        "read-only",
        "sin API key",
        PUBLIC_ORIGIN,
        "/data/v1/meta.json",
        "/data/v1/records/85.json",
        "/documentation",
        "8517130100",
    )
    for token in required:
        assert token in text
    assert "no clasifica" in lowered
    assert "asesoría legal" in lowered
    assert "ARANCEL_MX_API_DATASET=data-" not in text


def test_english_readme_documents_same_public_api_boundary() -> None:
    text = _text("README.en.md")
    lowered = text.lower()

    required = (
        "public HTTP API",
        "GET-only",
        "read-only",
        "no API key",
        PUBLIC_ORIGIN,
        "/data/v1/meta.json",
        "/data/v1/records/85.json",
        "/documentation",
        "8517130100",
    )
    for token in required:
        assert token in text
    assert "does not classify" in lowered
    assert "legal advice" in lowered
    assert "ARANCEL_MX_API_DATASET=data-" not in text


def test_external_consumption_guide_documents_static_api_and_deprecated_v1() -> None:
    text = _text("docs/external-consumption.md")
    lowered = text.lower()

    required = (
        'ARANCEL_MX_API_URL="https://arancel-mx.vercel.app"',
        "/data/v1/meta.json",
        "/data/v1/records/85.json",
        "/data/v1/search-index.json",
        "/data/v1/manifest.json",
        "/v1/lookup/8517130100",
        "/v1/meta",
        "/v1/search",
        "/readyz",
        "/documentation",
        "GitHub Pages",
        "Deprecation",
        "2027-01-31",
        "data-YYYY.MM.DD",
    )
    for token in required:
        assert token in text
    assert "api de escritura o administración" in lowered
    assert "read-only" in lowered
    assert "get-only" in lowered
    assert "fuente canónica" in lowered
    assert "api.example.com" not in lowered
    assert "el sitio no actúa como proxy" in lowered
    assert "fastapicloud.dev" not in lowered


def test_changelog_preserves_historical_fastapi_release_context() -> None:
    text = _text("CHANGELOG.md")

    assert "FastAPI" in text
    assert "ARANCEL_MX_API_DATASET" in text
    assert "data-2026.08.15" in text


def test_docs_hub_and_brand_guide_link_to_local_documentation_scope() -> None:
    for path in ("docs/README.md", "docs/brand.md"):
        text = _text(path)
        lowered = text.lower()
        assert f"{PUBLIC_ORIGIN}/documentation" in text
        assert "openapi público" not in lowered
        assert f"{PUBLIC_ORIGIN}/docs" not in text
