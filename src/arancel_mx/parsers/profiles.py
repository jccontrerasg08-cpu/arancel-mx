"""Deterministic profile resolution for official tariff workbooks."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

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
            "igi": ("IGI", "IMP", "IMPORTACION"),
            "ige": ("IGE", "EXP", "EXPORTACION"),
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
) -> dict[str, str] | None:
    headers = [(str(value), _header_key(value)) for value in row if _header_key(value)]
    columns: dict[str, str] = {}
    for logical, aliases in {**required, **optional}.items():
        matches = [original for original, normalized in headers if normalized in aliases]
        if len(matches) > 1:
            raise ValueError(
                f"ambiguous workbook profile: {family}; "
                f"logical={logical}; matching_headers={matches!r}"
            )
        if matches:
            columns[logical] = matches[0]
        elif logical in required:
            return None
    return columns


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
        for row_number, row in enumerate(probe.samples.get(sheet, ()), start=1):
            try:
                columns = _logical_columns(row, required, optional, family)
            except ValueError as exc:
                raise ValueError(
                    f"{exc}; location={sheet}!{row_number}; row={row!r}"
                ) from exc
            if columns is not None:
                candidates.append(
                    WorkbookProfile(
                        sheet=sheet,
                        header_row=row_number,
                        columns=columns,
                    )
                )

    if not candidates:
        raise ValueError(f"unknown workbook profile: {family}")
    if len(candidates) != 1:
        details = [
            {
                "sheet": candidate.sheet,
                "header_row": candidate.header_row,
                "columns": dict(candidate.columns),
            }
            for candidate in candidates
        ]
        raise ValueError(f"ambiguous workbook profile: {family}; candidates={details!r}")
    return ResolvedWorkbookProfile(
        family=family,
        parser_version=str(definition["parser_version"]),
        profile=candidates[0],
    )
