from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_spanish_readme_preserves_existing_contract_and_new_user_path():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    required = (
        "arancel-mx",
        "apache-2.0",
        "## alcance",
        "## instalación",
        "## uso desde python",
        "## estructura del repositorio",
        "## pruebas",
        "no constituye asesoría legal",
        "docs/demo.gif",
        "docs/dof_timeline.png",
        "docs/dof_timeline2.png",
        "docs/nico_flow.png",
        "src/arancel_mx/sources/source_registry.json",
        "propuestas nico",
        "capture manifests y hashes",
        "https://www.diputados.gob.mx/leyesbiblio/ref/ligie_2022.htm",
        "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html",
        "https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html",
        "https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html",
        "https://www.snice.gob.mx/cs/avi/snice/ligie.indicaranc22.html",
        "https://www.dof.gob.mx/nota_detalle.php?codigo=5656249&fecha=27/06/2022",
        "python -m arancel_mx --help",
        "python -m arancel_mx build --database data/arancel.duckdb --output-dir out/release",
        "python -m arancel_mx check-updates --state-path data/update_state/ligie.json --report-path out/update.json",
        "python -m arancel_mx reconcile --ledger-json ledger.json --dof-json dof.json --snice-json snice.json",
        "python -m arancel_mx release --release-dir out/release --source-dir data/raw/release --latest-dir out/latest",
        "python -m pytest -q",
        "python -m build",
        ".github/workflows/official-data-pipeline.yml",
        "official data pipeline",
        "17 11 * * *",
        "requirements/production-build.txt",
        "no_change",
        "github issue",
        "data-yyyy.mm.dd",
        "official-sources.tar.gz",
        "check-updates",
        "fuentes oficiales → captura → reconciliación legal → parseo → validación",
        "sin cambios: termina en verde",
        "cambio válido: release inmutable verificado",
        "cualquier fallo: bloquea la publicación + github issue",
        "revisión diaria automatizada",
        "publicación automática",
        "cualquier falla bloquea la publicación",
        "docs/getting-started.md",
        "docs/verify-release.md",
        "support.md",
        "citation.cff",
    )
    assert [value for value in required if value not in readme] == []
    assert "pip install arancel-mx" not in readme
    assert "jccontrerasg08-cpu.github.io/arancel-mx" not in readme


def test_english_readme_preserves_autonomous_contract_and_onboarding_links():
    readme = (ROOT / "README.en.md").read_text(encoding="utf-8").lower()
    required = (
        "readme.md",
        "español",
        ".github/workflows/official-data-pipeline.yml",
        "official data pipeline",
        "17 11 * * *",
        "requirements/production-build.txt",
        "no_change",
        "github issue",
        "data-yyyy.mm.dd",
        "official-sources.tar.gz",
        "check-updates",
        "official sources → capture → legal reconciliation → parse → validate",
        "unchanged: stop green",
        "changed + valid: verified immutable release",
        "any failure: block publication + github issue",
        "daily automated check",
        "automatic publication",
        "any failure blocks publication",
        "docs/getting-started.md",
        "docs/verify-release.md",
        "support.md",
        "citation.cff",
    )
    assert [value for value in required if value not in readme] == []
    assert "pip install arancel-mx" not in readme
    assert "jccontrerasg08-cpu.github.io/arancel-mx" not in readme
