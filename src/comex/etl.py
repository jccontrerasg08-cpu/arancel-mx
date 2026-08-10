"""Public ANAM/VUCEM ETL sources and runner."""

from __future__ import annotations

import re
import hashlib
import json
import os
import ssl
from html.parser import HTMLParser
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util.retry import Retry

from . import db
from .arancel_sources import discover_official_documents
from .catalogs import refresh_catalog_sql
from .dof import dof_index_url, index_dof_publications
from .manifest import Manifest, new_artifact, sha256_file
from .paths import RAW_DIR, ensure_data_dirs


@dataclass(frozen=True)
class FetchTask:
    url: str
    relative_path: str
    extra: dict | None = None


class Source:
    name = ""
    description = ""

    def tasks(self) -> list[FetchTask]:
        raise NotImplementedError

    def discover_tasks(self, client: requests.Session, timeout_s: float) -> list[FetchTask]:
        return self.tasks()


class _LegacyTlsAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        context = ssl.create_default_context()
        # ponytail: VUCEM serves weak DH params; remove when the server updates TLS.
        context.set_ciphers("DEFAULT:@SECLEVEL=1")
        pool_kwargs["ssl_context"] = context
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )


class VucemTigieSource(Source):
    name = "vucem-tigie"
    description = "Assets publicos del clasificador arancelario VUCEM/TIGIE."
    base = "https://www.ventanillaunica.gob.mx/Clasificador"

    def tasks(self) -> list[FetchTask]:
        return [
            FetchTask(f"{self.base}/d3/general.js", "general.js", {"format": "js"}),
            FetchTask(f"{self.base}/d3/small1.js", "small1.js", {"format": "js"}),
            FetchTask(f"{self.base}/d3/sb.js", "sb.js", {"format": "js"}),
            FetchTask(f"{self.base}/data/arcosNuevos.txt", "arcosNuevos.txt", {"format": "tsv"}),
        ]


class SniceNicoSource(Source):
    name = "snice-nico"
    description = "Documentos oficiales SNICE de LIGIE, NICO y modificaciones."
    default_ligie_index_url = "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html"
    default_nico_index_url = "https://www.snice.gob.mx/cs/avi/snice/ligie.nico22.mod.html"
    default_modifications_index_url = "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.mod.html"

    def __init__(
        self,
        ligie_index_url: str | None = None,
        nico_index_url: str | None = None,
        modifications_index_url: str | None = None,
    ) -> None:
        self.ligie_index_url = ligie_index_url or os.environ.get(
            "SNICE_LIGIE_INDEX_URL", self.default_ligie_index_url
        )
        self.nico_index_url = nico_index_url or os.environ.get(
            "SNICE_NICO_INDEX_URL", self.default_nico_index_url
        )
        self.modifications_index_url = modifications_index_url or os.environ.get(
            "SNICE_LIGIE_MODIFICACIONES_INDEX_URL",
            self.default_modifications_index_url,
        )

    def tasks(self) -> list[FetchTask]:
        raise RuntimeError("SNICE document tasks require official index discovery")

    def discover_tasks(self, client: requests.Session, timeout_s: float) -> list[FetchTask]:
        documents = discover_official_documents(
            client,
            self.ligie_index_url,
            self.nico_index_url,
            self.modifications_index_url,
            timeout_s,
        )
        counters: dict[str, int] = {}
        tasks: list[FetchTask] = []
        for document in documents:
            kind = document["kind"]
            counters[kind] = counters.get(kind, 0) + 1
            suffix = Path(urlparse(document["source_url"]).path).suffix.lower()
            if suffix not in {".xls", ".xlsx", ".pdf", ".html"}:
                suffix = ".html"
            tasks.append(
                FetchTask(
                    document["source_url"],
                    f"{kind}-{counters[kind]:03d}{suffix}",
                    {
                        "format": suffix.lstrip("."),
                        "kind": kind,
                        "title": document["title"],
                    },
                )
            )
        return tasks


class HsGlobalSource(Source):
    name = "hs-global"
    description = "Catalogo global HSProducts 2/4/6 digitos desde World Bank/WITS."
    url = "https://wits.worldbank.org/data/public/HSProducts.xls"

    def tasks(self) -> list[FetchTask]:
        return [FetchTask(self.url, "HSProducts.xls", {"format": "xls", "scope": "global"})]


class VucemNotificationsSource(Source):
    name = "vucem-notificaciones"
    description = "Snapshot publico de notificaciones por estrado VUCEM."
    url = "https://www.ventanillaunica.gob.mx/vucem/Notificaciones.html"

    def tasks(self) -> list[FetchTask]:
        return [FetchTask(self.url, "notificaciones.html", {"format": "html", "optional": True})]


