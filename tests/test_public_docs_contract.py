from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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


def test_canonical_public_docs_exist():
    for name in PUBLIC_DOCS:
        assert (ROOT / "docs" / name).is_file(), name


def test_getting_started_separates_consumer_and_contributor_install_paths():
    text = (ROOT / "docs" / "getting-started.md").read_text(encoding="utf-8").lower()
    required = (
        "consumir los datos sin instalar",
        "pip install .",
        'pip install -c requirements/production-build.txt -e ".[dev]"',
        "no constituye asesoría legal",
        "verify-release.md",
        "support.md",
    )
    assert [value for value in required if value not in text] == []


def test_public_docs_do_not_claim_a_stable_query_api_or_live_pages_site():
    combined = "\n".join(
        (ROOT / "docs" / name).read_text(encoding="utf-8").lower()
        for name in sorted(PUBLIC_DOCS)
        if (ROOT / "docs" / name).is_file()
    )
    assert "pip install arancel-mx" not in combined
    assert "api de búsqueda estable disponible" not in combined
    assert "jccontrerasg08-cpu.github.io/arancel-mx" not in combined
