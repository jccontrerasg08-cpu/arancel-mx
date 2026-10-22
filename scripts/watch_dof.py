"""Daily, read-only DOF watch through the official SIDOF services (decision 0002).

Checks the last ``--days`` DOF days, so a missed run is caught by the next one,
keeps the notes whose title points to a tariff instrument, and opens one GitHub
issue per new note for human review. An issue is the confirmation step: this
script never builds, changes or publishes data.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import quote
from zoneinfo import ZoneInfo

from arancel_mx.sources.http import (
    build_official_session,
    decode_fetched_text,
    fetch_official_document,
)
from arancel_mx.sources.sidof import (
    SIDOF_ALLOWED_HOSTS,
    DofNote,
    notes_by_date_url,
    tariff_candidates,
)
from scripts.github_api import GitHubApi, GitHubApiError, GitHubNotFound

LABEL = "dof-candidate"
LABEL_COLOR = "1d76db"
LABEL_DESCRIPTION = (
    "Instrumento del DOF detectado por la vigilancia diaria; requiere revisión humana"
)
MARKER = "<!-- arancel-mx-dof-note:{cod_nota} -->"
MEXICO_CITY = ZoneInfo("America/Mexico_City")

FetchDay = Callable[[date], Mapping[str, Any]]


def days_to_check(today: date, days: int) -> list[date]:
    return [today - timedelta(days=offset) for offset in range(days)]


def issue_title(note: DofNote) -> str:
    title = note.title if len(note.title) <= 180 else note.title[:177] + "..."
    return f"DOF {note.published_on:%Y-%m-%d}: {title}"


def issue_body(note: DofNote) -> str:
    return "\n".join(
        [
            "La vigilancia diaria del DOF detectó una publicación que puede cambiar la Tarifa o una medida relacionada.",
            "",
            "| Campo | Valor |",
            "|---|---|",
            f"| Fecha | {note.published_on:%Y-%m-%d} |",
            f"| Edición | {note.edition} · sección {note.section or '—'} · página {note.page or '—'} |",
            f"| Organismo | {note.organism or '—'} |",
            f"| Nota DOF | [{note.cod_nota}]({note.public_url}) |",
            f"| Documento Word | {note.doc_url if note.has_doc else '—'} |",
            f"| Edición completa firmada (PDF) | {note.edition_pdf_url} |",
            "",
            "**Revisión humana**",
            "",
            "- [ ] Confirmar si el instrumento cambia tasas, fracciones, NICO o medidas que sigue el proyecto.",
            "- [ ] Si las cambia, registrar sus operaciones y su entrada en vigor en el inventario de instrumentos.",
            "- [ ] Comprobar que la siguiente release certificada lo refleje, o documentar por qué no.",
            "",
            "Esta alerta no es una interpretación jurídica: es un aviso para revisar la fuente primaria.",
            "",
            MARKER.format(cod_nota=note.cod_nota),
        ]
    )


def _ensure_label(client: GitHubApi) -> None:
    try:
        client.request_json("GET", f"/labels/{quote(LABEL, safe='')}")
        return
    except GitHubNotFound:
        pass
    try:
        client.request_json(
            "POST",
            "/labels",
            json={
                "name": LABEL,
                "color": LABEL_COLOR,
                "description": LABEL_DESCRIPTION,
            },
        )
    except GitHubApiError as error:
        if error.status_code != 422:
            raise


def _known_notes(client: GitHubApi) -> set[int]:
    issues = client.request_json(
        "GET", f"/issues?state=all&labels={LABEL}&per_page=100"
    )
    if not isinstance(issues, list):
        raise ValueError("GitHub issues response must be a list")
    known: set[int] = set()
    for issue in issues:
        body = str(issue.get("body") or "") if isinstance(issue, Mapping) else ""
        start = body.find("<!-- arancel-mx-dof-note:")
        if start >= 0:
            value = body[start + len("<!-- arancel-mx-dof-note:") :].split(" ", 1)[0]
            if value.isdigit():
                known.add(int(value))
    return known


def watch(
    fetch_day: FetchDay,
    *,
    today: date,
    days: int,
    client: GitHubApi | None,
) -> dict[str, Any]:
    checked: list[str] = []
    failures: list[dict[str, str]] = []
    candidates: list[DofNote] = []
    for day in days_to_check(today, days):
        try:
            candidates.extend(tariff_candidates(fetch_day(day)))
            checked.append(day.isoformat())
        except Exception as error:  # one unreachable day must not hide the others
            failures.append(
                {
                    "date": day.isoformat(),
                    "error": f"{type(error).__name__}: {error}"[:300],
                }
            )

    created: list[int] = []
    if client is not None and candidates:
        _ensure_label(client)
        known = _known_notes(client)
        for note in sorted(
            candidates, key=lambda item: (item.published_on, item.cod_nota)
        ):
            if note.cod_nota in known:
                continue
            client.request_json(
                "POST",
                "/issues",
                json={
                    "title": issue_title(note),
                    "body": issue_body(note),
                    "labels": [LABEL],
                },
            )
            known.add(note.cod_nota)
            created.append(note.cod_nota)

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "days_checked": checked,
        "failures": failures,
        "candidates": [
            {**asdict(note), "published_on": note.published_on.isoformat()}
            for note in candidates
        ],
        "issues_created_for": created,
        "status": "failed" if not checked else "ok",
    }


def _fetch_day_from_sidof(day: date) -> Mapping[str, Any]:
    session = build_official_session()
    document = fetch_official_document(
        session,
        notes_by_date_url(day),
        SIDOF_ALLOWED_HOSTS,
        ("application/json", "text/plain", "text/html"),
        timeout_s=60.0,
        max_bytes=20 * 1024 * 1024,
    )
    payload = json.loads(decode_fetched_text(document))
    if not isinstance(payload, Mapping):
        raise ValueError("SIDOF response must be a JSON object")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--today", type=date.fromisoformat, default=None)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument(
        "--dry-run", action="store_true", help="Do not open GitHub issues"
    )
    args = parser.parse_args(argv)

    today = args.today or datetime.now(MEXICO_CITY).date()
    client = None
    if not args.dry_run:
        client = GitHubApi(
            os.environ["GITHUB_REPOSITORY"],
            os.environ["GITHUB_TOKEN"],
            api_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
        )
    result = watch(_fetch_day_from_sidof, today=today, days=args.days, client=client)
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "days_checked": len(result["days_checked"]),
                "failures": len(result["failures"]),
                "candidates": len(result["candidates"]),
                "issues_created_for": result["issues_created_for"],
            }
        )
    )
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
