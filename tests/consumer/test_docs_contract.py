from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

EXTERNAL_CONSUMPTION_HEADINGS = (
    "## Qué es y qué no es arancel-mx",
    "## Instalar y fijar versiones",
    "## Verificar",
    "## Consultar",
    "## Autoingesta",
    "## Mapeo de procedencia",
    "## Fuera de alcance",
    "## Licencia y atribución",
    "## Documentación relacionada",
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    rest = text[start:]
    next_heading = rest.find("\n## ", 1)
    return rest if next_heading < 0 else rest[:next_heading]


def test_bilingual_readmes_show_install_and_consumer_first_commands() -> None:
    spanish = _read("README.md")
    english = _read("README.en.md")

    required = (
        "pip install arancel-mx",
        "arancel-mx doctor",
        "arancel-mx data download",
        "arancel-mx lookup 01012101",
        "arancel-mx ficha 01012101",
        "arancel-mx compare 01012101",
        "arancel-mx chapters",
        "arancel-mx data verify",
        "docs/consumer-cli.md",
    )
    for document in (spanish, english):
        assert [value for value in required if value not in document] == []


def test_bilingual_readmes_document_sha256sum_check_without_pinning_asset_megabytes() -> None:
    spanish = _read("README.md")
    english = _read("README.en.md")
    for document in (spanish, english):
        assert "sha256sum -c SHA256SUMS" in document
        assert " MB" not in document
        assert "MiB" not in document
    assert "GitHub muestra el tamaño" in spanish
    assert "GitHub lists the size" in english


def test_contributing_lists_github_review_extensions_as_install_only() -> None:
    text = _read("CONTRIBUTING.md")
    for name in ("Octotree", "Refined GitHub", "Pretty Pull Requests"):
        assert name in text
    lowered = text.lower()
    assert "instala" in lowered
    assert "no reimplementa" in lowered


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
        "arancel-mx compare",
        "XDG_CACHE_HOME",
        "LOCALAPPDATA",
    )
    assert [value for value in required if value not in guide] == []
    assert "0.1.0" not in guide
    assert "platformdirs" in guide.lower()


def test_consumer_cli_treats_pip_install_as_current_public_path() -> None:
    guide = _read("docs/consumer-cli.md").lower()
    assert "current public install path" in guide
    assert "once the distribution is published" not in guide
    assert "until that publication happens" not in guide


def test_external_consumption_guide_exists_with_required_sections_in_order() -> None:
    path = ROOT / "docs/external-consumption.md"
    assert path.is_file(), "docs/external-consumption.md is the Spanish downstream source of truth"

    text = path.read_text(encoding="utf-8")
    positions = []
    for heading in EXTERNAL_CONSUMPTION_HEADINGS:
        index = text.find(heading)
        assert index >= 0, f"missing required heading: {heading}"
        positions.append(index)
    assert positions == sorted(positions)


def test_external_consumption_guide_locks_install_verify_query_and_public_surface() -> None:
    text = _read("docs/external-consumption.md")
    required = (
        "pip install arancel-mx==0.2.0",
        "  -> pip install arancel-mx==0.2.0",
        "data-2026.08.11",
        "data-YYYY.MM.DD",
        "--dataset data-YYYY.MM.DD",
        "arancel-mx doctor",
        "arancel-mx data download",
        "arancel-mx data verify",
        "SHA256SUMS",
        "sha256sum -c SHA256SUMS",
        "schema v2",
        "Dataset.latest()",
        'Dataset.version("data-YYYY.MM.DD")',
        "Dataset.open",
        "release_verified",
        "Dataset.provenance",
        "Dataset.compare",
        "lookup",
        "search",
        "ficha",
        "chapters",
        "parent",
        "children",
        "TariffRecord",
        "Ficha",
        "ProvenanceRecord",
        "SearchResult",
        "DatasetInfo",
        "HsSection",
        "CompareRow",
        "from arancel_mx import Dataset",
        "arancel_mx.duckdb",
        "arancel_mx.csv",
        "arancel_mx.json",
        "manifest.json",
        "official-sources.tar.gz",
        "igi_text",
        "ige_text",
        "fraccion8",
        "nico10",
        "fraction8",
        "classification10",
        "RecordNotFoundError",
        "--offline",
        "Apache-2.0",
        "NOTICE",
        "TERMS.md",
        "docs/consumer-cli.md",
        "docs/data-model.md",
        "docs/release-process.md",
        "docs/sources.md",
        "01012101",
    )
    assert [value for value in required if value not in text] == []
    assert "pip install arancelmx" not in text
    assert "import arancelmx" not in text
    assert "IGI=16%" not in text
    assert "IGI 16%" not in text


def test_external_consumption_out_of_scope_says_iva_nom_and_tmec_are_not_published() -> None:
    section = _section(_read("docs/external-consumption.md"), "## Fuera de alcance")
    for term in ("IVA", "NOM", "T-MEC", "GIR"):
        assert term in section
    for term in (
        "franja",
        "permisos",
        "PROSEC",
        "REST",
        "Postgres",
        "SIICEX",
        "VUCEM",
    ):
        assert term in section
    lowered = section.lower()
    assert "no publica" in lowered or "no están publicados" in lowered or "no publicados" in lowered


def test_siicex_sagu_pair_is_a_docs_golden_not_a_live_query() -> None:
    for path in ("docs/sources.md", "docs/external-consumption.md"):
        text = _read(path)
        assert "11063001" in text
        assert "11062002" in text
        assert "11063001" in text and ("no está" in text.lower() or "not in" in text.lower() or "falla cerrado" in text.lower())
        assert "11062002" in text and "10" in text
        assert "sagú" in text.lower() or "sagu" in text.lower()


def test_external_consumption_documents_fail_closed_consumer_behavior() -> None:
    text = _read("docs/external-consumption.md").lower()
    required = (
        "fail-closed",
        "cache",
        "--offline",
        "recordnotfounderror",
    )
    assert [value for value in required if value not in text] == []
    assert "asesoría legal" in text or "asesoria legal" in text


def test_no_second_full_english_external_consumption_guide() -> None:
    assert not (ROOT / "docs/external-consumption.en.md").exists()
