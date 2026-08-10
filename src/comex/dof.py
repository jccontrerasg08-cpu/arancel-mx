"""DOF publication indexing and retrieval for foreign-trade context."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from . import db


DOF_BASE_URL = "https://www.dof.gob.mx"
TRADE_TERMS = (
    "aduana",
    "aduanero",
    "aduanera",
    "anam",
    "arancel",
    "comercio exterior",
    "cuota compensatoria",
    "exportacion",
    "fraccion arancelaria",
    "importacion",
    "nico",
    "nom",
    "pedimento",
    "reglas generales de comercio exterior",
    "rgce",
    "sat",
    "secretaria de economia",
    "tarifa",
    "tigie",
)
CONTEXT_ONLY_TERMS = {"secretaria de economia"}
NON_TRADE_TERMS = (
    "comision federal de electricidad",
    "energia electrica",
    "suministro basico",
)


@dataclass(frozen=True)
class DofPublication:
    publication_id: str
    title: str
    url: str
    published_date: str
    dof_code: str
    section: str
    topic: str
    summary: str
    source_file: str


class _DofLinkExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {name.lower(): value or "" for name, value in attrs}
        if tag.lower() == "a" and attr.get("href"):
            self._current = attr
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current is None:
            return
        href = urljoin(self.base_url, self._current.get("href", ""))
        title = _clean_text(" ".join(self._text))
        if title:
            self.links.append({"url": href, "title": title})
        self._current = None
        self._text = []


def dof_index_url(year: int, month: int, day: int) -> str:
    return f"{DOF_BASE_URL}/index.php?year={year:04d}&month={month:02d}&day={day:02d}"


def extract_dof_publications(html: str, base_url: str, source_file: str = "") -> list[dict[str, str]]:
    """Extract foreign-trade-relevant DOF note links from a daily index page."""
    parser = _DofLinkExtractor(base_url)
    parser.feed(html)
    found: dict[str, DofPublication] = {}
    for link in parser.links:
        parsed = urlparse(link["url"])
        if "dof.gob.mx" not in parsed.netloc.lower() or "nota_detalle.php" not in parsed.path:
            continue
        title = _clean_text(link["title"])
        if not _is_trade_related(title):
            continue
        query = parse_qs(parsed.query)
        dof_code = (query.get("codigo") or [""])[0]
        published_date = (query.get("fecha") or [""])[0]
        url = link["url"]
        publication_id = dof_code or hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        found.setdefault(
            publication_id,
            DofPublication(
                publication_id=publication_id,
                title=title,
                url=url,
                published_date=published_date,
                dof_code=dof_code,
                section=_guess_section(title),
                topic=_guess_topic(title),
                summary=title,
                source_file=source_file,
            ),
        )
    return [item.__dict__ for item in found.values()]


def index_dof_publications(html: str, base_url: str, source_file: str = "", db_path=db.DB_PATH) -> int:
    rows = extract_dof_publications(html, base_url, source_file)
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        if source_file:
            conn.execute("DELETE FROM dof_publication WHERE source_file = ?", [source_file])
        if not rows:
            return 0
        conn.executemany(
            """
            INSERT OR REPLACE INTO dof_publication (
                publication_id, title, url, published_date, dof_code,
                section, topic, summary, source_file, indexed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                (
                    row["publication_id"],
                    row["title"],
                    row["url"],
                    row["published_date"],
                    row["dof_code"],
                    row["section"],
                    row["topic"],
                    row["summary"],
                    row["source_file"],
                )
                for row in rows
            ],
        )
    return len(rows)


def search_dof_publications(query: str, limit: int = 8, db_path=db.DB_PATH) -> list[dict]:
    if not db_path.exists():
        return []
    db.init_db(db_path)
    query_terms = _terms(query)
    if not query_terms:
        query_terms = set(_normalize(" ".join(TRADE_TERMS)).split())
    rows = _cached_dof_rows(str(db_path), db_path.stat().st_mtime_ns)
    scored = []
    for row in rows:
        haystack = _normalize(" ".join(str(value or "") for value in row[1:8]))
        score = sum(5 if _contains_term(haystack, term) else 0 for term in query_terms)
        phrase = _normalize(query)
        if phrase and phrase in haystack:
            score += 20
        if score:
            scored.append((score, row))
    scored.sort(key=lambda item: (-item[0], item[1][3], item[1][1]))
    return [
        {
            "publication_id": row[0],
            "title": row[1],
            "url": row[2],
            "published_date": row[3],
            "dof_code": row[4],
            "section": row[5],
            "topic": row[6],
            "summary": row[7],
            "source_file": row[8],
            "score": score,
        }
        for score, row in scored[:limit]
    ]


