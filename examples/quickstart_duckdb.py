#!/usr/bin/env python3
"""Minimal example: load the latest verified arancel-mx dataset and query it.

Requires: pip install arancel-mx duckdb
"""

from arancel_mx import Dataset


def main() -> None:
    # Downloads and verifies the latest immutable data-YYYY.MM.DD release
    ds = Dataset.latest()
    print(f"Dataset: {ds.info.dataset_tag} (verified={ds.info.release_verified})")

    # Exact lookup
    record = ds.lookup("85171301")
    print(f"\n{record.code} — {record.description}")
    print(f"  IGI: {record.igi_text}  |  IGE: {record.ige_text}")
    print(f"  Level: {record.level}  |  Unit: {record.unit_name}")

    # Hierarchy
    print("\nParents:")
    parent = ds.parent(record.code)
    while parent:
        print(f"  {parent.level}: {parent.code} — {parent.description[:60]}...")
        parent = ds.parent(parent.code)

    # Search
    print("\nSearch for 'teléfono':")
    for hit in ds.search("teléfono", limit=3):
        print(f"  {hit.record.code}  {hit.record.description[:50]}")

    # NICO coverage diagnostic (new in 0.3.8+)
    print("\n--- NICO coverage ---")
    # Note: after the CLI lands, users can also run:
    #   arancel-mx data nico-coverage --format json
    print("Use the CLI: arancel-mx data nico-coverage")


if __name__ == "__main__":
    main()