class VucemHojasSource(Source):
    name = "vucem-hojas-informativas"
    description = "Pagina publica de hojas informativas VUCEM."
    url = "https://www.ventanillaunica.gob.mx/vucem/HojaInformativa.html"

    def tasks(self) -> list[FetchTask]:
        return [FetchTask(self.url, "hojas-informativas.html", {"format": "html", "optional": True})]


class AnamCorpusSource(Source):
    name = "anam-corpus"
    description = "Paginas publicas ANAM: MOA, normatividad, tratados, glosario y aduanas."
    base = "https://www.anam.gob.mx"
    pages = {
        "moa.html": "/moa/",
        "disposiciones.html": "/disposiciones-vigentes-en-materia-de-comercio-exterior/",
        "tratados.html": "/tratados-y-acuerdos-firmados-con-mexico/",
        "aduanas.html": "/informacion-por-aduanas-2022/",
        "glosario.html": "/glosario-anam/",
        "normatividad.html": "/normatividad_2022/",
    }

    def tasks(self) -> list[FetchTask]:
        return [
            FetchTask(f"{self.base}{path}", name, {"format": "html"})
            for name, path in self.pages.items()
        ]


class DofComexSource(Source):
    name = "dof-comex"
    description = "Indices recientes del DOF filtrados para comercio exterior."

    def tasks(self) -> list[FetchTask]:
        days = _int_env("DOF_LOOKBACK_DAYS", 14)
        today = date.today()
        tasks = []
        for offset in range(max(days, 1)):
            current = today - timedelta(days=offset)
            tasks.append(
                FetchTask(
                    dof_index_url(current.year, current.month, current.day),
                    f"{current:%Y-%m-%d}.html",
                    {"format": "html", "scope": "dof-comex", "date": f"{current:%Y-%m-%d}", "optional": True},
                )
            )
        return tasks


SOURCES: dict[str, Source] = {
    source.name: source
    for source in (
        VucemTigieSource(),
        SniceNicoSource(),
        HsGlobalSource(),
        VucemNotificationsSource(),
        VucemHojasSource(),
        AnamCorpusSource(),
        DofComexSource(),
    )
}


def discover_registered_official_sources(registry, client):
    """Discover allowlisted official documents without changing legacy ETL sources."""
    from .arancel_reconcile import discover_registered_sources

    return discover_registered_sources(registry, client)


def list_sources() -> list[dict]:
    return [{"name": source.name, "description": source.description} for source in SOURCES.values()]


def _target_path(source: Source, task: FetchTask) -> Path:
    return RAW_DIR / source.name / task.relative_path


def _download(client: requests.Session, task: FetchTask, timeout_s: float) -> bytes:
    response = client.get(task.url, timeout=timeout_s)
    if task.extra and task.extra.get("optional") and response.status_code == 404:
        return b""
    response.raise_for_status()
    return response.content


