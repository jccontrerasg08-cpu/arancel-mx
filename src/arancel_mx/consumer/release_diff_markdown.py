"""Readable Markdown summary of a release comparison report.

It is a rendering of ``release_diff_report`` and adds nothing: every number and value
comes from the report. Values are escaped so release text cannot add links, HTML or
table cells, and a value that disappeared is written as "sin valor", never as 0.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from arancel_mx.consumer.ficha_markdown import escape
from arancel_mx.domain.normalization import format_code

EVENT_LABELS: dict[str, str] = {
    "row_added": "Código nuevo",
    "row_removed": "Código eliminado",
    "description_changed": "Cambio de descripción",
    "igi_changed": "Cambio de IGI",
    "ige_changed": "Cambio de IGE",
    "unit_changed": "Cambio de unidad",
    "hierarchy_changed": "Cambio de código padre",
    "nom_added": "NOM agregada",
    "nom_removed": "NOM retirada",
    "nom_scope_changed": "Cambio de alcance de NOM",
    "note_added": "Nota agregada",
    "note_removed": "Nota retirada",
    "note_text_changed": "Cambio de texto de nota",
}

LEVEL_LABELS: dict[str, str] = {
    "hs2": "Capítulo",
    "hs4": "Partida",
    "hs6": "Subpartida",
    "fraccion8": "Fracción",
    "nico10": "NICO",
}

AUXILIARY_LABELS: dict[str, str] = {
    "nom": "NOM del Anexo 2.4.1",
    "national_notes": "Notas Nacionales",
}

NOTE = (
    "Diferencias entre dos snapshots publicados. No son eventos legales: confirma el instrumento "
    "del DOF y su entrada en vigor antes de usar un cambio."
)

NO_VALUE = "_sin valor_"


def _value(value: object) -> str:
    if value is None or str(value).strip() == "":
        return NO_VALUE
    return escape(value)


def _code(value: object) -> str:
    text = str(value or "")
    try:
        return f"`{format_code(text)}`"
    except (ValueError, TypeError):
        return escape(text)


def _number(value: object) -> str:
    return f"{int(value):,}" if isinstance(value, int) else escape(value)


def _side(side: Mapping[str, Any]) -> str:
    version = side.get("dataset_version") or "versión desconocida"
    state = "verificada" if side.get("release_verified") else "sin verificación remota"
    return f"{escape(version)} ({state})"


def _auxiliary_identity(change: Mapping[str, Any]) -> str:
    skip = {"event", "old_value", "new_value"}
    return " · ".join(f"{escape(key)} {escape(value)}" for key, value in change.items() if key not in skip)


def _changes_table(changes: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = ["| Código | Nivel | Cambio | Antes | Después |", "|---|---|---|---|---|"]
    for change in changes:
        level = str(change.get("level"))
        event = str(change.get("event"))
        lines.append(
            f"| {_code(change.get('code'))} | {escape(LEVEL_LABELS.get(level, level))} "
            f"| {escape(EVENT_LABELS.get(event, event))} | {_value(change.get('old_value'))} "
            f"| {_value(change.get('new_value'))} |"
        )
    return lines


def release_diff_markdown(report: Mapping[str, Any]) -> str:
    """Render a ``release_diff_report`` as Markdown in Spanish."""

    counts = report.get("counts", {})
    changes: Sequence[Mapping[str, Any]] = report.get("changes", [])
    verified = report.get("comparison_status") == "verified_snapshots"
    lines = [
        f"# Comparación de releases {escape(report['from'].get('dataset_version') or '?')} → "
        f"{escape(report['to'].get('dataset_version') or '?')}",
        "",
        f"> {NOTE}",
        "",
        f"- Desde: {_side(report['from'])}",
        f"- Hasta: {_side(report['to'])}",
        "- Estado de la comparación: "
        + ("snapshots verificados" if verified else "al menos un archivo local sin verificación remota"),
        f"- Filas vigentes: {_number(counts.get('rows_from'))} → {_number(counts.get('rows_to'))}",
        f"- Niveles comparados: {', '.join(escape(LEVEL_LABELS.get(str(level), level)) for level in report.get('levels', []))}",
        f"- Cambios: {_number(counts.get('changes', len(changes)))}",
        "",
        "## Resumen",
        "",
        "| Cambio | Registros |",
        "|---|---|",
    ]
    for event, count in counts.get("by_event", {}).items():
        lines.append(f"| {escape(EVENT_LABELS.get(event, event))} | {_number(count)} |")
    lines += ["", "## Cambios por código", ""]
    if changes:
        lines += _changes_table(changes)
    else:
        lines.append("Las dos releases no difieren en los niveles comparados.")
    auxiliary: Mapping[str, Mapping[str, Any]] = report.get("auxiliary") or {}
    if auxiliary:
        lines += ["", "## Tablas auxiliares"]
        for table, result in auxiliary.items():
            label = escape(AUXILIARY_LABELS.get(table, table))
            lines += ["", f"### {label}", ""]
            if result.get("status") != "compared":
                lines.append(f"No comparada: {escape(result.get('reason') or 'sin motivo publicado')}.")
                continue
            rows = result.get("changes") or []
            if not rows:
                lines.append("Sin diferencias.")
                continue
            lines += ["| Registro | Cambio | Antes | Después |", "|---|---|---|---|"]
            for change in rows:
                event = str(change.get("event"))
                lines.append(
                    f"| {_auxiliary_identity(change)} | {escape(EVENT_LABELS.get(event, event))} "
                    f"| {_value(change.get('old_value'))} | {_value(change.get('new_value'))} |"
                )
    return "\n".join(lines) + "\n"
