from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

import arancel_mx
import arancel_mx.consumer.dataset as dataset_module
from arancel_mx.consumer.dataset import Dataset
from arancel_mx.consumer.models import DatasetInfo, SearchResult, TariffRecord


def test_root_package_exports_dataset() -> None:
    assert arancel_mx.Dataset is Dataset
    assert "Dataset" in arancel_mx.__all__


def test_dataset_open_validates_local_file_read_only(consumer_duckdb: Path) -> None:
    dataset = Dataset.open(consumer_duckdb)
    assert dataset.info.structural_valid is True
    assert dataset.info.path == str(consumer_duckdb)


def test_dataset_open_local_info_does_not_claim_release_verification(
    consumer_duckdb: Path,
) -> None:
    dataset = Dataset.open(consumer_duckdb)
    assert dataset.info.source == "local"
    assert dataset.info.release_verified is False
    assert dataset.info.github_digest_state == "not_applicable"


class _FakeManager:
    instances: list["_FakeManager"] = []

    def __init__(self, config, *, session=None) -> None:
        self.config = config
        self.session = session
        self.ensure_calls: list[str | None] = []
        self.path = Path(config.cache_dir) / "selected.duckdb"
        self._info = DatasetInfo(
            dataset_version="2026.08.11",
            schema_version="2",
            path=str(self.path),
            source="managed-cache",
            structural_valid=True,
            release_verified=True,
            github_digest_state="verified",
        )
        self.__class__.instances.append(self)

    def ensure(self, tag: str | None = None) -> Path:
        self.ensure_calls.append(tag)
        return self.path

    def verify(self, tag: str | None = None, *, online: bool = False, bundle: bool = False) -> DatasetInfo:
        return self._info


def test_dataset_version_uses_exact_tag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeManager.instances.clear()
    monkeypatch.setattr(dataset_module, "DatasetManager", _FakeManager)

    dataset = Dataset.version("data-2026.08.11", cache_dir=tmp_path, offline=False)

    manager = _FakeManager.instances[-1]
    assert manager.ensure_calls == ["data-2026.08.11"]
    assert dataset.info.release_verified is True


def test_dataset_latest_delegates_to_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeManager.instances.clear()
    monkeypatch.setattr(dataset_module, "DatasetManager", _FakeManager)

    Dataset.latest(cache_dir=tmp_path, timeout=7.5)

    manager = _FakeManager.instances[-1]
    assert manager.ensure_calls == [None]
    assert manager.config.cache_dir == tmp_path
    assert manager.config.timeout == 7.5


def test_dataset_lookup_returns_tariff_record(consumer_duckdb: Path) -> None:
    dataset = Dataset.open(consumer_duckdb)
    result = dataset.lookup("01012101")
    assert isinstance(result, TariffRecord)
    assert result.code == "01012101"


def test_dataset_search_returns_tuple_of_search_results(consumer_duckdb: Path) -> None:
    dataset = Dataset.open(consumer_duckdb)
    result = dataset.search("raza pura")
    assert isinstance(result, tuple)
    assert all(isinstance(item, SearchResult) for item in result)
    assert result[0].record.code == "010121"


def test_dataset_parent_children_and_provenance_delegate_to_query_layer(
    consumer_duckdb: Path,
) -> None:
    dataset = Dataset.open(consumer_duckdb)
    parent = dataset.parent("01012101")
    assert parent is not None and parent.code == "010121"
    assert tuple(item.code for item in dataset.children("010121")) == ("01012101",)
    provenance = dataset.provenance("01012101")
    assert provenance[0].source_document_id == "fixture-source"


def test_dataset_connect_context_manager_closes_connection(consumer_duckdb: Path) -> None:
    dataset = Dataset.open(consumer_duckdb)
    with dataset.connect() as connection:
        assert connection.execute("SELECT 1").fetchone()[0] == 1

    with pytest.raises(duckdb.Error):
        connection.execute("SELECT 1")
