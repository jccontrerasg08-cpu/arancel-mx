from __future__ import annotations

from dataclasses import dataclass

import pytest

from arancel_mx.api.config import ApiSettings
from arancel_mx.consumer.models import DatasetInfo


@dataclass
class FakeDataset:
    info: DatasetInfo


@pytest.fixture
def valid_settings() -> ApiSettings:
    return ApiSettings(
        dataset_tag="data-2026.08.15",
        cache_dir=None,
        timeout=30.0,
        offline=False,
    )


@pytest.fixture
def fake_dataset() -> FakeDataset:
    return FakeDataset(
        info=DatasetInfo(
            dataset_version="2026.08.15",
            schema_version="2",
            path="/verified/arancel_mx.duckdb",
            source="managed-cache",
            structural_valid=True,
            release_verified=True,
            github_digest_state="verified",
        )
    )
