import pytest

from arancel_mx.pipeline.hierarchy import assemble_classifications


def row(level, code, description, ligie_version="LIGIE-2022"):
    return {
        "level": level,
        "code": code,
        "description": description,
        "ligie_version": ligie_version,
    }


def test_complete_hierarchy_is_kept_without_generated_descriptions():
    hs = [
        row("hs2", "01", "Animales vivos"),
        row("hs4", "0101", "Caballos"),
        row("hs6", "010121", "Reproductores"),
    ]
    fractions = [row("fraccion8", "01012101", "Reproductores de raza pura")]
    nicos = [row("nico10", "0101210100", "Reproductores")]

    result = assemble_classifications(hs, fractions, nicos)

    assert [item["code"] for item in result] == [
        "01",
        "0101",
        "010121",
        "01012101",
        "0101210100",
    ]
    assert result[0]["description"] == "Animales vivos"
    assert result[2]["description"] == "Reproductores"


def test_fraction_without_hs6_parent_fails():
    with pytest.raises(ValueError, match="missing HS6 parent"):
        assemble_classifications([], [row("fraccion8", "01012101", "x")], [])


def test_hs6_without_hs4_parent_fails():
    hs = [row("hs2", "01", "Animales vivos"), row("hs6", "010121", "x")]

    with pytest.raises(ValueError, match="missing HS4 parent"):
        assemble_classifications(hs, [], [])


def test_hs4_without_hs2_parent_fails():
    with pytest.raises(ValueError, match="missing HS2 parent"):
        assemble_classifications([row("hs4", "0101", "x")], [], [])


def test_nico_without_fraction_parent_fails():
    with pytest.raises(ValueError, match="missing fraction parent"):
        assemble_classifications([], [], [row("nico10", "0101210100", "x")])


def test_current_fraction_without_nico_child_fails_closed():
    hs = [
        row("hs2", "24", "Tabaco"),
        row("hs4", "2404", "Productos con nicotina"),
        row("hs6", "240411", "Que contengan tabaco"),
    ]
    fractions = [row("fraccion8", "24041101", "Que contengan tabaco o tabaco reconstituido")]

    with pytest.raises(ValueError, match="current tariff fractions missing NICO coverage.*24041101"):
        assemble_classifications(hs, fractions, [])


def test_conflicting_duplicate_classification_fails_closed():
    hs = [
        row("hs2", "01", "Animales vivos"),
        row("hs2", "01", "Descripción incompatible"),
    ]

    with pytest.raises(ValueError, match="conflicting duplicate classification"):
        assemble_classifications(hs, [], [])


def test_identical_duplicates_are_collapsed_deterministically():
    hs2 = row("hs2", "01", "Animales vivos")

    result = assemble_classifications([hs2, dict(hs2)], [], [])

    assert result == [hs2]
