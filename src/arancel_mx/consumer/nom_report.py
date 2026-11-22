"""Annex 2.4.1 NOM rows for one code, with the same states as the record page.

The report repeats what the release publishes. It never says that a NOM does or does
not apply: a fraction the annex does not list is reported as "not listed", and a
release that cannot tell is reported as "unknown", never as "no NOM".
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict
from typing import Any

from arancel_mx.consumer.ficha_markdown import annex_state
from arancel_mx.consumer.models import NomRequirement

NOM_REPORT_POLICY = "nom-report-v1"

STATE_TEXT: dict[str, str] = {
    "listed": "El Anexo 2.4.1 de esta release lista NOM para la fracción.",
    "not_listed": (
        "El Anexo 2.4.1 de esta release no lista NOM para la fracción. "
        "No descarta otras regulaciones y restricciones no arancelarias."
    ),
    "not_listed_carried": (
        "El anexo de esta release viene de una release anterior y no lista NOM para la fracción. "
        "No descarta otras regulaciones y restricciones no arancelarias."
    ),
    "unavailable": "La release no pudo leer el Anexo 2.4.1: no se sabe si lista NOM para la fracción.",
    "unknown": "La release no publica el estado del Anexo 2.4.1: no se sabe si lista NOM para la fracción.",
    "not_a_fraction": "El Anexo 2.4.1 se consulta por fracción de 8 dígitos o NICO de 10.",
}

NOTE = (
    "Repite el Anexo 2.4.1 publicado en la release; no es una determinación de cumplimiento. "
    "Confirma en el DOF la versión vigente del Acuerdo de NOM de la SE."
)


def _nico_match(requirement: NomRequirement, nico: str | None) -> str | None:
    """How a row's NICO limits relate to the code asked for; None when no NICO was asked for."""

    if nico is None:
        return None
    listed = {str(item.get("nico")) for item in requirement.nico}
    if not listed:
        return "no_nico_limits"
    return "listed" if nico in listed else "other_nico"


def nom_report(
    code: str,
    *,
    requirements: Iterable[NomRequirement],
    annex: Mapping[str, Any] | None,
    dataset_version: str | None,
) -> dict[str, object]:
    """Build the report for one canonical code (2–10 digits)."""

    fraction = code[:8] if len(code) >= 8 else None
    nico = code[8:10] if len(code) == 10 else None
    rows = tuple(item for item in requirements if fraction and item.fraction8 == fraction)
    state = annex_state(annex, rows, code)
    return {
        "policy_version": NOM_REPORT_POLICY,
        "dataset_version": dataset_version,
        "code": code,
        "fraction8": fraction,
        "annex": dict(annex or {"status": "not_included"}),
        "state": state,
        "message": STATE_TEXT[state],
        "requirements": [
            {**asdict(item), "nico": list(item.nico), "nico_match": _nico_match(item, nico)}
            for item in sorted(rows, key=lambda item: (item.numeral, item.nom, item.annex_page))
        ],
        "note": NOTE,
    }
