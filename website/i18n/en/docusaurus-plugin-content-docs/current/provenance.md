# Provenance and evidence

Provenance is part of the data contract, not decorative metadata. A published row must be traceable to concrete source documents and to the execution that produced the release.

## Layers

```text
registered source
  -> captured document
  -> parsing / normalization
  -> reconciliation
  -> canonical record
  -> release
```

## Capture identity

For an official capture, the project preserves signals such as:

```text
authority
source_url
final_url
media_type
byte_size
sha256
retrieved_at
source_document_id
```

`retrieved_at` is the actual retrieval time. It is not the publication date or effective date.

## Legal evidence and structured data

The project separates source roles. DOF provides legal publication evidence, Diputados serves as the registered legislative compilation/ledger, and SNICE provides registered structured datasets. A convenient official source does not automatically become authoritative for every field.

VUCEM is being studied separately as an operational cross-check. See the repository's VUCEM characterization documentation. During this phase it is neither tariff authority nor a publication gate.

## Release provenance

`manifest.json` links the dataset to the registry, commit, and GitHub Actions execution. `official-sources.tar.gz` makes it possible to reconstruct which official bytes were observed.

Technical traceability does not replace legal interpretation or professional advice.
