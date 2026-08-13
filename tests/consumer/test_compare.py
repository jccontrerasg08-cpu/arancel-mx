from pathlib import Path

import pytest

from arancel_mx.consumer import Dataset
from arancel_mx.consumer.compare import compare_code
from arancel_mx.consumer.errors import InvalidCodeError
from arancel_mx.consumer.models import CompareRow, TariffRecord
from arancel_mx.sources.vucem import VUCEM_SAMPLE_FRACTION_SHEET_URL, fraction_sheet_url, parse_fraction_sheet


FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "vucem" / "buildHojas1.90014002.html"
)


def _record(code: str, level: str, *, description: str, igi: str, ige: str) -> TariffRecord:
    parents = {
        "hs6": "9001",
        "fraccion8": "900140",
        "nico10": "90014002",
    }
    return TariffRecord(
        code=code,
        level=level,
        description=description,
        unit_name=None,
        igi_text=igi,
        igi_kind="exento",
        igi_value=0.0,
        ige_text=ige,
        ige_kind="exento",
        ige_value=0.0,
        parent_code=parents[level],
        dataset_version="2026.08.11",
        schema_version="2",
        effective_from=None,
        effective_to=None,
        is_current=True,
    )


HS6 = _record(
    "900140",
    "hs6",
    description="Lentes de cristal oftálmico",
    igi="Ex.",
    ige="Ex.",
)
MX8 = _record(
    "90014002",
    "fraccion8",
    description=(
        "Lentes de cristal oftálmico, sin graduación, destinados a la fabricación de "
        "anteojos de seguridad, con espesor igual o superior a 3 mm sin exceder de 3.8 mm."
    ),
    igi="Ex.",
    ige="Ex.",
)
NICO = _record(
    "9001400200",
    "nico10",
    description=MX8.description,
    igi="Ex.",
    ige="Ex.",
)


class FakeTariff:
    def lookup(self, code: str) -> TariffRecord:
        if code == "01":
            return TariffRecord(
                code="01",
                level="hs2",
                description="Animales vivos.",
                unit_name=None,
                igi_text=None,
                igi_kind=None,
                igi_value=None,
                ige_text=None,
                ige_kind=None,
                ige_value=None,
                parent_code=None,
                dataset_version="2026.08.11",
                schema_version="2",
                effective_from=None,
                effective_to=None,
                is_current=True,
            )
        return {"900140": HS6, "90014002": MX8, "9001400200": NICO}[code]

    def children(self, code: str) -> tuple[TariffRecord, ...]:
        return {
            "900140": (MX8,),
            "90014002": (NICO,),
            "9001400200": (),
            "01": (),
        }[code]

    def parent(self, code: str) -> TariffRecord | None:
        return {"9001400200": MX8, "90014002": HS6, "900140": None, "01": None}[code]


def _sheet(_code: str):
    html = FIXTURE.read_text(encoding="utf-8")
    return parse_fraction_sheet(html, base_url=VUCEM_SAMPLE_FRACTION_SHEET_URL)


def test_compare_mx8_and_nico_against_vucem_fixture():
    rows = compare_code(FakeTariff(), "90014002", get_sheet=_sheet)
    by_key = {(row.code, row.field): row for row in rows}
    assert by_key[("90014002", "igi")].match is True
    assert by_key[("90014002", "ige")].match is True
    assert by_key[("9001400200", "igi")].match is True
    assert all(row.other_source == "vucem" for row in rows)


def test_compare_hs6_walks_mx8_and_nico_children():
    rows = compare_code(FakeTariff(), "900140", get_sheet=_sheet)
    codes = {row.code for row in rows}
    assert codes == {"900140", "90014002", "9001400200"}
    hs6 = next(row for row in rows if row.code == "900140")
    assert hs6.match is None
    assert "no hs6 page" in hs6.note


def test_compare_nico_uses_parent_vucem_sheet():
    rows = compare_code(FakeTariff(), "9001400200", get_sheet=_sheet)
    assert {row.field for row in rows} == {"description", "igi", "ige"}
    assert all(row.match is True for row in rows)


def test_compare_rejects_hs2_and_skips_fetch_offline():
    with pytest.raises(InvalidCodeError, match="hs6, fraccion8, or nico10"):
        compare_code(FakeTariff(), "01", get_sheet=_sheet)
    skipped = compare_code(FakeTariff(), "90014002", fetch=False)
    assert skipped[0].match is None
    assert "offline" in skipped[0].note


def test_compare_row_is_frozen():
    row = CompareRow(
        code="90014002",
        level="fraccion8",
        field="igi",
        dataset="Ex.",
        other="Ex.",
        other_source="vucem",
        match=True,
    )
    with pytest.raises(Exception):
        row.match = False  # type: ignore[misc]


def _vucem_html(code8: str, description: str, igi: str, ige: str) -> str:
    dotted = f"{code8[:4]}.{code8[4:6]}.{code8[6:]}"
    return (
        "<!doctype html><html><body>"
        f"<h2>Fracción Arancelaria: {dotted} ({code8})</h2>"
        f"<p>{description}</p>"
        "<table><tr><th>Fracción</th><th>Descripción</th><th>IGI</th><th>IGE</th></tr>"
        f"<tr><td>{dotted}</td><td>{description}</td><td>{igi}</td><td>{ige}</td></tr>"
        "</table>"
        "<table><tr><th>NICO</th><th>Descripción</th><th>IGI</th><th>IGE</th></tr>"
        f"<tr><td>00</td><td>{description}</td><td>{igi}</td><td>{ige}</td></tr>"
        "</table></body></html>"
    )


def _sheet_from_html(html: str):
    def get_sheet(code: str):
        return parse_fraction_sheet(html, base_url=fraction_sheet_url(code))

    return get_sheet


def test_dataset_compare_hs6_mx8_and_nico_against_matching_vucem(consumer_duckdb: Path):
    dataset = Dataset.open(consumer_duckdb)
    html = _vucem_html("01012101", "Reproductores de raza pura", "10", "Ex.")
    rows = dataset.compare("010121", get_sheet=_sheet_from_html(html))
    by_key = {(row.code, row.field): row for row in rows}

    assert {row.code for row in rows} == {"010121", "01012101", "0101210100"}
    assert by_key[("010121", "description")].match is None
    assert by_key[("01012101", "igi")].dataset == "10"
    assert by_key[("01012101", "igi")].other == "10"
    assert by_key[("01012101", "igi")].match is True
    assert by_key[("01012101", "ige")].match is True
    assert by_key[("0101210100", "igi")].match is True
    assert all(row.other_source == "vucem" for row in rows if row.code != "010121")


def test_dataset_compare_reports_igi_mismatch(consumer_duckdb: Path):
    dataset = Dataset.open(consumer_duckdb)
    html = _vucem_html("01012101", "Reproductores de raza pura", "5", "Ex.")
    rows = dataset.compare("01012101", get_sheet=_sheet_from_html(html))
    igi = next(row for row in rows if row.code == "01012101" and row.field == "igi")

    assert igi.dataset == "10"
    assert igi.other == "5"
    assert igi.match is False
