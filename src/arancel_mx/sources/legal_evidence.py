"""Required DOF evidence derived exclusively from the trusted Diputados ledger."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from arancel_mx.sources.diputados import LedgerLink, LedgerSnapshot


@dataclass(frozen=True)
class RequiredDofEvidence:
    role: str
    published_at: date
    url: str
    media_type: str


_REQUIRED_ROLES = (
    ("law_reform", "last_law_reform"),
    ("tariff_decree", "latest_tariff_modification"),
)


def _eligible_link(link: LedgerLink, published_at: date) -> bool:
    return (
        link.role == "dof"
        and bool(link.url.strip())
        and link.displayed_date == published_at
    )


def required_dof_evidence(
    ledger: LedgerSnapshot,
) -> tuple[RequiredDofEvidence, ...]:
    """Return the unique DOF evidence required for the current legal dates.

    URLs are never guessed. Evidence must already be present as a DOF link on the
    matching latest row in the parsed Cámara de Diputados ledger.
    """
    evidence: list[RequiredDofEvidence] = []
    for role, date_attribute in _REQUIRED_ROLES:
        published_at = getattr(ledger, date_attribute)
        links = [
            link
            for document in ledger.documents
            if document.category == role and document.displayed_date == published_at
            for link in document.links
            if _eligible_link(link, published_at)
        ]
        by_url: dict[str, list[LedgerLink]] = {}
        for link in links:
            by_url.setdefault(link.url, []).append(link)
        if not by_url:
            raise ValueError(f"missing DOF evidence: {role}")
        if len(by_url) != 1:
            raise ValueError(f"ambiguous DOF evidence: {role}")

        url, matching = next(iter(by_url.items()))
        declared_types = {
            link.media_type for link in matching if link.media_type and link.media_type.strip()
        }
        if len(declared_types) > 1:
            raise ValueError(f"ambiguous DOF media type: {role}")
        media_type = next(iter(declared_types), "application/octet-stream")
        evidence.append(
            RequiredDofEvidence(
                role=role,
                published_at=published_at,
                url=url,
                media_type=media_type,
            )
        )
    return tuple(evidence)
