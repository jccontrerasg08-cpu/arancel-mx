from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = (
    ROOT
    / "website"
    / "i18n"
    / "en"
    / "docusaurus-plugin-content-docs"
    / "current"
)
PUBLIC_DOCS = {
    "getting-started.md",
    "cli.md",
    "python-api.md",
    "dataset.md",
    "hs-mx-nico.md",
    "data-model.md",
    "sources.md",
    "provenance.md",
    "release-process.md",
    "reproducibility.md",
    "verify-release.md",
    "production-certification.md",
}


def test_english_public_docs_have_exact_sidebar_parity():
    actual = {
        path.name
        for path in TRANSLATIONS.glob("*.md")
        if path.is_file()
    }
    assert actual == PUBLIC_DOCS


def test_english_docs_do_not_translate_internal_maintainer_trees():
    root = ROOT / "website" / "i18n" / "en"
    assert not any("superpowers" in path.parts for path in root.rglob("*"))
    assert not any("operations" in path.parts for path in root.rglob("*"))


def test_english_source_and_release_docs_preserve_authority_and_verification_terms():
    sources = (TRANSLATIONS / "sources.md").read_text(encoding="utf-8").lower()
    release = (TRANSLATIONS / "release-process.md").read_text(encoding="utf-8").lower()

    assert "authoritative_for_tariff" in sources
    assert "publication_gate" in sources
    assert "100+" in sources
    assert "update lag" in sources
    assert "six assets" in release
    assert "gh attestation verify" in release
    assert "not a legal signature" in release
