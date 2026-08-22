from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PR_TEMPLATE = ROOT / ".github" / "pull_request_template.md"
CONTRIBUTING = ROOT / "CONTRIBUTING.md"
DECISION_TEMPLATE = ROOT / "docs" / "decisions" / "0000-template.md"
TRIAGE_GUIDE = ROOT / "docs" / "operations" / "issue-triage.md"


def test_contributor_flow_covers_compatibility_decisions_and_triage() -> None:
    template = PR_TEMPLATE.read_text(encoding="utf-8")
    contributing = CONTRIBUTING.read_text(encoding="utf-8")

    assert "Compatibilidad y decisión" in template
    assert "decisión registrada" in template
    assert "fragmento de changelog" in template
    assert "docs/decisions/" in contributing
    assert DECISION_TEMPLATE.is_file()
    assert TRIAGE_GUIDE.is_file()


def test_decision_template_and_triage_guide_keep_the_process_scoped() -> None:
    decision = DECISION_TEMPLATE.read_text(encoding="utf-8")
    triage = TRIAGE_GUIDE.read_text(encoding="utf-8")

    for heading in ("Contexto", "Decisión", "Alternativas", "Compatibilidad"):
        assert f"## {heading}" in decision
    assert "**Responsable:**" in decision
    for step in ("Duplicado", "Reproducción", "Alcance", "Etiqueta", "Siguiente acción"):
        assert step in triage
    assert "No cierres" in triage
