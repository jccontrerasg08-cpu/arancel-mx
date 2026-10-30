from pathlib import Path

from arancel_mx.parsers.decrees import DecreeRow, parse_decree_rows

DECREES = Path(__file__).resolve().parents[1] / "fixtures" / "pdf" / "decrees"


def test_reads_a_single_row_decree_with_its_full_description() -> None:
    rows = parse_decree_rows(DECREES / "LIGIE_2022_tarifa16_13oct26.pdf")

    assert rows == [
        DecreeRow(
            code="98030001",
            description=(
                "Partes y componentes para el ensamble de automóviles cuando se trate de "
                "empresas de la industria automotriz terminal que cuenten con autorización "
                "de depósito fiscal para ensamble y fabricación de vehículos conforme a la "
                "Ley Aduanera, siempre que se ajusten a los lineamientos que establezca la "
                "Secretaría de Economía."
            ),
            unit="Kg",
            igi="Ex.",
            ige="Ex.",
        )
    ]


def test_skips_empty_spacer_columns_between_duties() -> None:
    rows = parse_decree_rows(DECREES / "LIGIE_2022_tarifa13_10nov25.pdf")

    assert len(rows) == 8  # the decree modifies eight sugar fractions
    assert rows[0] == DecreeRow("17011205", "De remolacha.", "Kg", "156", "Ex.")
    assert {row.ige for row in rows} == {"Ex."}


def test_drops_the_hierarchy_dash_column_and_keeps_prohibitions() -> None:
    rows = {
        row.code: row
        for row in parse_decree_rows(DECREES / "LIGIE_2022_ref01_21jul25.pdf")
    }

    assert len(rows) == 11  # the reform lists eleven fractions
    assert rows["03048902"].description == "Totoabas de manejo intensivo"
    assert (rows["03048902"].igi, rows["03048902"].ige) == (
        "15",
        "Ex",
    )  # literal in the DOF text
    assert (rows["03028901"].igi, rows["03028901"].ige) == ("15", "Prohibida")
    assert rows["03019901"].ige == "Prohibida"
