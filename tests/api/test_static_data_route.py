from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from arancel_mx.api.app import create_app
from arancel_mx.consumer.dataset import Dataset
from tests.consumer.conftest import create_consumer_duckdb


def test_static_data_tree_is_served_from_the_loaded_release(
    valid_settings, tmp_path: Path
) -> None:
    path = create_consumer_duckdb(tmp_path / "fixture.duckdb")
    app = create_app(
        settings=valid_settings, dataset_loader=lambda settings: Dataset.open(path)
    )

    with TestClient(app) as client:
        meta = client.get("/data/v1/meta.json")
        assert meta.status_code == 200
        assert meta.json()["dataset_tag"] == valid_settings.dataset_tag
        records = client.get("/data/v1/records/01.json").json()
        assert [record["code"] for record in records] == [
            "01",
            "0101",
            "010121",
            "01012101",
            "0101210100",
        ]
        assert client.get("/data/v1/manifest.json").json()["record_count"] == 5
        assert client.get("/data/v1/records/99.json").status_code == 404
        assert client.get("/data/v1/../../etc/passwd").status_code == 404


def test_static_data_is_unavailable_without_a_dataset(valid_settings) -> None:
    def failing_loader(settings):
        from arancel_mx.consumer.errors import DatasetUnavailableError

        raise DatasetUnavailableError("offline")

    app = create_app(settings=valid_settings, dataset_loader=failing_loader)
    with TestClient(app) as client:
        assert client.get("/data/v1/meta.json").status_code == 503
