"""Build a tiny deterministic release-shaped fixture for consumer CLI E2E tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import MappingProxyType

from arancel_mx.consumer.release_api import DataRelease, ReleaseAsset
from tests.consumer.conftest import create_consumer_duckdb


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def create_consumer_release_fixture(
    root: Path,
    *,
    tag: str = "data-2026.08.11",
    release_id: int = 368540643,
) -> tuple[DataRelease, dict[str, bytes]]:
    """Create one internally consistent six-asset release fixture in memory."""

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    version = tag.removeprefix("data-")
    database = create_consumer_duckdb(
        root / "arancel_mx.duckdb",
        dataset_version=version,
        schema_version="2",
    )
    files: dict[str, bytes] = {
        "arancel_mx.duckdb": database.read_bytes(),
        "arancel_mx.csv": b"code,description\n01012101,fixture\n",
        "arancel_mx.json": b'[{"code":"01012101","description":"fixture"}]\n',
        "manifest.json": json.dumps(
            {
                "dataset_version": version,
                "schema_version": "2",
                "validation_status": "passed",
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
        "official-sources.tar.gz": b"deterministic-fixture-source-archive",
    }
    checksum_order = (
        "arancel_mx.duckdb",
        "arancel_mx.csv",
        "arancel_mx.json",
        "manifest.json",
        "official-sources.tar.gz",
    )
    files["SHA256SUMS"] = "".join(
        f"{_sha256(files[name])}  {name}\n" for name in checksum_order
    ).encode("ascii")

    assets = {
        name: ReleaseAsset(
            asset_id=release_id * 10 + index,
            name=name,
            url=(
                "https://github.com/jccontrerasg08-cpu/arancel-mx/"
                f"releases/download/{tag}/{name}"
            ),
            size=len(body),
            api_sha256=_sha256(body),
        )
        for index, (name, body) in enumerate(sorted(files.items()), start=1)
    }
    release = DataRelease(
        tag=tag,
        release_id=release_id,
        assets_by_name=MappingProxyType(assets),
    )
    return release, files
