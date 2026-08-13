from pathlib import Path

from arancel_mx.consumer.dataset import Dataset

ROOT = Path(__file__).resolve().parents[2]


def test_consumer_fixture_fraction_01012101_keeps_official_igi_literals(
    consumer_duckdb: Path,
) -> None:
    dataset = Dataset.open(consumer_duckdb)
    fraction = dataset.lookup("01012101")
    assert fraction.level == "fraccion8"
    assert fraction.code == "01012101"
    assert fraction.igi_text == "10"
    assert fraction.ige_text == "Ex."

    nico = dataset.lookup("0101210100")
    assert nico.level == "nico10"
    assert nico.code == "0101210100"
    assert nico.igi_text == "10"
    assert tuple(child.code for child in dataset.children("01012101")) == ("0101210100",)


def test_external_consumption_documents_fixture_golden_literals() -> None:
    text = (ROOT / "docs/external-consumption.md").read_text(encoding="utf-8")
    assert "01012101" in text
    assert "0101210100" in text
    assert "`10`" in text or "igi_text` `10`" in text or 'igi_text` 10' in text
    assert "igi_text" in text
    assert "Ex." in text
