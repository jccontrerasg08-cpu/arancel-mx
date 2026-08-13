"""Deterministic profile resolution for official tariff workbooks."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from arancel_mx.domain.normalization import normalize_code
from arancel_mx.parsers.workbooks import WorkbookProbe, WorkbookProfile


@dataclass(frozen=True)
class ResolvedWorkbookProfile:
    family: str
    parser_version: str
    profile: WorkbookProfile


_PROFILE_ALIASES = {
    "ligie_snapshot": {
        "required": {
            "code": ("FRACCION", "FRACCION ARANCELARIA"),
            "description": ("DESCRIPCION",),
        },
        "optional": {
            "unit_name": ("UNIDAD", "UNIDAD DE MEDIDA", "UMT"),
            "igi": ("IGI", "IMP", "IMPORT", "IMPORTACION"),
            "ige": ("IGE", "EXP", "EXPORT", "EXPORTACION"),
        },
        "parser_version": "ligie-profile-1",
    },
    "nico_snapshot": {
        "required": {
            "fraccion8": ("FRACCION", "FRACCION ARANCELARIA"),
            "nico2": ("NICO",),
            "description": ("DESCRIPCION", "DESCRIPCION NICO"),
        },
        "optional": {},
        "parser_version": "nico-profile-1",
    },
}


def _header_key(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    plain = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", " ", plain.upper()).strip()


def _logical_columns(
    row: tuple[object, ...],
    required: dict[str, tuple[str, ...]],
    optional: dict[str, tuple[str, ...]],
    family: str,
) -> tuple[dict[str, str], dict[str, int]] | None:
    headers = [
        (index, str(value), _header_key(value))
        for index, value in enumerate(row)
        if _header_key(value)
    ]
    columns: dict[str, str] = {}
    indices: dict[str, int] = {}
    for logical, aliases in {**required, **optional}.items():
        matches = [
            (index, original)
            for index, original, normalized in headers
            if normalized in aliases
        ]
        if len(matches) > 1:
            raise ValueError(
                f"ambiguous workbook profile: {family}; "
                f"logical={logical}; matching_headers={[item[1] for item in matches]!r}"
            )
        if matches:
            index, original = matches[0]
            columns[logical] = original
            indices[logical] = index
        elif logical in required:
            return None
    return columns, indices


def _supplement_ligie_tariff_columns(
    samples: tuple[tuple[object, ...], ...],
    row_number: int,
    columns: dict[str, str],
    indices: dict[str, int],
    optional: dict[str, tuple[str, ...]],
    family: str,
) -> tuple[dict[str, str], dict[str, int], int]:
    data_row = row_number + 1
    missing_rates = {"igi", "ige"}.difference(columns)
    if not missing_rates or row_number >= len(samples):
        return columns, indices, data_row

    rate_aliases = {
        logical: aliases
        for logical, aliases in optional.items()
        if logical in missing_rates
    }
    supplemental = _logical_columns(
        samples[row_number],
        {},
        rate_aliases,
        family,
    )
    if supplemental is None:
        _reject_unresolved_two_row_header(
            samples, row_number, indices, missing_rates, family
        )
        return columns, indices, data_row
    supplemental_columns, supplemental_indices = supplemental
    if not missing_rates.issubset(supplemental_columns):
        _reject_unresolved_two_row_header(
            samples, row_number, indices, missing_rates, family
        )
        return columns, indices, data_row

    merged_columns = {**columns, **supplemental_columns}
    merged_indices = {**indices, **supplemental_indices}
    return merged_columns, merged_indices, row_number + 2


def _reject_unresolved_two_row_header(
    samples: tuple[tuple[object, ...], ...],
    row_number: int,
    indices: dict[str, int],
    missing_rates: set[str],
    family: str,
) -> None:
    if row_number >= len(samples):
        return
    next_row = samples[row_number]
    code_index = indices.get("code")
    if code_index is None or code_index >= len(next_row):
        return
    try:
        code = normalize_code(next_row[code_index])
    except ValueError:
        code = ""
    if len(code) == 8:
        return
    raise ValueError(
        f"unresolved two-row tariff header: {family}; "
        f"missing_rates={sorted(missing_rates)}"
    )


def resolve_workbook_profile(
    probe: WorkbookProbe,
    family: str,
) -> ResolvedWorkbookProfile:
    """Resolve one registered workbook layout without guessing headers."""
    definition = _PROFILE_ALIASES.get(family)
    if definition is None:
        raise ValueError(f"unknown workbook profile: {family}")

    candidates: list[WorkbookProfile] = []
    required = definition["required"]
    optional = definition["optional"]
    for sheet in probe.sheet_names:
        samples = probe.samples.get(sheet, ())
        for row_number, row in enumerate(samples, start=1):
            try:
                resolved = _logical_columns(row, required, optional, family)
            except ValueError as exc:
                raise ValueError(
                    f"{exc}; location={sheet}!{row_number}; row={row!r}"
                ) from exc
            if resolved is None:
                continue
            columns, indices = resolved
            data_row = row_number + 1
            if family == "ligie_snapshot":
                columns, indices, data_row = _supplement_ligie_tariff_columns(
                    samples,
                    row_number,
                    columns,
                    indices,
                    optional,
                    family,
                )
            candidates.append(
                WorkbookProfile(
                    sheet=sheet,
                    header_row=row_number,
                    columns=columns,
                    data_row=data_row,
                    column_indices=indices,
                )
            )

    if not candidates:
        raise ValueError(f"unknown workbook profile: {family}")
    if len(candidates) > 1:
        max_specificity = max(len(candidate.columns) for candidate in candidates)
        most_specific = [
            candidate
            for candidate in candidates
            if len(candidate.columns) == max_specificity
        ]
        if len(most_specific) == 1:
            candidates = most_specific
    if len(candidates) != 1:
        details = [
            {
                "sheet": candidate.sheet,
                "header_row": candidate.header_row,
                "columns": dict(candidate.columns),
            }
            for candidate in candidates
        ]
        locations = [f"{candidate.sheet}!{candidate.header_row}" for candidate in candidates]
        raise ValueError(
            f"ambiguous workbook profile: {family}; "
            f"candidates={details!r}; locations={locations!r}"
        )
    return ResolvedWorkbookProfile(
        family=family,
        parser_version=str(definition["parser_version"]),
        profile=candidates[0],
    )
