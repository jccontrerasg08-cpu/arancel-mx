from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Mapping


@dataclass(frozen=True)
class CaptureManifest:
    path: Path
    manifest_path: Path
    sha256: str
    metadata: Mapping[str, Any]


def _safe_segment(value: object) -> str:
    segment = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-._")
    if not segment:
        raise ValueError("capture metadata contains an empty path segment")
    return segment


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def capture_document(
    content: bytes, metadata: Mapping[str, Any], raw_root: Path
) -> CaptureManifest:
    required = ("source_id", "kind", "observed_at", "source_url", "filename")
    missing = [key for key in required if not metadata.get(key)]
    if missing:
        raise ValueError(f"missing capture metadata: {', '.join(missing)}")
    digest = hashlib.sha256(content).hexdigest()
    directory = (
        Path(raw_root)
        / _safe_segment(metadata["observed_at"])
        / _safe_segment(metadata["source_id"])
        / _safe_segment(metadata["kind"])
    )
    directory.mkdir(parents=True, exist_ok=True)
    filename = _safe_segment(metadata["filename"])
    target = directory / filename
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            candidate = target.with_name(f"{target.stem}-{digest[:8]}{target.suffix}")
            if candidate.exists() and hashlib.sha256(candidate.read_bytes()).hexdigest() != digest:
                raise ValueError(f"capture hash collision: {candidate}")
            target = candidate
    if not target.exists():
        target.write_bytes(content)
    manifest_path = target.with_suffix(target.suffix + ".manifest.json")
    payload = dict(metadata)
    payload.update({"path": target.relative_to(raw_root).as_posix(), "sha256": digest, "size": len(content)})
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        comparable_existing = {
            key: value for key, value in existing.items() if key != "retrieved_at"
        }
        comparable_payload = {
            key: value for key, value in payload.items() if key != "retrieved_at"
        }
        if comparable_existing != comparable_payload:
            raise ValueError(f"capture manifest conflict: {manifest_path}")
        payload = existing
    else:
        _atomic_json(manifest_path, payload)
    return CaptureManifest(target, manifest_path, digest, payload)


def can_reuse_parse(
    previous: Mapping[str, Any] | None,
    source_sha256: str,
    parser_version: str,
    schema_version: str,
    registry_version: str,
) -> bool:
    if previous is None:
        return False
    identity = {
        "source_sha256": source_sha256,
        "parser_version": parser_version,
        "schema_version": schema_version,
        "registry_version": registry_version,
    }
    return all(str(previous.get(key)) == str(value) for key, value in identity.items())
