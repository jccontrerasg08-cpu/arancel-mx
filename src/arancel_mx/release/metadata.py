"""Release provenance and source identity helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import hashlib
import json
import re
from collections.abc import Mapping, Sequence


_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _validate_nonblank_dataclass(value: object) -> None:
    for field in fields(value):
        item = getattr(value, field.name)
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field.name} must be a non-blank string")


@dataclass(frozen=True)
class ReleaseProvenance:
    git_commit_sha: str
    github_run_id: str
    github_run_attempt: str
    github_workflow_ref: str
    github_artifact_name: str

    def __post_init__(self) -> None:
        _validate_nonblank_dataclass(self)

    @classmethod
    def local(cls) -> "ReleaseProvenance":
        return cls(
            git_commit_sha="local",
            github_run_id="local",
            github_run_attempt="local",
            github_workflow_ref="local",
            github_artifact_name="local",
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class SourceIdentity:
    dataset_key: str
    document_role: str
    source_url: str
    sha256: str
    registry_version: str

    def __post_init__(self) -> None:
        _validate_nonblank_dataclass(self)
        if not _SHA256.fullmatch(self.sha256):
            raise ValueError("sha256 must be a 64-character hexadecimal SHA-256")
        object.__setattr__(self, "sha256", self.sha256.lower())

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _ordered_identity_dicts(items: Sequence[SourceIdentity]) -> list[dict[str, str]]:
    return [
        item.to_dict()
        for item in sorted(
            items,
            key=lambda value: (
                value.dataset_key,
                value.document_role,
                value.source_url,
                value.sha256,
                value.registry_version,
            ),
        )
    ]


def source_identity_digest(items: Sequence[SourceIdentity]) -> str:
    payload = json.dumps(
        _ordered_identity_dicts(items),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def source_identity_from_manifest(
    manifest: Mapping[str, object],
) -> tuple[SourceIdentity, ...]:
    raw = manifest.get("source_identity")
    if not isinstance(raw, list) or not raw:
        raise ValueError("manifest.source_identity must be a non-empty list")

    identities: list[SourceIdentity] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"manifest.source_identity[{index}] must be an object")
        try:
            identities.append(
                SourceIdentity(
                    dataset_key=str(item["dataset_key"]),
                    document_role=str(item["document_role"]),
                    source_url=str(item["source_url"]),
                    sha256=str(item["sha256"]),
                    registry_version=str(item["registry_version"]),
                )
            )
        except KeyError as exc:
            raise ValueError(
                f"manifest.source_identity[{index}] missing {exc.args[0]}"
            ) from exc
    return tuple(identities)


def source_identity_history(
    current: Sequence[SourceIdentity],
    previous_manifest: Mapping[str, object] | None,
) -> dict[str, object]:
    """Describe the current source diff against one prior certified release."""
    if previous_manifest is None:
        return {"previous_dataset_version": None, "changes": []}
    previous_version = previous_manifest.get("dataset_version")
    if not isinstance(previous_version, str) or not previous_version.strip():
        raise ValueError("previous manifest dataset_version must be a non-blank string")
    previous = source_identity_from_manifest(previous_manifest)
    return {
        "previous_dataset_version": previous_version,
        "changes": source_identity_changes(current, previous),
    }


def source_identity_changed(
    current: Sequence[SourceIdentity],
    previous: Sequence[SourceIdentity],
) -> bool:
    return source_identity_digest(current) != source_identity_digest(previous)


def source_identity_changes(
    current: Sequence[SourceIdentity],
    previous: Sequence[SourceIdentity],
) -> list[dict[str, object]]:
    """Return deterministic, inspectable changes keyed by dataset and document role."""
    current_by_key = {(item.dataset_key, item.document_role): item for item in current}
    previous_by_key = {(item.dataset_key, item.document_role): item for item in previous}
    changes: list[dict[str, object]] = []
    for dataset_key, document_role in sorted(set(current_by_key) | set(previous_by_key)):
        before = previous_by_key.get((dataset_key, document_role))
        after = current_by_key.get((dataset_key, document_role))
        if before == after:
            continue
        changes.append(
            {
                "change": "added" if before is None else "removed" if after is None else "updated",
                "dataset_key": dataset_key,
                "document_role": document_role,
                "previous": before.to_dict() if before is not None else None,
                "current": after.to_dict() if after is not None else None,
            }
        )
    return changes
