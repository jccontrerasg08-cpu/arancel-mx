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
