"""Keep the 2026 status note aligned with the packaged instrument registry."""

from __future__ import annotations

import json
from importlib.resources import files


def _instruments() -> dict[str, dict]:
    raw = files("arancel_mx.sources").joinpath("legal_instruments.json").read_text(encoding="utf-8")
    payload = json.loads(raw)
    assert payload["version"] == "2026-10-30"
    return {item["id"]: item for item in payload["instruments"]}


def test_2026_status_instruments_match_the_packaged_registry() -> None:
    instruments = _instruments()

    ref02 = instruments["ref02"]
    assert ref02["dof_date"] == "2025-12-29"
    assert ref02["entry_into_force"] == "2026-01-01"
    assert ref02["validity_end"] is None
    assert len(ref02["rows"]) == 1463

    ref01 = instruments["ref01"]
    assert ref01["dof_date"] == "2025-07-21"
    assert ref01["entry_into_force"] == "2026-01-17"
    assert len(ref01["rows"]) == 11

    tarifa15 = instruments["tarifa15"]
    assert tarifa15["dof_date"] == "2026-04-23"
    assert tarifa15["entry_into_force"] == "2026-04-24"
    assert len(tarifa15["rows"]) == 185

    tarifa16 = instruments["tarifa16"]
    assert tarifa16["dof_date"] == "2026-10-13"
    assert tarifa16["entry_into_force"] == "2026-10-14"
    assert tarifa16["validity_end"] == "2031-10-14"
    assert len(tarifa16["rows"]) == 1

    assert instruments["tarifa09"]["validity_end"] == "2026-04-23"
    assert len(instruments["tarifa09"]["rows"]) == 544
    assert instruments["tarifa11"]["validity_end"] == "2026-04-23"
    assert len(instruments["tarifa11"]["rows"]) == 155