@lru_cache(maxsize=8)
def _cached_dof_rows(db_path_text: str, _mtime_ns: int) -> tuple[tuple, ...]:
    with db.connect(Path(db_path_text), read_only=True) as conn:
        return tuple(conn.execute(
            """
            SELECT publication_id, title, url, published_date, dof_code,
                   section, topic, summary, source_file
            FROM dof_publication
            ORDER BY indexed_at DESC, published_date DESC
            LIMIT 500
            """
        ).fetchall())


def format_dof_context(rows: list[dict]) -> str:
    if not rows:
        return ""
    blocks = []
    for row in rows:
        blocks.append(
            "\n".join(
                [
                    f"[DOF | {row.get('published_date') or 'fecha n.d.'} | {row.get('topic') or 'comercio exterior'}]",
                    f"Titulo: {row.get('title')}",
                    f"URL: {row.get('url')}",
                    f"Resumen local: {row.get('summary')}",
                ]
            )
        )
    return "\n\n".join(blocks)


def dof_status(db_path=db.DB_PATH) -> dict:
    if not db_path.exists():
        return {"initialized": False, "items": 0, "latest": None}
    db.init_db(db_path)
    with db.connect(db_path, read_only=True) as conn:
        count = conn.execute("SELECT COUNT(*) FROM dof_publication").fetchone()[0]
        latest = conn.execute(
            """
            SELECT published_date, title, url
            FROM dof_publication
            ORDER BY indexed_at DESC, published_date DESC
            LIMIT 1
            """
        ).fetchone()
    return {
        "initialized": True,
        "items": int(count),
        "latest": {
            "published_date": latest[0],
            "title": latest[1],
            "url": latest[2],
        } if latest else None,
    }


def _is_trade_related(value: str) -> bool:
    normalized = _normalize(value)
    if any(term in normalized for term in NON_TRADE_TERMS):
        return False
    matched = {_normalize(term) for term in TRADE_TERMS if _contains_term(normalized, term)}
    strong = matched - {_normalize(term) for term in CONTEXT_ONLY_TERMS}
    return bool(strong)


def _guess_section(title: str) -> str:
    normalized = _normalize(title)
    if "secretaria de economia" in normalized:
        return "Secretaria de Economia"
    if "hacienda" in normalized or "sat" in normalized:
        return "SHCP/SAT"
    if "anam" in normalized or "aduana" in normalized:
        return "ANAM/Aduanas"
    return "DOF"


def _guess_topic(title: str) -> str:
    normalized = _normalize(title)
    for label, terms in (
        ("TIGIE/aranceles", ("tigie", "tarifa", "arancel", "fraccion arancelaria", "nico")),
        ("Aduanas/pedimentos", ("aduana", "anam", "pedimento")),
        ("Importacion/exportacion", ("importacion", "exportacion", "comercio exterior")),
        ("NOMs/regulaciones", ("nom", "cuota compensatoria", "reglas generales de comercio exterior", "rgce")),
    ):
        if any(_contains_term(normalized, term) for term in terms):
            return label
    return "Comercio exterior"


def _terms(value: str) -> set[str]:
    stop = {
        "para", "como", "cuando", "donde", "cual", "cuales", "sobre", "entre",
        "esta", "este", "estos", "estas", "hacer", "tengo", "puedo", "debo",
        "dime", "habla", "noticia", "noticias",
    }
    return {word for word in _normalize(value).split() if len(word) >= 3 and word not in stop}


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _contains_term(normalized_text: str, term: str) -> bool:
    normalized_term = _normalize(term)
    if not normalized_term:
        return False
    if " " in normalized_term:
        return normalized_term in normalized_text
    words = normalized_text.split()
    return any(word == normalized_term or (len(normalized_term) >= 5 and word.startswith(normalized_term)) for word in words)


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = "".join(ch if ch.isalnum() else " " for ch in text)
    return " ".join(text.split())
