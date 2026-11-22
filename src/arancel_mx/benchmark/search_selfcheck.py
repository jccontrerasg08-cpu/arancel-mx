"""Self-check benchmark of the current lexical search, using the release itself as ground truth.

Each probe asks the search for something whose correct answer is known without human labelling: a record's
own code (plain and dotted) and a record's own published description. It measures whether search finds a known
record. It does not measure classification of goods: finding a fraction by its own description says nothing about
which fraction an actual product belongs to.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from statistics import median, quantiles
from time import perf_counter

from arancel_mx.consumer.models import SearchResult

SELFCHECK_VERSION = "search-selfcheck-v1"
SCOPE_NOTE = (
    "Retrieval of known records only. This is not a classification benchmark and its rates are not a "
    "probability that a suggested code is correct for a product."
)

Search = Callable[[str, int], Sequence[SearchResult]]


@dataclass(frozen=True, slots=True)
class SelfcheckRecord:
    code: str
    formatted_code: str
    description: str


def sample_records(records: Sequence[SelfcheckRecord], size: int) -> tuple[SelfcheckRecord, ...]:
    """Deterministic, evenly spaced sample over records ordered by code (no randomness, reproducible)."""

    if size <= 0:
        raise ValueError("sample size must be greater than zero")
    ordered = sorted(records, key=lambda record: record.code)
    if size >= len(ordered):
        return tuple(ordered)
    step = len(ordered) / size
    return tuple(ordered[int(index * step)] for index in range(size))


def _same_item(result: SearchResult, record: SelfcheckRecord) -> bool:
    """The record itself, or the same item at another level of its own line (e.g. its NICO or subheading
    carrying exactly the same published description)."""

    code = result.record.code
    if code == record.code:
        return True
    related = code.startswith(record.code) or record.code.startswith(code)
    return related and result.record.description == record.description


def _rank(results: Sequence[SearchResult], record: SelfcheckRecord, *, exact: bool) -> int | None:
    for position, result in enumerate(results, start=1):
        if result.record.code == record.code if exact else _same_item(result, record):
            return position
    return None


def run_selfcheck(
    records: Sequence[SelfcheckRecord],
    search: Search,
    *,
    sample: int = 200,
    depth: int = 10,
    description_counts: Counter[str] | None = None,
    dataset_version: str | None = None,
    scorer_version: str | None = None,
    max_failures: int = 25,
    clock: Callable[[], float] = perf_counter,
) -> dict[str, object]:
    """Run the three probes over a deterministic sample and return a report.

    ``description_counts`` counts the sampled population per description; a description shared by several
    records of that population (for example «Los demás.») cannot identify one record, so those probes are reported
    as non-distinctive and left out of the description rates instead of being counted as failures. A hit on the
    same item at another level of its own line (its NICO or subheading with the identical description) counts.
    """

    if depth <= 0:
        raise ValueError("depth must be greater than zero")
    timings: list[float] = []

    def timed(query: str, limit: int) -> Sequence[SearchResult]:
        start = clock()
        results = search(query, limit)
        timings.append((clock() - start) * 1000)
        return results

    chosen = sample_records(records, sample)
    counts = description_counts if description_counts is not None else Counter(r.description for r in records)
    code_hits = dotted_hits = 0
    description_ranks: list[int | None] = []
    non_distinctive = 0
    failures: list[dict[str, object]] = []
    for record in chosen:
        for probe, query in (("exact_code", record.code), ("dotted_code", record.formatted_code)):
            rank = _rank(timed(query, 1), record, exact=True)
            if rank == 1:
                if probe == "exact_code":
                    code_hits += 1
                else:
                    dotted_hits += 1
            elif len(failures) < max_failures:
                failures.append({"probe": probe, "code": record.code, "query": query, "rank": rank})
        if counts[record.description] > 1:
            non_distinctive += 1
            continue
        rank = _rank(timed(record.description, depth), record, exact=False)
        description_ranks.append(rank)
        if rank != 1 and len(failures) < max_failures:
            failures.append({"probe": "own_description", "code": record.code, "query": record.description, "rank": rank})
    evaluated = len(description_ranks)

    def rate(hits: int, total: int) -> float | None:
        return round(hits / total, 4) if total else None

    def found_within(k: int) -> int:
        return sum(1 for rank in description_ranks if rank is not None and rank <= k)

    return {
        "selfcheck_version": SELFCHECK_VERSION,
        "dataset_version": dataset_version,
        "scorer_version": scorer_version,
        "scope": SCOPE_NOTE,
        "sample": {"requested": sample, "records": len(chosen), "population": len(records), "depth": depth},
        "exact_code": {"top1": code_hits, "rate": rate(code_hits, len(chosen))},
        "dotted_code": {"top1": dotted_hits, "rate": rate(dotted_hits, len(chosen))},
        "own_description": {
            "evaluated": evaluated,
            "non_distinctive_skipped": non_distinctive,
            "top1": found_within(1),
            "top5": found_within(5),
            f"top{depth}": found_within(depth),
            "not_found": sum(1 for rank in description_ranks if rank is None),
            "top1_rate": rate(found_within(1), evaluated),
            "top5_rate": rate(found_within(5), evaluated),
        },
        "latency_ms": {
            "searches": len(timings),
            "p50": round(median(timings), 1) if timings else None,
            "p95": round(quantiles(timings, n=20)[-1], 1) if len(timings) >= 2 else None,
            "max": round(max(timings), 1) if timings else None,
            "note": "Wall time of each in-process search on this machine; compare only runs on the same machine.",
        },
        "failures": failures,
    }
