"""Reader for Annex 2.4.1 of the Secretaría de Economía foreign-trade rules.

The annex lists, for each tariff fraction, the Normas Oficiales Mexicanas (NOM) that
apply at the point of entry or exit. It is published as a table inside a long PDF.
This module turns the words of the annex pages into records.

The rows of the table are not aligned vertically in the PDF (a fraction code can sit a
few points below the first line of its description), so rows are read in the order the
document stores them, which keeps each row together: fraction, description, NOM and
"acotación", then each NICO with its description. Coordinates only decide the column, and the
boundary of the last column comes from the vertical rules the PDF draws for each table (it
differs from one table to another).

It fails closed: a word in the fraction column that is not a fraction, a table row
without a fraction, or a NOM code that does not look like one raises
:class:`AnnexParseError` instead of being guessed. Free text between tables (numeral
introductions) is kept apart so a caller can audit it.

The annex has five numerals with different legal meaning, and the numeral is kept on
every record:

1. imports subject to NOM (rule 2.4.3);
2. imports subject to NOM that cannot use the exemption of rule 2.4.11;
3. imports subject to NOM for commercial and sanitary information (rule 2.4.8): the NOM
   is named in the heading of each section (I, II, ...), not in the table;
4. exports subject to NOM (rule 2.4.9);
5. imports subject to emergency NOM (rule 2.4.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Iterable, Sequence

# x0, y0, x1, y1, text, block, line, word: the shape of ``page.get_text("words")``.
Word = tuple[float, float, float, float, str, int, int, int]

NUMERAL_MEANING = {
    1: "import_noms",
    2: "import_noms_without_exemption",
    3: "commercial_information_noms",
    4: "export_noms",
    5: "emergency_noms",
}

# Column starts measured on the whole annex: fraction ~91, NICO ~139-141, description ~161.
# The NOM or "acotación" column starts at a vertical rule drawn at x 375.8 or 392.7 depending on
# the table; description words can start close to it, so only the rule can tell them apart.
_FRACTION_COLUMN_MAX = 120.0
_NICO_COLUMN_MAX = 150.0
_NOM_RULE_RANGE = (360.0, 420.0)
_DEFAULT_NOM_COLUMN = 378.8
# A section number alone on its line is centered on the page (x ~ 299); a description that wraps
# can also leave a Roman-looking word ("XI.") alone, but in the description column (x ~ 161).
_CENTERED_MIN = 240.0
_CENTERED_MAX = 360.0
_LINE_TOLERANCE = 3.5
_ROW_TOLERANCE = 4.0
_HEADER_DEPTH = 46.0

_FRACTION = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")
_NICO = re.compile(r"^\d{2}$")
_NUMERAL = re.compile(r"^([1-5])\.-$")
_ROMAN = re.compile(r"^[IVX]+\.$")
_NOM_CODE = re.compile(
    r"NOM-(?:EM-)?\d{3}(?:/\d{1,2})?-[A-Z0-9]+(?:/[A-Z0-9]+)*(?:-[A-Z0-9]+(?:/[A-Z0-9]+)*)*-\d{4}"
)
_MARGIN_NOTE = re.compile(
    r"^(Numeral|Fracci[oó]n|P[aá]rrafo|Inciso|Anexo|Regla|Cap[ií]tulo|Apartado|Art[ií]culo)\s+"
    r"(reformad|adicionad|derogad|abrogad)",
    re.IGNORECASE,
)
_HEADER_WORDS = frozenset(
    {
        "Fracción",
        "arancelaria",
        "arancelaria/",
        "arancelaria/N",  # some headers split "NICO" as "N" + "ICO"
        "/NICO",
        "NICO",
        "ICO",
        "Descripción",
        "NOM",
        "/",
        "Acotación",
    }
)

_FRACTION_COL, _NICO_COL, _DESCRIPTION_COL, _NOM_COL = 0, 1, 2, 3


class AnnexParseError(ValueError):
    """The annex pages do not have the structure this reader knows."""


@dataclass(frozen=True)
class AnnexPage:
    """The words of one page and the vertical table rules drawn on it as (x, top, bottom)."""

    words: tuple[Word, ...]
    rules: tuple[tuple[float, float, float], ...] = ()


@dataclass(frozen=True)
class NomRequirement:
    """One NOM that applies to a fraction and, when present, the limit the annex sets."""

    nom: str
    scope: str | None


@dataclass(frozen=True)
class NicoLine:
    nico: str
    description: str


@dataclass(frozen=True)
class AnnexRecord:
    numeral: int
    section: str | None
    section_title: str | None
    fraction: str
    description: str
    requirements: tuple[NomRequirement, ...]
    nico: tuple[NicoLine, ...]
    page: int
    # NOM that a numeral 3 heading names only as cancelled ("cancela a la NOM-…"); never a requirement.
    superseded_noms: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnnexParse:
    records: tuple[AnnexRecord, ...]
    free_text: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class _Item:
    column: int
    text: str


@dataclass
class _Draft:
    numeral: int
    section: str | None
    section_title: str | None
    fraction: str
    page: int
    description: list[str] = field(default_factory=list)
    nom_lines: list[str] = field(default_factory=list)
    nico: list[tuple[str, list[str]]] = field(default_factory=list)


def _nom_column_start(y: float, rules: Sequence[tuple[float, float, float]]) -> float:
    """x where the NOM or "acotación" column starts at height ``y``: the table rule that covers it."""
    low, high = _NOM_RULE_RANGE
    covering = [
        x
        for x, top, bottom in rules
        if low <= x <= high and top - 2.0 <= y <= bottom + 2.0
    ]
    return min(covering) if covering else _DEFAULT_NOM_COLUMN


def _column(word: Word, rules: Sequence[tuple[float, float, float]]) -> int:
    x0 = word[0]
    if x0 < _FRACTION_COLUMN_MAX:
        return _FRACTION_COL
    if x0 < _NICO_COLUMN_MAX:
        return _NICO_COL
    if x0 < _nom_column_start(word[1], rules):
        return _DESCRIPTION_COL
    return _NOM_COL


def _join(parts: Iterable[str]) -> str:
    """Join wrapped lines: a trailing hyphen continues the word, anything else is a space."""
    text = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        text = (
            part
            if not text
            else (text + part if text.endswith("-") else f"{text} {part}")
        )
    return text


def _group_lines(words: Sequence[Word]) -> list[tuple[float, list[Word]]]:
    """Words grouped into lines by vertical position, each line ordered left to right."""
    lines: list[tuple[float, list[Word]]] = []
    for word in sorted(words, key=lambda item: (item[1], item[0])):
        if lines and abs(word[1] - lines[-1][0]) <= _LINE_TOLERANCE:
            lines[-1][1].append(word)
        else:
            lines.append((word[1], [word]))
    return [(y, sorted(line, key=lambda item: item[0])) for y, line in lines]


def _header_starts(words: Sequence[Word]) -> list[float]:
    """Vertical start of each table header: a line that is exactly "Fracción" with "arancelaria" below."""
    starts = []
    left = [word for word in words if word[0] < _NICO_COLUMN_MAX]
    for y, line in _group_lines(left):
        if len(line) == 1 and line[0][4] == "Fracción":
            if any(
                0 < word[1] - y < 20 and word[4].startswith("arancelaria")
                for word in left
            ):
                starts.append(y)
    return starts


def _in_header(word: Word, starts: Sequence[float]) -> bool:
    return word[4] in _HEADER_WORDS and any(
        -_LINE_TOLERANCE <= word[1] - y <= _HEADER_DEPTH for y in starts
    )


def _marker_words(words: Sequence[Word]) -> list[Word]:
    """Numeral ("4.-") and section ("XIV.") markers: at the left edge, or a section alone and centered."""
    found = []
    for _, line in _group_lines(words):
        first = line[0]
        if first[0] < _FRACTION_COLUMN_MAX and _NUMERAL.match(first[4]):
            found.append(first)
        elif _ROMAN.match(first[4]) and (
            first[0] < _FRACTION_COLUMN_MAX
            or (len(line) == 1 and _CENTERED_MIN <= first[0] <= _CENTERED_MAX)
        ):
            found.append(first)
    return found


def _reading_order(
    band: Sequence[Word], rules: Sequence[tuple[float, float, float]]
) -> list[_Item]:
    """Table text in document order: consecutive words of one line and one column make an item."""
    items: list[_Item] = []
    key: tuple[int, int, int] | None = None
    parts: list[str] = []
    for word in sorted(band, key=lambda item: (item[5], item[6], item[7])):
        current = (word[5], word[6], _column(word, rules))
        if current != key and parts and key is not None:
            items.append(_Item(key[2], _join(parts)))
            parts = []
        key = current
        parts.append(word[4])
    if parts and key is not None:
        items.append(_Item(key[2], _join(parts)))
    return items


class _Reader:
    def __init__(self) -> None:
        self.records: list[AnnexRecord] = []
        self.free_text: list[tuple[int, str]] = []
        self.draft: _Draft | None = None
        self.numeral: int | None = None
        self.section: str | None = None
        self.title: list[str] = []
        self.mode = "text"
        self.rules: tuple[tuple[float, float, float], ...] = ()

    def page(self, number: int, page: AnnexPage) -> None:
        self.rules = page.rules
        words = [word for word in page.words if word[4].strip()]
        starts = _header_starts(words)
        words = [word for word in words if not _in_header(word, starts)]
        markers = _marker_words(words)
        # Cut the page where a marker or a header begins; the part above the first cut
        # continues whatever the previous page was doing.
        cuts = sorted(
            [(word[1], "text", word) for word in markers]
            + [(y, "table", None) for y in starts],
            key=lambda cut: cut[0],
        )
        edges: list[tuple[float, float, str, Word | None]] = [
            (-1.0, cuts[0][0] - 0.01 if cuts else 100_000.0, self.mode, None)
        ]
        for position, (y, kind, marker) in enumerate(cuts):
            upper = (
                cuts[position + 1][0] - 0.01 if position + 1 < len(cuts) else 100_000.0
            )
            edges.append((y - 0.01, upper, kind, marker))
        for low, high, kind, marker in edges:
            band = [word for word in words if low <= word[1] <= high]
            if kind == "text":
                self._text(number, band, marker)
            else:
                self._table(number, band)
            self.mode = kind

    def _text(self, number: int, band: list[Word], marker: Word | None) -> None:
        if marker is not None:
            self._close()
            band = [word for word in band if word is not marker]
            if _NUMERAL.match(marker[4]):
                self.numeral = int(marker[4][0])
                self.section, self.title = None, []
            else:
                self.section, self.title = marker[4][:-1], []
        lines = [_join(word[4] for word in line) for _, line in _group_lines(band)]
        lines = [line for line in lines if line and not _MARGIN_NOTE.match(line)]
        if self.numeral == 3 and self.section is not None:
            self.title.extend(lines)
        else:
            self.free_text.extend((number, line) for line in lines)

    def _table(self, number: int, band: list[Word]) -> None:
        if self.numeral is None:
            raise AnnexParseError(f"table before any numeral on page {number}")
        for item in _reading_order(band, self.rules):
            if _MARGIN_NOTE.match(item.text):
                continue
            if self.draft is None and self.numeral == 5:
                # Numeral 5 (emergency NOM) has an empty table today, followed by explanatory paragraphs.
                self.free_text.append((number, item.text))
                continue
            if item.column == _FRACTION_COL:
                if not _FRACTION.match(item.text):
                    raise AnnexParseError(
                        f"unexpected text in the fraction column on page {number}: {item.text!r}"
                    )
                self._close()
                title = _join(self.title) if self.numeral == 3 else ""
                self.draft = _Draft(
                    self.numeral,
                    self.section,
                    title or None,
                    item.text.replace(".", ""),
                    number,
                )
                continue
            if self.draft is None:
                raise AnnexParseError(
                    f"table text before any fraction on page {number}: {item.text!r}"
                )
            if item.column == _NICO_COL:
                if not _NICO.match(item.text):
                    raise AnnexParseError(
                        f"unexpected text in the NICO column on page {number}: {item.text!r}"
                    )
                self.draft.nico.append((item.text, []))
            elif item.column == _DESCRIPTION_COL:
                (
                    self.draft.nico[-1][1]
                    if self.draft.nico
                    else self.draft.description
                ).append(item.text)
            else:
                self.draft.nom_lines.append(item.text)

    def _close(self) -> None:
        if self.draft is not None:
            self.records.append(_finish(self.draft))
            self.draft = None


def _finish(draft: _Draft) -> AnnexRecord:
    text = _join(draft.nom_lines)
    requirements: list[NomRequirement] = []
    superseded: tuple[str, ...] = ()
    if draft.numeral == 3:
        heading = draft.section_title or ""
        cancelled_at = re.search(r"\bcancela", heading)
        operative = heading[: cancelled_at.start()] if cancelled_at else heading
        noms = list(dict.fromkeys(_NOM_CODE.findall(operative)))
        superseded = tuple(
            code
            for code in dict.fromkeys(_NOM_CODE.findall(heading[len(operative) :]))
            if code not in noms
        )
        if not noms:
            raise AnnexParseError(
                f"no NOM named in the heading of the section of {draft.fraction}"
            )
        requirements = [NomRequirement(nom, text or None) for nom in noms]
    else:
        starts = [match.start() for match in re.finditer(r"NOM-", text)]
        if not starts:
            raise AnnexParseError(
                f"no NOM code for {draft.fraction} on page {draft.page}: {text[:60]!r}"
            )
        for position, start in enumerate(starts):
            end = starts[position + 1] if position + 1 < len(starts) else len(text)
            chunk = text[start:end].strip()
            match = _NOM_CODE.match(chunk)
            if match is None:
                raise AnnexParseError(
                    f"unreadable NOM code for {draft.fraction} on page {draft.page}: {chunk[:40]!r}"
                )
            requirements.append(
                NomRequirement(match.group(0), chunk[match.end() :].strip() or None)
            )
    return AnnexRecord(
        numeral=draft.numeral,
        section=draft.section,
        section_title=draft.section_title,
        fraction=draft.fraction,
        description=_join(draft.description),
        requirements=tuple(requirements),
        nico=tuple(NicoLine(nico, _join(lines)) for nico, lines in draft.nico),
        page=draft.page,
        superseded_noms=superseded,
    )


def parse_annex(pages: Sequence[AnnexPage], *, first_page: int = 1) -> AnnexParse:
    """Parse the annex pages into records, in document order."""
    reader = _Reader()
    for offset, words in enumerate(pages):
        reader.page(first_page + offset, words)
    reader._close()
    return AnnexParse(tuple(reader.records), tuple(reader.free_text))


def read_annex_pages(
    pdf_path: Path, first_page: int, last_page: int
) -> list[AnnexPage]:
    """Words and table rules of the annex pages (1-based, inclusive) of the registered PDF."""
    import pymupdf

    pages = []
    with pymupdf.open(pdf_path) as document:
        for number in range(first_page, last_page + 1):
            page = document[number - 1]
            words = tuple(
                (w[0], w[1], w[2], w[3], w[4], w[5], w[6], w[7])
                for w in page.get_text("words")
            )
            rules = tuple(
                (
                    round(d["rect"].x0 + d["rect"].width / 2, 1),
                    float(d["rect"].y0),
                    float(d["rect"].y1),
                )
                for d in page.get_drawings()
                if d["rect"].width < 2.5 and d["rect"].height > 15
            )
            pages.append(AnnexPage(words, rules))
    return pages
