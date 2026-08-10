"""
Descarga el directorio de cuadros del SIE Banxico para el sector 1.

Uso:
    python banxico_directorio.py
    python banxico_directorio.py --comercio
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import requests


URL = (
    "https://www.banxico.org.mx/SieInternet/consultarDirectorioInternetAction.do"
    "?&sector=1&accion=consultarDirectorioCuadros&locale=es"
)
OUT = Path(__file__).resolve().parent / "data" / "banxico_sector1_cuadros.json"
SCAN_OUT = Path(__file__).resolve().parent / "data" / "banxico_sector1_scan.json"
COMERCIO_TERMS = (
    "balanza comercial",
    "mercanc",
    "export",
    "import",
    "manufactur",
    "agropecuario",
    "petroler",
    "petroqu",
)
COMERCIO_IDS = {
    "CA176",
    "CA179",
    "CA181",
    "CA81",
    "CA180",
    "CA186",
    "CA187",
    "CA188",
    "CA189",
    "CA7",
    "CA177",
    "CA178",
    "CA6",
    "CA182",
    "CA183",
    "CA8",
    "CA184",
    "CA185",
    "CE125",
    "CE197",
    "CE198",
    "CE130",
    "CE132",
    "CE134",
    "CE135",
    "CE160",
    "CE171",
    "CE172",
    "CE173",
    "CE199",
    "CE200",
    "CE127",
    "CE79",
    "CE126",
    "CE122",
    "CE191",
    "CE192",
    "CE121",
    "CE201",
    "CE202",
    "CE124",
    "CE195",
    "CE196",
    "CE123",
    "CE193",
    "CE194",
    "CE37",
    "CE45",
    "CE41",
    "CE49",
    "CE55",
    "CE51",
    "CE86",
    "CE114",
    "CE115",
    "CE85",
    "CE116",
    "CE117",
    "CE87",
    "CE128",
    "CE129",
}


def _decode_response(response: requests.Response) -> str:
    encoding = response.encoding or response.apparent_encoding or "ISO-8859-1"
    return response.content.decode(encoding, errors="replace")


def _clean_text(value: str) -> str:
    return " ".join(html.unescape(value or "").split())


def descargar_directorio() -> list[dict[str, str]]:
    response = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    text = _decode_response(response)

    cuadros = []
    seen = set()
    pattern = re.compile(r"idCuadro=([A-Z0-9]+).*?>([^<]{3,200})<", re.I | re.S)
    for match in pattern.finditer(text):
        cuadro_id = match.group(1)
        nombre = _clean_text(match.group(2))
        if not nombre or (cuadro_id, nombre) in seen:
            continue
        seen.add((cuadro_id, nombre))
        cuadros.append(
            {
                "idCuadro": cuadro_id,
                "nombre": nombre,
                "url": (
                    "https://www.banxico.org.mx/SieInternet/"
                    "consultarDirectorioInternetAction.do?"
                    f"accion=consultarCuadro&idCuadro={cuadro_id}&sector=1&locale=es"
                ),
            }
        )
    return cuadros


def es_comercio(cuadro: dict[str, str]) -> bool:
    if cuadro["idCuadro"] in COMERCIO_IDS:
        return True
    nombre = cuadro["nombre"].lower()
    return any(term in nombre for term in COMERCIO_TERMS)


def _extract_title(text: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    return _clean_text(match.group(1)) if match else ""


def _extract_links(text: str, base_url: str) -> list[dict[str, str]]:
    links = []
    pattern = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
    href_pattern = re.compile(r"""href\s*=\s*["']?([^"'\s>]+)""", re.I)
    tag_pattern = re.compile(r"<[^>]+>")
    for match in pattern.finditer(text):
        href_match = href_pattern.search(match.group(1))
        if not href_match:
            continue
        href = href_match.group(1)
        label = _clean_text(tag_pattern.sub(" ", match.group(2)))
        links.append({"texto": label, "url": urljoin(base_url, href)})
    return links


def _extract_series(text: str) -> list[str]:
    patterns = [
        r"idSerie=([A-Z]{1,3}\d+)",
        r"series/([A-Z]{1,3}\d+)",
        r"\b(S[EF]\d{3,})\b",
    ]
    found = []
    for pattern in patterns:
        found.extend(re.findall(pattern, text, re.I))
    return sorted({serie.upper() for serie in found})


def escanear_cuadro(
    session: requests.Session,
    cuadro: dict[str, str],
    retries: int = 2,
    retry_delay: float = 10.0,
) -> dict[str, object]:
    result: dict[str, object] = {
        "idCuadro": cuadro["idCuadro"],
        "nombre": cuadro["nombre"],
        "url": cuadro["url"],
        "ok": False,
        "status_code": None,
        "content_type": "",
        "bytes": 0,
        "titulo": "",
        "series": [],
        "series_count": 0,
        "links_count": 0,
        "links": [],
        "error": "",
    }
    for attempt in range(retries + 1):
        try:
            response = session.get(cuadro["url"], timeout=30)
            result["status_code"] = response.status_code
            result["content_type"] = response.headers.get("content-type", "")
            result["bytes"] = len(response.content)
            if response.status_code == 429 and attempt < retries:
                time.sleep(retry_delay)
                continue
            response.raise_for_status()
            text = _decode_response(response)
            links = _extract_links(text, cuadro["url"])
            series = _extract_series(text)
            result.update(
                {
                    "ok": True,
                    "titulo": _extract_title(text),
                    "series": series,
                    "series_count": len(series),
                    "links_count": len(links),
                    "links": links[:50],
                    "error": "",
                }
            )
            break
        except Exception as exc:
            result["error"] = str(exc)
    return result


def escanear_directorio(cuadros: list[dict[str, str]], delay: float = 0.0) -> dict[str, object]:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    paginas = []
    for index, cuadro in enumerate(cuadros, start=1):
        print(f"[{index}/{len(cuadros)}] {cuadro['idCuadro']} {cuadro['nombre']}")
        paginas.append(escanear_cuadro(session, cuadro))
        if delay:
            time.sleep(delay)
    ok = sum(1 for pagina in paginas if pagina["ok"])
    series = sorted({serie for pagina in paginas for serie in pagina.get("series", [])})
    return {
        "fuente": URL,
        "escaneado_en": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "paginas_total": len(paginas),
        "paginas_ok": ok,
        "paginas_error": len(paginas) - ok,
        "series_unicas": len(series),
        "series": series,
        "paginas": paginas,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comercio", action="store_true", help="Muestra solo cuadros de comercio exterior.")
    parser.add_argument("--scan", action="store_true", help="Escanea cada pagina de cuadro encontrada.")
    parser.add_argument("--delay", type=float, default=0.0, help="Pausa en segundos entre paginas al escanear.")
    parser.add_argument("--output", type=Path, default=OUT, help="Ruta JSON de salida.")
    args = parser.parse_args()

    cuadros = descargar_directorio()
    if args.comercio:
        cuadros = [cuadro for cuadro in cuadros if es_comercio(cuadro)]

    if args.scan:
        output = args.output if args.output != OUT else SCAN_OUT
        reporte = escanear_directorio(cuadros, args.delay)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            "OK. "
            f"{reporte['paginas_ok']}/{reporte['paginas_total']} paginas, "
            f"{reporte['series_unicas']} series unicas guardadas en {output}"
        )
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(cuadros, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK. {len(cuadros)} cuadros guardados en {args.output}")


if __name__ == "__main__":
    main()
