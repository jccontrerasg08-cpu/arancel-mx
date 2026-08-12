"""HS section grouping derived from chapter number.

This is structural Harmonized System / LIGIE section membership, not a captured
SIICEX, CAAAREM, or other third-party document. Chapter 98 (Mexican special
operations) has no WCO section.
"""

from __future__ import annotations

from arancel_mx.consumer.models import HsSection


# Short LIGIE section headings. Chapter ranges follow the Harmonized System.
_SECTIONS: tuple[HsSection, ...] = (
    HsSection("I", "Animales vivos y productos del reino animal", "01", "05"),
    HsSection("II", "Productos del reino vegetal", "06", "14"),
    HsSection(
        "III",
        "Grasas y aceites animales, vegetales o de origen microbiano",
        "15",
        "15",
    ),
    HsSection("IV", "Productos de las industrias alimentarias", "16", "24"),
    HsSection("V", "Productos minerales", "25", "27"),
    HsSection(
        "VI",
        "Productos de las industrias químicas o de las industrias conexas",
        "28",
        "38",
    ),
    HsSection("VII", "Plástico y caucho, y sus manufacturas", "39", "40"),
    HsSection("VIII", "Pieles, cueros, peletería y manufacturas", "41", "43"),
    HsSection("IX", "Madera, carbón vegetal, corcho y cestería", "44", "46"),
    HsSection("X", "Pasta de madera, papel y cartón", "47", "49"),
    HsSection("XI", "Materias textiles y sus manufacturas", "50", "63"),
    HsSection("XII", "Calzado, sombreros, paraguas y similares", "64", "67"),
    HsSection(
        "XIII",
        "Manufacturas de piedra, productos cerámicos y vidrio",
        "68",
        "70",
    ),
    HsSection("XIV", "Perlas, piedras y metales preciosos; bisutería", "71", "71"),
    HsSection("XV", "Metales comunes y manufacturas de estos metales", "72", "83"),
    HsSection("XVI", "Máquinas, aparatos y material eléctrico", "84", "85"),
    HsSection("XVII", "Material de transporte", "86", "89"),
    HsSection(
        "XVIII",
        "Instrumentos de óptica, medida, relojería y música",
        "90",
        "92",
    ),
    HsSection("XIX", "Armas, municiones, y sus partes y accesorios", "93", "93"),
    HsSection("XX", "Mercancías y productos diversos", "94", "96"),
    HsSection("XXI", "Objetos de arte o colección y antigüedades", "97", "97"),
)


def hs_sections() -> tuple[HsSection, ...]:
    """Return the 21 HS/LIGIE sections in roman-numeral order."""

    return _SECTIONS


def section_for_chapter(chapter: str) -> HsSection | None:
    """Return the HS section for a 2-digit chapter, or None if ungrouped."""

    if not isinstance(chapter, str) or len(chapter) != 2 or not chapter.isdigit():
        raise ValueError(f"chapter must be a 2-digit code: {chapter!r}")
    for section in _SECTIONS:
        if section.chapter_from <= chapter <= section.chapter_to:
            return section
    return None
