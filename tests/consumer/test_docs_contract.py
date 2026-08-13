from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_bilingual_readmes_show_install_and_consumer_first_commands() -> None:
    spanish = _read("README.md")
    english = _read("README.en.md")

    required = (
        "pip install arancel-mx",
        "arancel-mx doctor",
        "arancel-mx data download",
        "arancel-mx lookup 01012101",
        "arancel-mx ficha 01012101",
        "arancel-mx chapters",
        "arancel-mx data verify",
        "docs/consumer-cli.md",
    )
    for document in (spanish, english):
        assert [value for value in required if value not in document] == []


def test_consumer_guide_documents_offline_formats_and_version_pinning() -> None:
    guide_path = ROOT / "docs/consumer-cli.md"
    assert guide_path.exists(), "docs/consumer-cli.md must document the public consumer CLI"

    guide = guide_path.read_text(encoding="utf-8")
    required = (
        "package version",
        "dataset version",
        "--dataset data-YYYY.MM.DD",
        "--offline",
        "--no-offline",
        "ARANCEL_MX_OFFLINE",
        "ARANCEL_MX_DATASET",
        "--format json",
        "--format csv",
        "arancel-mx doctor --json",
        "arancel-mx search \"refrigeradores\"",
        "arancel-mx ficha",
        "arancel-mx chapters",
    )
    assert [value for value in required if value not in guide] == []
