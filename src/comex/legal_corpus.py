"""Local Markdown corpus retrieval for Mexican foreign-trade documents."""

from __future__ import annotations

import os
import csv
import hashlib
import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .paths import LEGAL_CORPUS_DIR, STATE_DIR, ensure_data_dirs


MAX_CHARS = 1500
DEFAULT_LIMIT = 5
SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".csv", ".tsv", ".json", ".jsonl"}


@dataclass(frozen=True)
class CorpusChunk:
    source: str
    title: str
    heading: str
    text: str


def corpus_dir() -> Path:
    custom = os.environ.get("COMEX_LEGAL_CORPUS_DIR", "").strip()
    return Path(custom) if custom else LEGAL_CORPUS_DIR


def legal_corpus_status() -> dict:
    ensure_data_dirs()
    root = corpus_dir()
    files = _corpus_files(root)
    unsupported = _unsupported_corpus_files(root)
    chunks = _cached_chunks(str(root), _corpus_signature(root))
    return {
        "path": str(root),
        "files": len(files),
        "ignored_files": len(unsupported),
        "chunks": len(chunks),
        "sources": [str(path.relative_to(root)) for path in files[:30]],
        "ignored_sources": [str(path.relative_to(root)) for path in unsupported[:30]],
    }


def retrieve_legal_context(query: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    ensure_data_dirs()
    query_terms = _terms(query)
    if not query_terms:
        return []
    root = corpus_dir()
    signature = _corpus_signature(root)
    scored = []
    chunks = _cached_chunks(str(root), signature)
    for chunk in _candidate_chunks(root, signature, chunks, query_terms):
        score = _score(query_terms, chunk)
        if score:
            scored.append((score, chunk))
    scored.sort(key=lambda item: (-item[0], item[1].source, item[1].heading))
    return [
        {
            "source": chunk.source,
            "title": chunk.title,
            "heading": chunk.heading,
            "text": chunk.text,
            "score": score,
        }
        for score, chunk in scored[:limit]
    ]


def format_legal_context(chunks: list[dict]) -> str:
    if not chunks:
        return ""
    blocks = []
    for item in chunks:
        title = item.get("title") or "Documento"
        heading = item.get("heading") or item.get("title") or "Documento"
        source = item.get("source") or "corpus local"
        score = item.get("score", "")
        text = re.sub(r"\s+", " ", str(item.get("text") or "")).strip()
        meta = f"source={source}; title={title}; heading={heading}; score={score}"
        blocks.append(f"[{meta}]\n{text[:MAX_CHARS]}")
    return "\n\n".join(blocks)


def _corpus_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_SUFFIXES
        and path.name.lower() != "readme.md"
        and not path.name.startswith(".")
    )


def _unsupported_corpus_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() not in SUPPORTED_SUFFIXES
        and path.name.lower() != "readme.md"
        and not path.name.startswith(".")
    )


def _corpus_signature(root: Path) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        (str(path.relative_to(root)), path.stat().st_mtime_ns, path.stat().st_size)
        for path in _corpus_files(root)
    )


def _index_path(root: Path) -> Path:
    digest = hashlib.sha1(str(root.resolve()).encode("utf-8")).hexdigest()[:12]
    return STATE_DIR / f"legal_corpus_{digest}.sqlite"


def _candidate_chunks(
    root: Path,
    signature: tuple[tuple[str, int, int], ...],
    chunks: tuple[CorpusChunk, ...],
    query_terms: set[str],
) -> tuple[CorpusChunk, ...]:
    try:
        return _fts_candidates(root, signature, chunks, query_terms)
    except sqlite3.Error:
        return chunks


def _fts_candidates(
    root: Path,
    signature: tuple[tuple[str, int, int], ...],
    chunks: tuple[CorpusChunk, ...],
    query_terms: set[str],
    limit: int = 80,
) -> tuple[CorpusChunk, ...]:
    if not chunks or not query_terms:
        return chunks
    path = _index_path(root)
    expected = json.dumps(signature, ensure_ascii=False)
    query = " OR ".join(sorted(query_terms))
    ensure_data_dirs()
    with sqlite3.connect(path) as conn:
        current = _fts_signature(conn)
        if current != expected:
            _rebuild_fts(conn, chunks, expected)
        rows = conn.execute(
            "SELECT rowid FROM chunk_fts WHERE chunk_fts MATCH ? LIMIT ?",
            [query, limit],
        ).fetchall()
    if not rows:
        return chunks
    return tuple(chunks[row[0] - 1] for row in rows if 0 < row[0] <= len(chunks))


