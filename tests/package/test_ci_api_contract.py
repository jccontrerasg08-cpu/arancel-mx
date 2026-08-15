from __future__ import annotations

from pathlib import Path


CI = Path(".github/workflows/ci.yml")


def test_required_ci_type_checks_public_consumer_and_fastapi_surface() -> None:
    workflow = CI.read_text(encoding="utf-8")

    assert "Type-check public consumer and API" in workflow
    assert (
        "python -m mypy src/arancel_mx/consumer src/arancel_mx/api "
        "src/arancel_mx/__init__.py"
    ) in workflow


def test_ci_smokes_the_fastapi_cloud_python_runtime() -> None:
    workflow = CI.read_text(encoding="utf-8")

    assert "fastapi-cloud-runtime:" in workflow
    assert 'python-version-file: ".python-version"' in workflow
    assert (
        'python -m pip install -c requirements/production-build.txt -e "." '
        "pytest==9.1.1 httpx2==2.9.0"
    ) in workflow
    assert (
        "python -m pytest -q tests/api tests/package/test_api_install_smoke.py"
    ) in workflow
