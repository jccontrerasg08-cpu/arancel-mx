from __future__ import annotations

from pathlib import Path


def test_download_latest_publication_bundle_requires_the_exact_public_release_assets(tmp_path):
    from arancel_mx.operational.sync import download_latest_publication_bundle
    from arancel_mx.release.package import PUBLIC_RELEASE_ASSETS

    calls: list[str] = []

    class Response:
        def __init__(self, *, payload=None, content=b""):
            self.payload = payload
            self.content = content

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    release_url = "https://api.github.com/repos/jccontrerasg08-cpu/arancel-mx/releases/latest"
    assets = [
        {"name": name, "browser_download_url": f"https://downloads.example/{name}"}
        for name in PUBLIC_RELEASE_ASSETS
    ]

    def fetch(url, *, timeout, headers):
        calls.append(url)
        if url == release_url:
            return Response(payload={"tag_name": "data-2026.08.18", "published_at": "2026-08-18T12:00:00Z", "assets": assets})
        return Response(content=f"contents:{Path(url).name}".encode())

    bundle, published_at = download_latest_publication_bundle(
        tmp_path,
        release_url=release_url,
        fetch=fetch,
    )

    assert bundle == tmp_path / "data-2026.08.18"
    assert published_at.isoformat() == "2026-08-18T12:00:00+00:00"
    assert {path.name for path in bundle.iterdir()} == set(PUBLIC_RELEASE_ASSETS)
    assert calls == [release_url, *(asset["browser_download_url"] for asset in assets)]


def test_download_latest_publication_bundle_rejects_a_release_with_missing_assets(tmp_path):
    from arancel_mx.operational.sync import OperationalSyncError
    from arancel_mx.operational.sync import download_latest_publication_bundle

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "tag_name": "data-2026.08.18",
                "published_at": "2026-08-18T12:00:00Z",
                "assets": [],
            }

    def fetch(url, *, timeout, headers):
        return Response()

    try:
        download_latest_publication_bundle(
            tmp_path,
            release_url="https://api.github.com/repos/jccontrerasg08-cpu/arancel-mx/releases/latest",
            fetch=fetch,
        )
    except OperationalSyncError as error:
        assert "assets" in str(error)
    else:
        raise AssertionError("a partial release must never be promoted")


def test_sync_rehydrates_only_evidence_when_latest_tag_is_already_active(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    from arancel_mx.operational import OperationalRelease
    from arancel_mx.operational.sync import synchronize_latest_release

    release = OperationalRelease(
        tag="data-2026.08.17",
        dataset_version="2026.08.17",
        schema_version="2",
        manifest_sha256="a" * 64,
        generated_at=datetime(2026, 8, 17, 10, 0, tzinfo=timezone.utc),
        published_at=datetime(2026, 8, 17, 11, 0, tzinfo=timezone.utc),
        source_checked_at=datetime(2026, 8, 19, 19, 0, tzinfo=timezone.utc),
        evidence={"source_documents": [{"source_document_id": "dof-1"}], "record_provenance": [], "national_notes": []},
    )
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        "arancel_mx.operational.sync._latest_release",
        lambda **kwargs: ("data-2026.08.17", {"arancel_mx.duckdb": "https://example/duckdb", "manifest.json": "https://example/manifest", "SHA256SUMS": "https://example/sums"}, release.published_at),
    )
    monkeypatch.setattr("arancel_mx.operational.sync._active_release_state", lambda connection: ("data-2026.08.17", {}))
    monkeypatch.setattr(
        "arancel_mx.operational.sync._download_assets",
        lambda destination, downloads, names, **kwargs: observed.setdefault("asset_names", names) and tmp_path,
    )
    monkeypatch.setattr("arancel_mx.operational.sync._certified_evidence_release", lambda *args, **kwargs: release)
    monkeypatch.setattr(
        "arancel_mx.operational.sync.promote_release",
        lambda connection, promoted, records: observed.update({"release": promoted, "records": list(records)}),
    )

    result = synchronize_latest_release(object(), checked_at=release.source_checked_at)

    assert result == {"release_tag": "data-2026.08.17", "record_count": 0, "changed": True}
    assert observed["asset_names"] == ("arancel_mx.duckdb", "manifest.json", "SHA256SUMS")
    assert observed["release"] == release
    assert observed["records"] == []


def test_sync_skips_download_when_active_release_already_has_evidence(monkeypatch):
    from datetime import datetime, timezone

    from arancel_mx.operational.sync import synchronize_latest_release

    checked_at = datetime(2026, 8, 19, 19, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "arancel_mx.operational.sync._latest_release",
        lambda **kwargs: ("data-2026.08.17", {}, checked_at),
    )
    monkeypatch.setattr(
        "arancel_mx.operational.sync._active_release_state",
        lambda connection: ("data-2026.08.17", {"source_documents": [{"source_document_id": "dof-1"}]}),
    )
    monkeypatch.setattr(
        "arancel_mx.operational.sync._download_assets",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not download")),
    )

    assert synchronize_latest_release(object(), checked_at=checked_at) == {
        "release_tag": "data-2026.08.17",
        "record_count": 0,
        "changed": False,
    }
