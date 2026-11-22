"""Markdown export of one tariff card, built only from the verified dataset.

Nothing is computed or inferred: a value the release does not publish is written as not published, never as 0,
"exento" or "no aplica". Text taken from the data is escaped so it renders literally, and only http(s) links are
written. The card states that it is not an official classification and does not determine duties or compliance.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from urllib.parse import urlsplit

from arancel_mx.consumer.models import Ficha, NationalNote, NomRequirement, ProvenanceRecord
from arancel_mx.consumer.query import format_code

_SPECIAL = str.maketrans({character: f"\\{character}" for character in "\\`*_[]<>|~"})

DISCLAIMER = (
    "Ficha de consulta generada con datos de una release de arancel-mx. No es una clasificación arancelaria "
    "oficial, no determina contribuciones ni el cumplimiento de regulaciones y no sustituye la consulta del DOF "
    "y de la autoridad competente."
)
NOT_PUBLISHED = "_No publicado en esta release_"

_ANNEX_TEXT = {
    "not_listed": "La fracción no aparece en el Anexo 2.4.1 tal como se leyó en esta release. Otras regulaciones pueden aplicar.",
    "not_listed_carried": "La fracción no aparece en el Anexo 2.4.1 leído en una release anterior, porque el anexo vigente no se pudo leer. Anexo leído en la release",
    "unavailable": "Los datos del Anexo 2.4.1 no están disponibles en esta release.",
    "unknown": "La release no indica si incluye el Anexo 2.4.1; no se puede saber si la fracción aparece.",
}


def escape(value: object) -> str:
    """Escape Markdown so data text cannot add links, HTML or table cells."""

    return " ".join(str(value).splitlines()).translate(_SPECIAL)


def safe_url(value: object) -> str | None:
    """Return the URL only when it is plain http(s)."""

    parts = urlsplit(str(value))
    return str(value) if parts.scheme in {"http", "https"} and parts.netloc else None


def _link(label: str, url: object) -> str:
    target = safe_url(url)
    return f"[{escape(label)}](<{target.replace('>', '%3E')}>)" if target else escape(label)


def _present(value: object) -> bool:
    return value is not None and str(value).strip() != ""


def _note_order(note: NationalNote) -> tuple[int, int, str]:
    number = note.note_number.strip()
    return (0 if note.scope_type == "section" else 1, int(number) if number.isdigit() else 10**6, number)


def annex_state(annex: Mapping[str, object] | None, requirements: Iterable[NomRequirement], code: str) -> str:
    """Same states as the record page: listed, not_listed, not_listed_carried, unavailable, unknown, not_a_fraction."""

    if len(code) < 8:
        return "not_a_fraction"
    if any(True for _ in requirements):
        return "listed"
    status = (annex or {}).get("status")
    return {
        "available": "not_listed",
        "carried_forward": "not_listed_carried",
        "unavailable": "unavailable",
    }.get(str(status), "unknown")


def ficha_markdown(
    ficha: Ficha,
    *,
    generated_at: str,
    release_verified: bool,
    provenance: Iterable[ProvenanceRecord] = (),
    nom_requirements: Iterable[NomRequirement] = (),
    annex: Mapping[str, object] | None = None,
    national_notes: Iterable[NationalNote] = (),
) -> str:
    record = ficha.record
    code = record.code
    fraction = code[:8]
    noms = tuple(item for item in nom_requirements if item.fraction8 == fraction) if len(code) >= 8 else ()

    def value(item: object) -> str:
        return escape(item) if _present(item) else NOT_PUBLISHED

    validity = (
        f"desde {escape(record.effective_from)}" + (f" hasta {escape(record.effective_to)}" if record.effective_to else "")
        if record.effective_from
        else NOT_PUBLISHED
    )
    lines = [
        f"# Ficha arancelaria {escape(ficha.formatted_code)}",
        "",
        f"> {DISCLAIMER}",
        "",
        f"- **Release de datos:** data-{escape(record.dataset_version)}"
        + (" (verificada)" if release_verified else " (archivo local, sin verificación remota)"),
        f"- **Generada el:** {escape(generated_at)}",
        "",
        "| | |",
        "|---|---|",
        f"| Código | {escape(code)} |",
        f"| Descripción | {value(record.description)} |",
        f"| Unidad de medida | {value(record.unit_name)} |",
        f"| IGI (importación) | {value(record.igi_text)} |",
        f"| IGE (exportación) | {value(record.ige_text)} |",
        f"| Vigencia de la tasa publicada | {validity} |",
    ]
    if ficha.section is not None or ficha.hierarchy:
        lines += ["", "## Jerarquía", ""]
        if ficha.section is not None:
            lines.append(f"- Sección {escape(ficha.section.roman)} — {escape(ficha.section.name)}")
        for node in ficha.hierarchy:
            if node.code != code:
                lines.append(f"- {escape(format_code(node.code))} — {escape(node.description)}")
    state = annex_state(annex, noms, code)
    if state != "not_a_fraction":
        lines += ["", "## NOM del Anexo 2.4.1", ""]
        if state == "listed":
            lines += [
                "Normas que el anexo lista para esta fracción. Esto señala qué revisar; no determina si el producto está sujeto.",
                "",
            ]
            for item in noms:
                details = "; ".join(
                    part
                    for part in (
                        f"acotación: {escape(item.scope)}" if _present(item.scope) else "",
                        f"página {item.annex_page}",
                    )
                    if part
                )
                lines.append(f"- {escape(item.nom)} (numeral {item.numeral}; {details})")
        else:
            text = _ANNEX_TEXT[state]
            carried = (annex or {}).get("carried_from")
            lines.append(f"{text} {escape(carried)}." if state == "not_listed_carried" and carried else text)
    notes = tuple(sorted(national_notes, key=_note_order))
    if notes:
        lines += ["", "## Notas nacionales", "", "Orientan la clasificación; no la resuelven.", ""]
        for note in notes:
            kind = "Sección" if note.scope_type == "section" else "Capítulo"
            scope = f"{kind} {note.scope_value or note.chapter}"
            lines.append(f"- **Nota {escape(note.note_number)} ({escape(scope)}):** {escape(note.text)}")
    lines += ["", "## Fuentes registradas", ""]
    sources = tuple(provenance)
    if sources:
        for source in sources:
            label = source.title or source.source_url
            sha = f" — SHA-256 `{escape(source.sha256)}`" if _present(source.sha256) else ""
            lines.append(f"- {_link(label, source.source_url)} ({escape(source.authority)}){sha}")
    else:
        lines.append("La release no registra fuentes para este código.")
    return "\n".join(lines) + "\n"
