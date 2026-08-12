from __future__ import annotations

import pytest

from arancel_mx.consumer.hs_sections import hs_sections, section_for_chapter


def test_hs_sections_are_the_21_ligie_groupings() -> None:
    sections = hs_sections()
    assert len(sections) == 21
    assert [section.roman for section in sections] == [
        "I",
        "II",
        "III",
        "IV",
        "V",
        "VI",
        "VII",
        "VIII",
        "IX",
        "X",
        "XI",
        "XII",
        "XIII",
        "XIV",
        "XV",
        "XVI",
        "XVII",
        "XVIII",
        "XIX",
        "XX",
        "XXI",
    ]
    assert {section.source for section in sections} == {"hs_section_grouping"}


def test_siicex_example_chapter_11_is_vegetable_products() -> None:
    section = section_for_chapter("11")
    assert section is not None
    assert section.roman == "II"
    assert section.name == "Productos del reino vegetal"
    assert section.chapter_from == "06"
    assert section.chapter_to == "14"


def test_live_animals_chapter_is_section_i() -> None:
    section = section_for_chapter("01")
    assert section is not None
    assert section.roman == "I"


def test_chapter_98_has_no_wco_section() -> None:
    assert section_for_chapter("98") is None


def test_reserved_chapter_77_still_belongs_to_section_xv() -> None:
    section = section_for_chapter("77")
    assert section is not None
    assert section.roman == "XV"


@pytest.mark.parametrize("value", ["1", "011", "ab", ""])
def test_section_for_chapter_rejects_non_hs2_values(value: str) -> None:
    with pytest.raises(ValueError, match="2-digit"):
        section_for_chapter(value)
