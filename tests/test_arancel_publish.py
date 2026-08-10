from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from comex import main
from src.comex.arancel_publish import prepare_github_release


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(root: Path) -> tuple[Path, Path, Path]:
    release = root / "release"
    sources = root / "sources"
    latest = root / "latest"
    release.mkdir()
    sources.mkdir()

    for name, content in {
        "arancel_mx.csv": b"record_id,code\r\n1,01\r\n",
        "arancel_mx.json": b'[{"record_id":"1","code":"01"}]\n',
        "arancel_mx.duckdb": b"duckdb fixture",
    }.items():
        (release / name).write_bytes(content)
    manifest = {
        "dataset_version": "2026.08.09",
        "validation_status": "passed",
        "row_count": 1,
        "artifact_sha256": {
            name: _sha256(release / name)
            for name in ("arancel_mx.csv", "arancel_mx.json", "arancel_mx.duckdb")
        },
    }
    (release / "manifest.json").write_text(
        json.dumps(manifest) + "\n", encoding="utf-8"
    )
    checksummed = [
        release / "arancel_mx.csv",
        release / "arancel_mx.json",
        release / "arancel_mx.duckdb",
        release / "manifest.json",
    ]
    (release / "SHA256SUMS").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in checksummed),
        encoding="ascii",
    )

    captured = []
    for kind, name, content in (
        ("ligie", "ligie.xlsx", b"ligie"),
        ("nico", "nico.xlsx", b"nico"),
    ):
        path = sources / name
        path.write_bytes(content)
        captured.append({"kind": kind, "filename": name, "sha256": _sha256(path)})
    (sources / "source_capture.json").write_text(
        json.dumps(captured) + "\n", encoding="utf-8"
    )
    return release, sources, latest


class ArancelPublishTests(unittest.TestCase):
    def test_prepares_verified_source_archive_and_lightweight_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            release, sources, latest = _fixture(Path(tmp))

            summary = prepare_github_release(release, sources, latest)

            self.assertEqual(summary["validation_status"], "passed")
            archive_path = release / "official-sources.tar.gz"
            self.assertTrue(archive_path.is_file())
            with tarfile.open(archive_path, "r:gz") as archive:
                self.assertEqual(set(archive.getnames()), {
                    "official-sources/ligie.xlsx",
                    "official-sources/nico.xlsx",
                    "official-sources/source_capture.json",
                })
            self.assertIn(
                "official-sources.tar.gz",
                (release / "SHA256SUMS").read_text(encoding="ascii"),
            )
            self.assertEqual(
                {path.name for path in latest.iterdir()},
                {"manifest.json", "SHA256SUMS", "README.md"},
            )
            self.assertEqual(
                (latest / "manifest.json").read_bytes(),
                (release / "manifest.json").read_bytes(),
            )

    def test_rejects_corrupt_release_before_writing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            release, sources, latest = _fixture(Path(tmp))
            (release / "arancel_mx.csv").write_bytes(b"corrupt")

            with self.assertRaisesRegex(ValueError, "checksum"):
                prepare_github_release(release, sources, latest)

            self.assertFalse((release / "official-sources.tar.gz").exists())
            self.assertFalse(latest.exists())

    def test_rejects_corrupt_source_before_writing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            release, sources, latest = _fixture(Path(tmp))
            (sources / "nico.xlsx").write_bytes(b"corrupt")

            with self.assertRaisesRegex(ValueError, "source checksum"):
                prepare_github_release(release, sources, latest)

            self.assertFalse((release / "official-sources.tar.gz").exists())
            self.assertFalse(latest.exists())

    def test_cli_packages_release(self):
        expected = {"dataset_version": "2026.08.09", "validation_status": "passed"}
        with patch("comex.prepare_github_release", return_value=expected) as package:
            with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = main([
                    "arancel-package-release",
                    "--release-dir", "release",
                    "--source-dir", "sources",
                    "--latest-dir", "latest",
                ])

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        package.assert_called_once_with(Path("release"), Path("sources"), Path("latest"))


if __name__ == "__main__":
    unittest.main()
