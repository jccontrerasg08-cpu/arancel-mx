from datetime import date
import json
from pathlib import Path

import pytest

from arancel_mx.sources.sidof import (
    is_tariff_relevant,
    latest_snice_fractions_workbook,
    note_by_code_url,
    notes_by_date_url,
    parse_notes,
    tariff_candidates,
)

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "sidof" / "notas-13-10-2026.json"
)


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parse_notes_reads_real_listing() -> None:
    notes = parse_notes(_payload())

    assert len(notes) == 7
    decree = next(note for note in notes if note.cod_nota == 5800977)
    assert decree.published_on == date(2026, 10, 13)
    assert decree.edition == "MAT"
    assert decree.cod_diario == 330185
    assert decree.has_doc and decree.has_pdf
    assert decree.public_url == "https://sidof.segob.gob.mx/notas/5800977"
    assert decree.doc_url.endswith("/documentos/doc/5800977")
    assert decree.edition_pdf_url.endswith("/documentos/pdf/330185")


def test_tariff_candidates_keep_only_the_tarifa_decree() -> None:
    assert [note.cod_nota for note in tariff_candidates(_payload())] == [5800977]


@pytest.mark.parametrize(
    "title",
    [
        "DECRETO por el que se modifica la Tarifa de la Ley de los Impuestos Generales de Importación y de Exportación.",
        "ACUERDO que modifica al diverso por el que se dan a conocer los Números de Identificación Comercial (NICO) y sus tablas de correlación.",
        "RESOLUCIÓN final de la investigación antidumping ... se impone una cuota compensatoria definitiva",
        "DECRETO por el que se modifica el diverso por el que se exenta el pago de arancel de importación ... canasta básica",
        "Acuerdo por el que se da a conocer la Decisión No. 129 de la Comisión Administradora del Tratado de Libre Comercio entre los Estados Unidos Mexicanos y la República de Colombia",
        "DECRETO por el que se establecen diversos Programas de Promoción Sectorial",
        "ACUERDO por el que se dan a conocer los cupos para importar azúcar",
    ],
)
def test_relevant_titles(title: str) -> None:
    assert is_tariff_relevant(title)


@pytest.mark.parametrize(
    "title",
    [
        "",
        "Decreto por el que se establecen las condiciones aplicables al tránsito internacional de mercancías",
        "Declaratoria de vigencia de la Norma Mexicana NMX-F-605-NORMEX-2015",
        "Convenio de Coordinación en materia de transferencia de insumos",
        "Aviso: el cargo que ocupo en el Consejo",
    ],
)
def test_irrelevant_titles(title: str) -> None:
    assert not is_tariff_relevant(title)


def test_parse_notes_rejects_error_responses() -> None:
    with pytest.raises(ValueError, match="400"):
        parse_notes({"messageCode": 400, "response": "Fecha inválida"})


def test_service_urls() -> None:
    assert notes_by_date_url(date(2026, 10, 13)) == (
        "https://sidofqa.segob.gob.mx/dof/sidof/notas/13-10-2026"
    )
    assert note_by_code_url(5800977) == (
        "https://sidofqa.segob.gob.mx/dof/sidof/notas/nota/5800977"
    )


def test_latest_snice_fractions_workbook_picks_newest_date() -> None:
    links = [
        "https://www.snice.gob.mx/~oracle/SNICE_DOCS/FRACCIONESARANCELARIAS-LIGIE_20260420-20260420.xlsx",
        "https://www.snice.gob.mx/~oracle/SNICE_DOCS/FRACCIONESARANCELARIAS-LIGIE_20261014-20261014.xlsx",
        "https://www.snice.gob.mx/~oracle/SNICE_DOCS/NICO-MARZO24-LIGIE_20240404-20240404.XLSX",
    ]
    assert latest_snice_fractions_workbook(links) == (date(2026, 10, 14), links[1])
    assert latest_snice_fractions_workbook(links[2:]) is None
