from arancel_mx.storage.duckdb import connect, init_tariff_db


def test_tariff_database_excludes_dashboard_tables(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")

    with connect(path, read_only=True) as connection:
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}

    assert {"source_document", "tariff_fraction", "nico", "tariff_rate"} <= tables
    assert not {"dashboard_monthly", "country", "customs_revenue"} & tables
