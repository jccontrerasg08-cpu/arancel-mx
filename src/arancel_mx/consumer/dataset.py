"""Small public facade for verified Mexican tariff datasets."""

from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

from arancel_mx.consumer.config import resolve_config
from arancel_mx.consumer.integrity import validate_duckdb
from arancel_mx.consumer.manager import DatasetManager
from arancel_mx.consumer.models import DatasetInfo, ProvenanceRecord, SearchResult, TariffRecord
from arancel_mx.consumer import query
from arancel_mx.storage.duckdb import connect as duckdb_connect


class Dataset:
    """Read-only access to one structurally validated tariff dataset."""

    def __init__(self, path: Path, info: DatasetInfo) -> None:
        self._path = Path(path)
        self._info = info

    @staticmethod
    def _config(
        *,
        offline: bool | None,
        cache_dir: str | Path | None,
        timeout: float | None,
    ):
        # ``resolve_config`` uses a sentinel so omitted values can fall through to
        # environment/defaults. Do not pass None for bool/timeout because None is
        # not a valid explicit value at that lower boundary.
        kwargs: dict[str, object] = {}
        if offline is not None:
            kwargs["offline"] = offline
        if cache_dir is not None:
            kwargs["cache_dir"] = cache_dir
        if timeout is not None:
            kwargs["timeout"] = timeout
        return resolve_config(**kwargs)

    @classmethod
    def latest(
        cls,
        *,
        offline: bool | None = None,
        cache_dir: str | Path | None = None,
        timeout: float | None = None,
    ) -> "Dataset":
        config = cls._config(
            offline=offline,
            cache_dir=cache_dir,
            timeout=timeout,
        )
        manager = DatasetManager(config)
        path = manager.ensure()
        info = manager.verify()
        return cls(path, info)

    @classmethod
    def version(
        cls,
        tag: str,
        *,
        offline: bool | None = None,
        cache_dir: str | Path | None = None,
        timeout: float | None = None,
    ) -> "Dataset":
        config = cls._config(
            offline=offline,
            cache_dir=cache_dir,
            timeout=timeout,
        )
        manager = DatasetManager(config)
        path = manager.ensure(tag)
        info = manager.verify(tag)
        return cls(path, info)

    @classmethod
    def open(cls, path: str | Path) -> "Dataset":
        db_path = Path(path)
        info = validate_duckdb(
            db_path,
            manifest=None,
            expected_tag=None,
            release_verified=False,
            github_digest_state="not_applicable",
        )
        return cls(db_path, info)

    @property
    def info(self) -> DatasetInfo:
        return self._info

    def connect(self) -> AbstractContextManager[Any]:
        """Return an advanced read-only DuckDB connection context manager."""

        return duckdb_connect(self._path, read_only=True)

    def lookup(self, code: str) -> TariffRecord:
        with self.connect() as connection:
            return query.lookup(connection, code)

    def search(self, text: str, *, limit: int = 20) -> tuple[SearchResult, ...]:
        with self.connect() as connection:
            return query.search(connection, text, limit=limit)

    def parent(self, code: str) -> TariffRecord | None:
        with self.connect() as connection:
            return query.parent(connection, code)

    def children(self, code: str) -> tuple[TariffRecord, ...]:
        with self.connect() as connection:
            return query.children(connection, code)

    def provenance(self, code: str) -> tuple[ProvenanceRecord, ...]:
        with self.connect() as connection:
            return query.provenance(connection, code)
