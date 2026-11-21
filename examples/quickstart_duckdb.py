#!/usr/bin/env python3
"""Load the latest verified dataset and print a citable lookup.

Requires: pip install arancel-mx
"""

from arancel_mx import Dataset


def citation(info) -> str:
    verified = "release-verified" if info.release_verified else "structural-only"
    return (
        f"arancel-mx dataset {info.dataset_version} ({verified}, {info.source})\n"
        f"schema {info.schema_version}\n"
        f"local file {info.path}"
    )


def main() -> None:
    dataset = Dataset.latest()
    print(citation(dataset.info))

    record = dataset.lookup("85171301")
    print(f"\n{record.code} [{record.level}] {record.description}")
    print(f"IGI {record.igi_text} | IGE {record.ige_text} | unit {record.unit_name}")
    print(
        f"rate basis {record.validity_basis} | "
        f"effective {record.effective_from} .. {record.effective_to}"
    )

    print("\nHierarchy:")
    parent = dataset.parent(record.code)
    while parent is not None:
        print(f"  {parent.level} {parent.code}")
        parent = dataset.parent(parent.code)

    print("\nSearch:")
    for hit in dataset.search("telefono", limit=3):
        print(f"  {hit.match_kind} {hit.record.code} {hit.record.description[:60]}")


if __name__ == "__main__":
    main()
