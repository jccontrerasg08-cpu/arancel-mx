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
    assert "pip install arancel-mx" in document
    assert 'pip install "arancel-mx[maintainer]"' in document
    assert "from arancel_mx import Dataset" in document
    assert "Dataset.latest()" in document
    assert "data-YYYY.MM.DD" in document
    assert "dataset is not embedded" in document.lower()


def test_package_release_doc_keeps_code_and_data_release_channels_separate() -> None:
    document = _read("docs/package-release.md")
    assert "pkg-v0.2.0" in document
    assert "GitHub Releases" in document
    assert "TestPyPI" in document
    assert "PyPI" in document
    assert "not create a GitHub Release" in document
