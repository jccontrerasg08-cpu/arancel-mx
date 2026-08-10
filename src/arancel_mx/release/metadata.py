"""Release provenance and source identity helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ReleaseProvenance:
    git_commit_sha: str
    github_run_id: str
    github_run_attempt: str
    github_workflow_ref: str
    github_artifact_name: str

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
