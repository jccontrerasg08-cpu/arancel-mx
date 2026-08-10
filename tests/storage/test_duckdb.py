from arancel_mx.storage.duckdb import connect, init_tariff_db


def test_tariff_database_excludes_dashboard_tables(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")

    with connect(path, read_only=True) as connection:
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}

    assert {"source_document", "tariff_fraction", "nico", "tariff_rate"} <= tables
    assert not {"dashboard_monthly", "country", "customs_revenue"} & tables


def test_dataset_release_requires_release_metadata_json(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")

    with connect(path, read_only=True) as connection:
        columns = {
            row[0]: row
            for row in connection.execute("DESCRIBE dataset_release").fetchall()
        }

    assert "release_metadata_json" in columns
    assert columns["release_metadata_json"][2] == "NO"
