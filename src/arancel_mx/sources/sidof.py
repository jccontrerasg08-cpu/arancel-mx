"""Read-only access to the official SIDOF web services of the Diario Oficial.

SIDOF publishes documented JSON services (Consultar Notas, Consultar Diarios,
Obtener Documentos, Dec. 2018) that list every note of a DOF day. This module
turns one day's listing into tariff-relevant candidates and builds the URLs of
the note's Word document and the signed edition PDF. It never classifies,
interprets or applies an instrument; a candidate is only a lead for review.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any, Mapping

SIDOF_API_BASE = "https://sidofqa.segob.gob.mx/dof/sidof"
SIDOF_ALLOWED_HOSTS = ("sidofqa.segob.gob.mx",)
SIDOF_PUBLIC_NOTE_URL = "https://sidof.segob.gob.mx/notas/{cod_nota}"

_EDITIONS = (
    ("NotasMatutinas", "MAT"),
    ("NotasVespertinas", "VES"),
    ("NotasExtraordinarias", "EXT"),
)

# Titles of instruments that create, change or condition LIGIE/TIGIE rates or
# the measures tracked by the depth program. Matching is accent- and
# case-insensitive. A miss is cheaper than noise only up to a point, so the
# terms stay specific to tariff instruments rather than to "Economía" at large.
_RELEVANT_TITLE = re.compile(
    r"impuestos generales de importacion"
    r"|tarifa de la ley"
    r"|\btigie\b"
    r"|numeros? de identificacion comercial"
    r"|notas nacionales"
    r"|tablas? de correlacion"
    r"|arancel"
    r"|\bcupos?\b"
    r"|cuota(?:s)? compensatoria"
    r"|promocion sectorial"
    r"|\bprosec\b"
    r"|industria manufacturera, maquiladora"
    r"|\bimmex\b"
    r"|regla octava"
    r"|canasta basica"
    r"|tratado de libre comercio"
    r"|reglas de origen"
)

_FOLD = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


@dataclass(frozen=True)
class DofNote:
    cod_nota: int
    cod_diario: int
    published_on: date
    edition: str
    section: str
    title: str
    organism: str
    page: int | None
    has_doc: bool
    has_pdf: bool

    @property
    def public_url(self) -> str:
        return SIDOF_PUBLIC_NOTE_URL.format(cod_nota=self.cod_nota)

    @property
    def doc_url(self) -> str:
        return f"{SIDOF_API_BASE}/documentos/doc/{self.cod_nota}"

    @property
    def edition_pdf_url(self) -> str:
        """Signed PDF of the whole edition (carries the DOF e.firma)."""
        return f"{SIDOF_API_BASE}/documentos/pdf/{self.cod_diario}"


def notes_by_date_url(day: date) -> str:
    return f"{SIDOF_API_BASE}/notas/{day:%d-%m-%Y}"


def note_by_code_url(cod_nota: int) -> str:
    return f"{SIDOF_API_BASE}/notas/nota/{cod_nota}"


def _fold(value: str) -> str:
    return " ".join(value.translate(_FOLD).lower().split())


def is_tariff_relevant(title: str) -> bool:
    return bool(title) and _RELEVANT_TITLE.search(_fold(title)) is not None


def _parse_day(value: object) -> date:
    day, month, year = str(value).split("-")
    return date(int(year), int(month), int(day))


def _flag(value: object) -> bool:
    return str(value).upper() == "S"


def parse_notes(payload: Mapping[str, Any]) -> tuple[DofNote, ...]:
    """Parse a ``/notas/{fecha}`` response; reject anything but a 200/OK."""
    if payload.get("messageCode") != 200 or payload.get("response") != "OK":
        raise ValueError(
            f"SIDOF responded {payload.get('messageCode')!r}: {payload.get('response')!r}"
        )
    notes: list[DofNote] = []
    for key, edition in _EDITIONS:
        for item in payload.get(key) or ():
            page = item.get("pagina")
            notes.append(
                DofNote(
                    cod_nota=int(item["codNota"]),
                    cod_diario=int(item["codDiario"]),
                    published_on=_parse_day(item["fecha"]),
                    edition=edition,
                    section=str(item.get("codSeccion") or ""),
                    title=" ".join(str(item.get("titulo") or "").split()),
                    organism=str(item.get("codOrgaDos") or ""),
                    page=int(page) if isinstance(page, (int, float)) else None,
                    has_doc=_flag(item.get("existeDoc")),
                    has_pdf=_flag(item.get("existePdf")),
                )
            )
    return tuple(notes)


def tariff_candidates(payload: Mapping[str, Any]) -> tuple[DofNote, ...]:
    """Notes of one DOF day whose title points to a tariff instrument."""
    return tuple(
        note for note in parse_notes(payload) if is_tariff_relevant(note.title)
    )


# SNICE publishes the Tarifa workbook the pipeline reads under a dated name,
# e.g. FRACCIONESARANCELARIAS-LIGIE_20261014-20261014.xlsx.
_SNICE_FRACTIONS_WORKBOOK = re.compile(
    r"/SNICE_DOCS/FRACCIONESARANCELARIAS-LIGIE_(\d{8})-\d{8}\.xlsx", re.IGNORECASE
)


def latest_snice_fractions_workbook(
    links: list[str] | tuple[str, ...],
) -> tuple[date, str] | None:
    """Return the newest dated fractions workbook linked from the SNICE LIGIE page."""
    found: list[tuple[date, str]] = []
    for link in links:
        match = _SNICE_FRACTIONS_WORKBOOK.search(link)
        if match:
            stamp = match.group(1)
            found.append((date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:])), link))
    return max(found) if found else None
