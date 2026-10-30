"""Build the rate-validity registry from captured LIGIE 2022 instruments.

Reads the PDFs that ``scripts/capture_instrument_research.py`` captured from the
Cámara de Diputados ledger, extracts each instrument's Tarifa rows with
``arancel_mx.parsers.decrees`` and writes
``src/arancel_mx/sources/legal_instruments.json``. The instrument facts below
(entry into force, end of validity) come from the transitory articles and are
recorded in ``docs/research/ligie-instrument-inventory.md``. Run it again, and
review the diff, whenever the DOF publishes a new Tarifa instrument.

Usage::

    python -m scripts.extract_legal_instruments --documents research-capture/documents
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Sequence

import pymupdf

from arancel_mx.parsers.decrees import parse_decree_rows

LEDGER = "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022/"
OUTPUT = Path("src/arancel_mx/sources/legal_instruments.json")
VERSION = "2026-10-30"

# Instruments whose Tarifa rows set a general IGI/IGE rate. validity_end is the
# last day the rate applies (inclusive); abrogation ends the day before the
# abrogating instrument enters into force.
INSTRUMENTS = (
    {
        "id": "orig",
        "kind": "base",
        "title": "DECRETO por el que se expide la Ley de los Impuestos Generales de Importación y de Exportación.",
        "dof_date": "2022-06-07",
        "file": "LIGIE_2022_orig_07jun22.pdf",
        "entry_into_force": "2022-12-12",
        "entry_rule": (
            "Transitorio Primero: diez días hábiles después de que el SAT determine que los sistemas están listos. "
            "Cuarta Resolución de Modificaciones a las RGCE para 2022 (DOF 2022-12-05), artículo segundo: "
            "entra en vigor el 12 de diciembre de 2022."
        ),
        "validity_end": None,
    },
    {
        "id": "tarifa07",
        "kind": "temporary_rate",
        "title": "DECRETO por el que se modifica la Tarifa (tasas temporales en 392 fracciones).",
        "dof_date": "2023-08-15",
        "file": "LIGIE_2022_tarifa07_15ago23.pdf",
        "entry_into_force": "2023-08-16",
        "entry_rule": "Fecha fija.",
        "validity_end": "2024-04-22",
        "end_rule": "Abrogado por tarifa09, en vigor desde el 2024-04-23.",
    },
    {
        "id": "tarifa09",
        "kind": "temporary_rate",
        "title": "DECRETO por el que se modifica la Tarifa (tasas temporales en 544 fracciones).",
        "dof_date": "2024-04-22",
        "file": "LIGIE_2022_tarifa09_22abr24.pdf",
        "entry_into_force": "2024-04-23",
        "entry_rule": "Día siguiente al de su publicación.",
        "validity_end": "2026-04-23",
        "end_rule": "Vigencia de dos años contados a partir de su entrada en vigor.",
    },
    {
        "id": "tarifa10",
        "kind": "modify_rate",
        "title": "DECRETO por el que se reforma el diverso del 22 de abril de 2024 (sulfato de amonio 35 %).",
        "dof_date": "2024-05-08",
        "file": "LIGIE_2022_tarifa10_08may24.pdf",
        "entry_into_force": "2024-05-09",
        "entry_rule": "Día siguiente al de su publicación.",
        "validity_end": None,
    },
    {
        "id": "tarifa11",
        "kind": "temporary_rate",
        "title": "DECRETO por el que se modifica la Tarifa y el Decreto IMMEX (prendas de vestir y textiles).",
        "dof_date": "2024-12-19",
        "file": "LIGIE_2022_tarifa11_19dic24.pdf",
        "entry_into_force": "2024-12-20",
        "entry_rule": "Día siguiente al de su publicación.",
        "validity_end": "2026-04-23",
        "end_rule": "Vigente hasta el 23 de abril de 2026.",
    },
    {
        "id": "tarifa13",
        "kind": "modify_rate",
        "title": "DECRETO por el que se modifica la Tarifa (azúcar).",
        "dof_date": "2025-11-10",
        "file": "LIGIE_2022_tarifa13_10nov25.pdf",
        "entry_into_force": "2025-11-11",
        "entry_rule": "Día siguiente al de su publicación.",
        "validity_end": None,
    },
    {
        "id": "ref02",
        "kind": "modify_rate",
        "title": "DECRETO por el que se reforman diversas fracciones arancelarias de la Tarifa de la LIGIE.",
        "dof_date": "2025-12-29",
        "file": "LIGIE_2022_ref02_29dic25.pdf",
        "entry_into_force": "2026-01-01",
        "entry_rule": "Fecha fija.",
        "validity_end": None,
    },
    {
        "id": "ref01",
        "kind": "modify_rate",
        "title": "DECRETO por el que se reforman y adicionan diversas disposiciones de la LIGIE (totoaba).",
        "dof_date": "2025-07-21",
        "file": "LIGIE_2022_ref01_21jul25.pdf",
        "entry_into_force": "2026-01-17",
        "entry_rule": "180 días después de su publicación.",
        "validity_end": None,
    },
    {
        "id": "tarifa15",
        "kind": "modify_rate",
        "title": "DECRETO por el que se modifica la Tarifa y el Decreto PROSEC.",
        "dof_date": "2026-04-23",
        "file": "LIGIE_2022_tarifa15_23abr26.pdf",
        "entry_into_force": "2026-04-24",
        "entry_rule": "Día siguiente al de su publicación.",
        "validity_end": None,
    },
    {
        "id": "tarifa16",
        "kind": "temporary_rate",
        "title": "DECRETO por el que se modifica la Tarifa (9803.00.01, partes para ensamble automotriz).",
        "dof_date": "2026-10-13",
        "file": "LIGIE_2022_tarifa16_13oct26.pdf",
        "entry_into_force": "2026-10-14",
        "entry_rule": "Día siguiente al de su publicación.",
        "validity_end": "2031-10-14",
        "end_rule": (
            "Vigencia de cinco años contados a partir de su entrada en vigor; el plazo vence el mismo día "
            "del año de calendario correspondiente (artículo 12 del Código Fiscal de la Federación)."
        ),
    },
)

# Instruments whose effect on the general rate this registry does not model.
# A fraction they mention keeps its rate but gets no inferred start date.
UNMODELED = (
    {
        "id": "tarifa02",
        "dof_date": "2022-11-18",
        "file": "LIGIE_2022_tarifa02_18nov22.pdf",
        "reason": "Tasas escalonadas y tablas de programas sectoriales (desgravaciones del acero, frontera, IMMEX).",
    },
    {
        "id": "tarifa01",
        "dof_date": "2022-11-18",
        "file": "LIGIE_2022_tarifa01_18nov22.pdf",
        "reason": "Exención temporal de arancel, abrogada el 2023-05-17.",
    },
    {
        "id": "tarifa04",
        "dof_date": "2023-01-16",
        "file": "LIGIE_2022_tarifa04_16ene23.pdf",
        "reason": "Maíz blanco, temporal hasta el 2023-06-30, abrogado por tarifa06.",
    },
    {
        "id": "tarifa06",
        "dof_date": "2023-06-23",
        "file": "LIGIE_2022_tarifa06_23jun23.pdf",
        "reason": "Maíz blanco, temporal hasta el 2023-12-31.",
    },
)

_CODE = re.compile(r"\b(\d{4})\.(\d{2})\.(\d{2})\b")


def _find(documents: Path, name: str) -> Path:
    matches = sorted(documents.glob(f"*_{name}"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"expected one captured copy of {name}, found {len(matches)}"
        )
    return matches[0]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mentioned_codes(path: Path) -> list[str]:
    codes: set[str] = set()
    with pymupdf.open(path) as document:
        for page in document:
            codes.update("".join(match) for match in _CODE.findall(page.get_text()))
    return sorted(codes)


def build_registry(documents: Path) -> dict[str, object]:
    instruments = []
    for spec in INSTRUMENTS:
        path = _find(documents, spec["file"])
        rows = parse_decree_rows(path)
        codes = [row.code for row in rows]
        if len(set(codes)) != len(codes):
            raise ValueError(f"{spec['id']}: duplicate fraction rows")
        entry = {key: value for key, value in spec.items() if key != "file"}
        entry["source_url"] = LEDGER + spec["file"]
        entry["sha256"] = _sha256(path)
        entry["rows"] = [[row.code, row.igi, row.ige] for row in rows]
        instruments.append(entry)
    unmodeled = []
    for spec in UNMODELED:
        path = _find(documents, spec["file"])
        entry = {key: value for key, value in spec.items() if key != "file"}
        entry["source_url"] = LEDGER + spec["file"]
        entry["sha256"] = _sha256(path)
        entry["codes"] = _mentioned_codes(path)
        unmodeled.append(entry)
    return {
        "kind": "arancel-mx/ligie-rate-instruments",
        "version": VERSION,
        "ledger_url": "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm",
        "instruments": instruments,
        "unmodeled": unmodeled,
    }


def render(registry: dict[str, object]) -> str:
    """Pretty JSON with one tariff row or code per line, so diffs stay reviewable."""
    text = json.dumps(registry, ensure_ascii=False, indent=2)
    # Collapse each [code, igi, ige] row onto one line.
    text = re.sub(
        r"\[\n\s+(\"[^\"\n]*\"|null),\n\s+(\"[^\"\n]*\"|null),\n\s+(\"[^\"\n]*\"|null)\n\s+\]",
        r"[\1, \2, \3]",
        text,
    )
    return text + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    registry = build_registry(args.documents)
    args.out.write_text(render(registry), encoding="utf-8")
    counts = {item["id"]: len(item["rows"]) for item in registry["instruments"]}
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
