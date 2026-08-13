from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_readmes_contain_pip_install_and_first_query() -> None:
    spanish = _read("README.md")
    english = _read("README.en.md")
    for text in (spanish, english):
        assert "pip install arancel-mx" in text
        assert "arancel-mx data download" in text
        assert "arancel-mx lookup 01012101" in text


def test_readmes_distinguish_package_and_dataset_versions() -> None:
    spanish = _read("README.md").lower()
    english = _read("README.en.md").lower()
    assert "paquete" in spanish and "dataset" in spanish and "data-yyyy.mm.dd" in spanish
    assert "package" in english and "dataset" in english and "data-yyyy.mm.dd" in english


def test_changelog_has_020_section_and_consumer_scope() -> None:
    changelog = _read("CHANGELOG.md")
    assert "## [0.2.0]" in changelog
    for phrase in ("Dataset", "doctor", "offline", "PyPI"):
        assert phrase.lower() in changelog.lower()


def test_package_release_doc_explains_lightweight_install_and_python_api() -> None:
    document = _read("docs/package-release.md")
    assert 'pip install "arancel-mx[maintainer]"' in document
    assert "data-YYYY.MM.DD" in document
    assert "dataset is not embedded" in document.lower()
    assert "pkg-v0.2.1" in document
    assert "docs/consumer-cli.md" in document
    assert "docs/external-consumption.md" in document
    assert "docs/release-process.md" in document


def test_consumer_docs_cover_install_and_python_api() -> None:
    cli = _read("docs/consumer-cli.md")
    ingest = _read("docs/external-consumption.md")
    assert "pip install arancel-mx" in cli
    assert "from arancel_mx import Dataset" in cli
    assert "Dataset.latest()" in cli
    assert "XDG_CACHE_HOME" in cli
    assert "Dataset.compare" in ingest


def test_package_release_doc_keeps_code_and_data_release_channels_separate() -> None:
    document = _read("docs/package-release.md")
    assert "pkg-v0.2.0" in document
    assert "GitHub Releases" in document
    assert "TestPyPI" in document
    assert "PyPI" in document
    assert "not create a GitHub Release" in document


def _status_row(text: str, capability: str) -> str:
    for line in text.splitlines():
        if capability in line and line.strip().startswith("|"):
            return line
    raise AssertionError(f"missing status-table row for {capability!r}")


def test_readmes_state_pypi_020_is_published_not_roadmap() -> None:
    spanish = _read("README.md")
    english = _read("README.en.md")

    spanish_row = _status_row(spanish, "Publicación en PyPI")
    english_row = _status_row(english, "PyPI publication")
    assert "Roadmap" not in spanish_row
    assert "Roadmap" not in english_row
    assert "0.2.0" in spanish_row
    assert "0.2.0" in english_row
    assert "Publicado" in spanish_row or "publicado" in spanish_row
    assert "Published" in english_row or "published" in english_row

    for text in (spanish, english):
        lowered = text.lower()
        assert "production-certified" not in lowered
        assert "producción certificada" not in lowered
        assert "cuando se publique" not in lowered
        assert "once the package is published" not in lowered
        assert "pip install arancel-mx==0.2.0" in text


def test_changelog_020_heading_is_pypi_upload_date_not_unreleased_candidate() -> None:
    changelog = _read("CHANGELOG.md")
    assert "## [0.2.0] - 2026-08-12" in changelog
    assert "Unreleased package candidate" not in changelog
    assert "Trusted Publishing" in changelog
    lowered = changelog.lower()
    assert "already available on pypi" not in lowered or "not mean" not in lowered
    assert "matrix" in lowered
    assert "production-certified" not in lowered


def test_package_release_doc_describes_020_as_published() -> None:
    document = _read("docs/package-release.md")
    lowered = document.lower()
    assert "must not claim that the candidate has already been published" not in lowered
    assert "0.2.0" in document
    assert "published" in lowered
    assert "0.2.1" in document
    assert "matrix" in lowered
    assert "production-certified" not in lowered


def test_readme_en_links_external_consumption_with_english_ingest_summary() -> None:
    english = _read("README.en.md")
    assert "docs/external-consumption.md" in english
    lowered = english.lower()
    for phrase in ("install", "verify", "query", "out of scope"):
        assert phrase in lowered
    spanish = _read("README.md")
    assert "docs/external-consumption.md" in spanish
