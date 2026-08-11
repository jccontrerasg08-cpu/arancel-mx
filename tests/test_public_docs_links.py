from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = (
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
)


def test_public_docusaurus_docs_do_not_link_outside_plugin_with_parent_paths():
    violations = []
    for name in PUBLIC_DOCS:
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        if "](../" in text:
            violations.append(name)
    assert violations == []