def _index_downloaded_file(source: str, path: Path, url: str) -> None:
    if path.stat().st_size == 0:
        return
    if source in {"vucem-tigie", "snice-nico", "hs-global"}:
        refresh_catalog_sql()
        return
    if source == "vucem-notificaciones":
        _index_notifications(path)
        return
    if source == "dof-comex":
        index_dof_publications(path.read_text(encoding="utf-8", errors="ignore"), url, str(path))
        return
    if source == "anam-corpus":
        with db.connect() as conn:
            key = path.stem
            file_hash = sha256_file(path)
            conn.execute(
                """
                INSERT OR REPLACE INTO anam_public_pages
                (page_key, url, title, source_file, sha256, fetched_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                [key, url, key.replace("-", " ").title(), str(path), file_hash],
            )
            if key == "tratados":
                rows = _extract_anam_trade_agreements(path.read_text(encoding="utf-8", errors="ignore"), url)
                conn.execute("DELETE FROM anam_trade_agreements WHERE page_key = ?", [key])
                for row in rows:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO anam_trade_agreements
                        (agreement_key, page_key, title, url, host, dof_code, published_date,
                         source_file, sha256, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        [
                            row["agreement_key"],
                            key,
                            row["title"],
                            row["url"],
                            row["host"],
                            row["dof_code"],
                            row["published_date"],
                            str(path),
                            file_hash,
                        ],
                    )


class _LinkExtractor(HTMLParser):
    def __init__(self, base_url: str):
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
        elif tag.lower() == "img" and self._current and attr.get("alt"):
            self._text.append(attr["alt"])

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current is None:
            return
        href = urljoin(self.base_url, self._current.get("href", ""))
        text = _clean_link_text(" ".join(self._text))
        title = text or _clean_link_text(self._current.get("title") or self._current.get("aria-label") or "")
        self.links.append({"url": href, "title": title})
        self._current = None
        self._text = []


def _extract_anam_trade_agreements(html: str, base_url: str) -> list[dict[str, str]]:
    parser = _LinkExtractor(base_url)
    parser.feed(html)
    found: dict[str, dict[str, str]] = {}
    for link in parser.links:
        parsed = urlparse(link["url"])
        host = parsed.netloc.lower()
        if "dof.gob.mx" not in host:
            continue
        query = parse_qs(parsed.query)
        url = link["url"]
        title = link["title"] or _fallback_link_title(parsed.path)
        dof_code = (query.get("codigo") or [""])[0]
        published_date = (query.get("fecha") or [""])[0]
        if re.fullmatch(r"acuerdo\d+", title.strip(), flags=re.IGNORECASE):
            title = _fallback_dof_title(dof_code, published_date)
        found.setdefault(
            url,
            {
                "agreement_key": hashlib.sha1(url.encode("utf-8")).hexdigest()[:16],
                "title": title,
                "url": url,
                "host": host,
                "dof_code": dof_code,
                "published_date": published_date,
            },
        )
    return list(found.values())


def _clean_link_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _fallback_link_title(path: str) -> str:
    name = Path(path).stem.replace("_", " ").replace("-", " ").strip()
    return name or "Documento DOF"


def _fallback_dof_title(dof_code: str, published_date: str) -> str:
    bits = ["Documento DOF"]
    if published_date:
        bits.append(published_date)
    if dof_code:
        bits.append(f"codigo {dof_code}")
    return " - ".join(bits)


def _index_notifications(path: Path) -> int:
    html = path.read_text(encoding="utf-8", errors="ignore")
    rfcs = sorted(set(re.findall(r"\b[A-Z&]{3,4}\d{6}[A-Z0-9]{3}\b", html.upper())))
    loaded = 0
    with db.connect() as conn:
        for rfc in rfcs:
            nid = f"{path.name}:{rfc}"
            conn.execute(
                """
                INSERT OR REPLACE INTO vucem_notifications
                (notification_id, rfc, title, body, source_file)
                VALUES (?, ?, ?, ?, ?)
                """,
                [nid, rfc, "Notificacion publica VUCEM", _snippet_for_rfc(html, rfc), str(path)],
            )
            loaded += 1
    return loaded


def _snippet_for_rfc(text: str, rfc: str, radius: int = 220) -> str:
    idx = text.upper().find(rfc)
    if idx < 0:
        return ""
    raw = text[max(0, idx - radius): idx + len(rfc) + radius]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)).strip()


def run_etl(source_name: str | None = None, timeout_s: float = 30.0) -> dict:
    """Download one source or all sources, update manifest and index local data."""
    ensure_data_dirs()
    db.init_db()
    selected = [SOURCES[source_name]] if source_name else list(SOURCES.values())
    manifest = Manifest()
    stats = {"sources": 0, "files_seen": 0, "files_changed": 0, "errors": [], "warnings": []}

    with requests.Session() as client:
        client.headers.update(
            {"User-Agent": os.environ.get("ARANCEL_MX_USER_AGENT", "comercio-exterior-mexico/1.0")}
        )
        client.mount("http://", _http_adapter())
        client.mount("https://", _http_adapter())
        client.mount("https://www.ventanillaunica.gob.mx", _LegacyTlsAdapter(max_retries=_http_retries()))
        for source in selected:
            stats["sources"] += 1
            load_run_id = db.create_load_run(source.name, "etl")
            records_loaded = 0
            warnings = []
            try:
                tasks = source.discover_tasks(client, timeout_s)
                for task in tasks:
                    stats["files_seen"] += 1
                    try:
                        target = _target_path(source, task)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        content = _download(client, task, timeout_s)
                        artifact = new_artifact(source.name, task.url, target, content, task.extra)
                        changed = manifest.upsert(artifact)
                        if changed or not target.exists():
                            target.write_bytes(content)
                            stats["files_changed"] += 1
                        _index_downloaded_file(source.name, target, task.url)
                        records_loaded += 1
                    except Exception as exc:
                        if task.extra and task.extra.get("optional"):
                            warning = {"source": source.name, "url": task.url, "warning": str(exc)}
                            warnings.append(warning)
                            stats["warnings"].append(warning)
                            continue
                        raise
                db.finish_load_run(load_run_id, "OK", records_read=len(tasks), records_loaded=records_loaded, message=json.dumps(warnings, ensure_ascii=False) if warnings else "")
            except Exception as exc:
                message = str(exc)
                stats["errors"].append({"source": source.name, "error": message})
                db.finish_load_run(load_run_id, "ERROR", message=message)
    return stats


def etl_status() -> dict:
    return {"sources": list_sources(), "manifest": Manifest().summary(), "db": db.db_status()}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _http_retries() -> Retry:
    return Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )


def _http_adapter() -> HTTPAdapter:
    return HTTPAdapter(max_retries=_http_retries())
