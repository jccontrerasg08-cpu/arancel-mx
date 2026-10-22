from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import scripts.watch_dof as watch_dof
from scripts.github_api import GitHubNotFound

FIXTURE = Path(__file__).parent / "fixtures" / "sidof" / "notas-13-10-2026.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class FakeClient:
    def __init__(
        self, existing_bodies: list[str] | None = None, label_exists: bool = True
    ) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []
        self.existing = [
            {"number": index + 1, "body": body}
            for index, body in enumerate(existing_bodies or [])
        ]
        self.label_exists = label_exists

    def request_json(self, method: str, path: str, json: dict | None = None):
        self.calls.append((method, path, json))
        if method == "GET" and path.startswith("/labels/"):
            if not self.label_exists:
                raise GitHubNotFound(404, "Not Found")
            return {"name": "dof-candidate"}
        if method == "GET" and path.startswith("/issues"):
            return self.existing
        if method == "POST":
            return {"number": 99}
        raise AssertionError(path)


def _fetch(day: date) -> dict:
    if day == date(2026, 10, 13):
        return _payload()
    return {"messageCode": 200, "response": "OK", "NotasMatutinas": []}


def test_watch_opens_one_issue_per_new_tariff_note() -> None:
    client = FakeClient()
    result = watch_dof.watch(_fetch, today=date(2026, 10, 16), days=7, client=client)

    assert result["status"] == "ok"
    assert len(result["days_checked"]) == 7
    assert [item["cod_nota"] for item in result["candidates"]] == [5800977]
    assert result["issues_created_for"] == [5800977]
    created = [
        call for call in client.calls if call[0] == "POST" and call[1] == "/issues"
    ]
    assert len(created) == 1
    body = created[0][2]
    assert body["labels"] == ["dof-candidate"]
    assert body["title"].startswith(
        "DOF 2026-10-13: Decreto por el que se modifica la Tarifa"
    )
    assert "<!-- arancel-mx-dof-note:5800977 -->" in body["body"]
    assert (
        "https://sidofqa.segob.gob.mx/dof/sidof/documentos/pdf/330185" in body["body"]
    )


def test_watch_is_idempotent_across_runs() -> None:
    client = FakeClient(existing_bodies=["texto\n<!-- arancel-mx-dof-note:5800977 -->"])
    result = watch_dof.watch(_fetch, today=date(2026, 10, 16), days=7, client=client)

    assert result["issues_created_for"] == []
    assert not [
        call for call in client.calls if call[1] == "/issues" and call[0] == "POST"
    ]


def test_watch_creates_missing_label() -> None:
    client = FakeClient(label_exists=False)
    watch_dof.watch(_fetch, today=date(2026, 10, 13), days=1, client=client)

    assert ("POST", "/labels") in [(method, path) for method, path, _ in client.calls]


def test_unreachable_days_are_recorded_without_hiding_others() -> None:
    def flaky(day: date) -> dict:
        if day == date(2026, 10, 15):
            raise ConnectionError("reset")
        return _fetch(day)

    result = watch_dof.watch(flaky, today=date(2026, 10, 16), days=4, client=None)

    assert result["status"] == "ok"
    assert result["failures"][0]["date"] == "2026-10-15"
    assert [item["cod_nota"] for item in result["candidates"]] == [5800977]
    assert result["issues_created_for"] == []


def test_watch_fails_only_when_no_day_could_be_checked(
    tmp_path: Path, monkeypatch
) -> None:
    def down(day: date) -> dict:
        raise ConnectionError("blocked")

    monkeypatch.setattr(watch_dof, "_fetch_day_from_sidof", down)
    result_path = tmp_path / "watch.json"
    assert (
        watch_dof.main(
            [
                "--days",
                "2",
                "--today",
                "2026-10-16",
                "--result",
                str(result_path),
                "--dry-run",
            ]
        )
        == 1
    )
    assert json.loads(result_path.read_text(encoding="utf-8"))["status"] == "failed"
