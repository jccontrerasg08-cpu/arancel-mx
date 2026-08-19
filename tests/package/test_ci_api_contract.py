from __future__ import annotations

from pathlib import Path
import re


CI = Path(".github/workflows/ci.yml")
_JOB_HEADER = re.compile(r"(?m)^  ([A-Za-z0-9_-]+):$")


def _job(name: str) -> str:
    workflow = CI.read_text(encoding="utf-8")
    header = re.search(rf"(?m)^  {re.escape(name)}:$", workflow)
    assert header is not None, f"CI workflow must define job {name}"
    start = header.start()
    following = [
        match.start()
        for match in _JOB_HEADER.finditer(workflow[header.end() :])
    ]
    end = header.end() + following[0] if following else len(workflow)
    return workflow[start:end]


def test_ci_allows_live_source_probes_to_report_before_job_timeout() -> None:
    job = _job("test")

    assert "timeout-minutes: 30" in job
    assert "Verify documented official URLs are accessible" in job


def test_required_ci_type_checks_the_full_package() -> None:
    job = _job("test")

    assert "Type-check full package" in job
    assert "python -m mypy src/arancel_mx" in job


def test_ci_smokes_the_fastapi_cloud_python_runtime() -> None:
    job = _job("fastapi-cloud-runtime")

    assert 'python-version-file: ".python-version"' in job
    assert (
        'python -m pip install -c requirements/production-build.txt -e "." '
        "pytest==9.1.1 httpx2==2.10.0"
    ) in job
    assert (
        "python -m pytest -q tests/api tests/package/test_api_install_smoke.py"
    ) in job


def test_fastapi_cloud_job_exercises_default_verified_startup() -> None:
    job = _job("fastapi-cloud-runtime")

    assert "Smoke-test default FastAPI startup" in job
    assert "ARANCEL_MX_API_DATASET: data-2026.08.15" in job
    assert 'ARANCEL_MX_CACHE_DIR: "${{ runner.temp }}/arancel-mx-api-cache"' in job
    assert "from arancel_mx.api.app import app" in job
    assert "with TestClient(app) as client:" in job
    assert 'client.get("/readyz")' in job
    assert 'client.get("/v1/meta")' in job
