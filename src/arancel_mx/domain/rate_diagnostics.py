"""Read-only summaries of published rate-validity fields.

The pipeline decides whether a fraction is dated. This module only counts
what the public view already stores.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping


def summarize_rate_validity(
    rows: Iterable[Mapping[str, object]],
    *,
    dataset_version: str | None = None,
) -> dict[str, object]:
    """Count current fractions by whether ``rate_effective_from`` is present.

    Each row needs ``code``, ``rate_effective_from``, and ``validity_basis``.
    """

    seen: set[str] = set()
    dated = 0
    undated = 0
    bases: Counter[str] = Counter()
    for row in rows:
        code = str(row["code"])
        if code in seen:
            continue
        seen.add(code)
        basis = str(row.get("validity_basis") or "unknown")
        bases[basis] += 1
        if row.get("rate_effective_from") is None:
            undated += 1
        else:
            dated += 1
    return {
        "dataset_version": dataset_version,
        "level": "fraccion8",
        "counts": {
            "fraccion8": dated + undated,
            "dated": dated,
            "undated": undated,
        },
        "validity_basis": dict(sorted(bases.items())),
        "note": (
            "Undated fractions are those the pipeline refused to date "
            "(snapshot disagreement, unmodeled instrument, or no instrument row). "
            "This summary does not invent dates."
        ),
    }