def _fts_signature(conn: sqlite3.Connection) -> str:
    conn.execute("CREATE TABLE IF NOT EXISTS corpus_meta (key TEXT PRIMARY KEY, value TEXT)")
    row = conn.execute("SELECT value FROM corpus_meta WHERE key = 'signature'").fetchone()
    return str(row[0]) if row else ""


def _rebuild_fts(conn: sqlite3.Connection, chunks: tuple[CorpusChunk, ...], signature: str) -> None:
    conn.execute("DROP TABLE IF EXISTS chunk_fts")
    conn.execute("CREATE VIRTUAL TABLE chunk_fts USING fts5(source, title, heading, text)")
    conn.executemany(
        "INSERT INTO chunk_fts (source, title, heading, text) VALUES (?, ?, ?, ?)",
        [(chunk.source, chunk.title, chunk.heading, chunk.text) for chunk in chunks],
    )
    conn.execute(
        "INSERT OR REPLACE INTO corpus_meta (key, value) VALUES ('signature', ?)",
        [signature],
    )


@lru_cache(maxsize=8)
def _cached_chunks(root_text: str, _signature: tuple[tuple[str, int, int], ...]) -> tuple[CorpusChunk, ...]:
    root = Path(root_text)
    chunks = []
    for path in _corpus_files(root):
        chunks.extend(_chunks_from_file(path, root))
    return tuple(chunks)


def _chunks_from_file(path: Path, root: Path) -> list[CorpusChunk]:
    text = _read_document_text(path)
    title = _title_from_text(text) or path.stem.replace("_", " ").replace("-", " ").title()
    sections = _sections(text)
    chunks = []
    rel = str(path.relative_to(root))
    for heading, body in sections:
        clean = _clean_markdown(body)
        if not clean:
            continue
        for part in _split_text(clean, MAX_CHARS):
            chunks.append(CorpusChunk(rel, title, heading or title, part))
    return chunks


def _read_document_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        rows = []
        with path.open(encoding="utf-8", errors="ignore", newline="") as fh:
            for idx, row in enumerate(csv.DictReader(fh, delimiter=delimiter), start=1):
                cells = [f"{key}: {value}" for key, value in row.items() if value not in (None, "")]
                if cells:
                    rows.append(f"- fila {idx}: " + "; ".join(cells))
        return f"# {path.stem.replace('_', ' ').replace('-', ' ').title()}\n\n## Tabla estructurada\n" + "\n".join(rows)
    if suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            return path.read_text(encoding="utf-8", errors="ignore")
        return f"# {path.stem.replace('_', ' ').replace('-', ' ').title()}\n\n## JSON estructurado\n{json.dumps(data, ensure_ascii=False, indent=2)}"
    if suffix == ".jsonl":
        rows = []
        for idx, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                item = line
            rows.append(f"- fila {idx}: {json.dumps(item, ensure_ascii=False)}")
        return f"# {path.stem.replace('_', ' ').replace('-', ' ').title()}\n\n## JSONL estructurado\n" + "\n".join(rows)
    return path.read_text(encoding="utf-8", errors="ignore")


def _sections(text: str) -> list[tuple[str, str]]:
    current = ""
    buffer = []
    sections = []
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", line)
        if match:
            if buffer:
                sections.append((current, "\n".join(buffer)))
                buffer = []
            current = match.group(2).strip()
        else:
            buffer.append(line)
    if buffer:
        sections.append((current, "\n".join(buffer)))
    return sections or [("", text)]


def _split_text(text: str, max_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(paragraph[i:i + max_chars].strip() for i in range(0, len(paragraph), max_chars))
            continue
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) > max_chars and current:
            chunks.append(current.strip())
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current.strip())
    return chunks


def _title_from_text(text: str) -> str:
    match = re.search(r"^\s{0,3}#\s+(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _clean_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE)
    return re.sub(r"[ \t]+", " ", text).strip()


def _score(query_terms: set[str], chunk: CorpusChunk) -> int:
    haystack = _terms(f"{chunk.title} {chunk.heading} {chunk.text}")
    score = sum(4 if term in haystack else 0 for term in query_terms)
    phrase = _normalize(" ".join(query_terms))
    if phrase and phrase in _normalize(chunk.text):
        score += 10
    return score


def _terms(value: str) -> set[str]:
    normalized = _normalize(value)
    stop = {
        "para", "como", "cuando", "donde", "cual", "cuales", "sobre", "entre",
        "esta", "este", "estos", "estas", "hacer", "tengo", "puedo", "debo",
    }
    return {word for word in normalized.split() if len(word) >= 3 and word not in stop}


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = "".join(ch if ch.isalnum() else " " for ch in text)
    return " ".join(text.split())
