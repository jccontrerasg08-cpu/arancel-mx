"""JSON manifest for idempotent public-source downloads."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .paths import MANIFEST_PATH, ensure_data_dirs


@dataclass
class Artifact:
    source_name: str
    source_url: str
    local_path: str
    sha256: str
    size_bytes: int
    fetched_at: str
    extra: dict | None = None


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class Manifest:
    def __init__(self, path: Path = MANIFEST_PATH) -> None:
        ensure_data_dirs()
        self.path = path
        self.artifacts: list[Artifact] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self.artifacts = []
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.artifacts = [Artifact(**item) for item in raw.get("artifacts", [])]
        except (OSError, json.JSONDecodeError, TypeError):
            self.artifacts = []

    def save(self) -> None:
        self.path.write_text(
            json.dumps({"artifacts": [asdict(a) for a in self.artifacts]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def upsert(self, artifact: Artifact) -> bool:
        key = (artifact.source_name, artifact.local_path)
        for idx, existing in enumerate(self.artifacts):
            if (existing.source_name, existing.local_path) == key:
                if existing.sha256 == artifact.sha256:
                    return False
                self.artifacts[idx] = artifact
                self.save()
                return True
        self.artifacts.append(artifact)
        self.save()
        return True

    def summary(self) -> dict:
        by_source: dict[str, int] = {}
        latest = ""
        for artifact in self.artifacts:
            by_source[artifact.source_name] = by_source.get(artifact.source_name, 0) + 1
            latest = max(latest, artifact.fetched_at)
        return {
            "path": str(self.path),
            "exists": self.path.exists(),
            "total": len(self.artifacts),
            "by_source": by_source,
            "latest": latest,
        }


def new_artifact(source: str, url: str, path: Path, content: bytes, extra: dict | None = None) -> Artifact:
    return Artifact(
        source_name=source,
        source_url=url,
        local_path=str(path),
        sha256=sha256_bytes(content),
        size_bytes=len(content),
        fetched_at=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        extra=extra,
    )
