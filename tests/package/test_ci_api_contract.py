from __future__ import annotations

from pathlib import Path


def test_required_ci_type_checks_public_consumer_and_fastapi_surface() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "Type-check public consumer and API" in workflow
    assert (
        "python -m mypy src/arancel_mx/consumer src/arancel_mx/api "
        "src/arancel_mx/__init__.py"
    ) in workflow
