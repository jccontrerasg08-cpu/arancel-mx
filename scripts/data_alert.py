"""Deterministic formatting and lifecycle helpers for official-data alerts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib


MAX_ALERT_MESSAGE = 800
ALERT_MARKER_PREFIX = "<!-- arancel-mx-data-alert-key:"


def _clean(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-blank string")
    return value.strip()


def _sanitize_message(value: str) -> str:
    text = " ".join(str(value).replace("\x00", " ").split())
    text = text.replace("<!--", "< !--").replace("-->", "-- >")
    if len(text) > MAX_ALERT_MESSAGE:
        text = text[: MAX_ALERT_MESSAGE - 3] + "..."
    return text or "failure reported without diagnostic text"


@dataclass(frozen=True)
class DataAlert:
    stage: str
    failure_category: str
    dataset_version: str
    message: str
    run_id: str
    run_attempt: str
    commit_sha: str
    run_url: str

    def __post_init__(self) -> None:
        for field in (
            "stage",
            "failure_category",
            "dataset_version",
            "run_id",
            "run_attempt",
            "commit_sha",
            "run_url",
        ):
            object.__setattr__(self, field, _clean(getattr(self, field), field))
        object.__setattr__(self, "message", _sanitize_message(self.message))

    @property
    def key(self) -> str:
        payload = f"{self.stage}\x00{self.failure_category}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @property
    def title(self) -> str:
        return f"[DATA ALERT] {self.stage}: {self.failure_category}"

    @property
    def marker(self) -> str:
        return f"{ALERT_MARKER_PREFIX}{self.key} -->"

    def body(self) -> str:
        return "\n".join(
            [
                self.marker,
                "# Official data pipeline blocked",
                "",
                "Publication state: **BLOCKED**",
                f"Dataset candidate: `{self.dataset_version}`",
                f"Stage: `{self.stage}`",
                f"Failure category: `{self.failure_category}`",
                "",
                "## Diagnostic",
                self.message,
                "",
                "## Run provenance",
                f"- Run: {self.run_url}",
                f"- Run ID: `{self.run_id}`",
                f"- Attempt: `{self.run_attempt}`",
                f"- Commit: `{self.commit_sha}`",
                "",
                "The release remains blocked until a later successful production run recovers this alert.",
                "",
            ]
        )
