"""Protege la presencia y los enlaces de la política de desarrollo del Central Hub."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs" / "governance" / "DEVELOPMENT_POLICY.md"


def test_development_policy_is_present_and_has_required_controls() -> None:
    text = POLICY.read_text(encoding="utf-8")

    for heading in (
        "## Principios obligatorios",
        "## Puerta de cambio basada en evidencia",
        "## Seguridad, secretos y dependencias",
        "## Cambios entre repositorios",
        "## Excepciones, revisión y recuperación",
    ):
        assert heading in text

    assert "No se elimina un archivo" in text
    assert "No se declara" in text
    assert "Mínimo privilegio" in text


def test_policy_is_reachable_from_documentation_and_contributing() -> None:
    docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "governance/DEVELOPMENT_POLICY.md" in docs_index
    assert "docs/governance/DEVELOPMENT_POLICY.md" in contributing
