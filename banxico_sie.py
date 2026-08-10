"""
Pipeline SIE Banxico - Comercio Exterior (datos 100% reales)
============================================================
Descarga las 22 series mensuales de la balanza comercial (cuadro CE125) desde la
API REST del SIE y ACTUALIZA data/comercio_exterior.json con la historia mensual
COMPLETA (sustituye la seccion "series" y marca "completo": true). Conserva las
secciones por pais (CA8) y anuales (CA176) ya incluidas.

----------------------------------------------------------------------------
DONDE PONGO MI TOKEN?  (elige UNA opcion)
  Opcion A - variable de entorno:
        Windows:  set BANXICO_TOKEN=tu_token_de_64_caracteres
        Mac/Linux: export BANXICO_TOKEN="tu_token_de_64_caracteres"
  Opcion B - archivo: crea un archivo llamado  token.txt  en esta misma carpeta
        y pega dentro SOLO tu token (una linea). El script lo lee solo.
  Opcion C - por linea de comandos:  python banxico_sie.py --token TU_TOKEN
  Si tu Windows/red bloquea la verificacion SSL de Banxico, usa temporalmente:
        python banxico_sie.py --insecure

Consigue el token gratis (~1 min): https://www.banxico.org.mx/SieAPIRest/service/v1/token
Luego:  pip install -r requirements.txt   &&   python banxico_sie.py
----------------------------------------------------------------------------
"""
from src.env import load_env

load_env()
import argparse
import json
import os
import sys
from datetime import datetime
import requests
import urllib3
from series_catalog import SERIES, todas_las_series

BASE = "https://www.banxico.org.mx/SieAPIRest/service/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "data", "comercio_exterior.json")
# Banxico can reject long multi-series URLs with HTTP 413, so keep batches small.
LOTE = 10


def leer_token(arg_token):
    if arg_token:
        return arg_token.strip()
    if os.environ.get("BANXICO_TOKEN"):
        return os.environ["BANXICO_TOKEN"].strip()
    tk = os.path.join(HERE, "token.txt")
    if os.path.exists(tk):
        with open(tk, encoding="utf-8") as f:
            return f.read().strip()
    return None


def _fecha(s):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s


def _num(v):
    if v in (None, "", "N/E", "NA"):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def descargar(token, ids=None, verify_ssl=True):
    ids = ids or todas_las_series()
    headers = {"Bmx-Token": token, "Accept": "application/json"}
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    porid = {}
    for i in range(0, len(ids), LOTE):
        lote = ids[i:i+LOTE]
        try:
            r = requests.get(
                f"{BASE}/series/{','.join(lote)}/datos",
                headers=headers,
                timeout=60,
                verify=verify_ssl,
            )
        except requests.exceptions.SSLError:
            sys.exit(
                "ERROR SSL: Python no pudo verificar el certificado de Banxico.\n"
                "Soluciones: actualiza/instala certificados de Windows/Python, revisa proxy o antivirus,\n"
                "o ejecuta temporalmente `python banxico_sie.py --insecure` solo en una red confiable."
            )
        if r.status_code in (400, 401) and "token" in r.text.lower() and "inv" in r.text.lower():
            sys.exit("ERROR: token invalido. Revisa tu BANXICO_TOKEN / token.txt.")
        if r.status_code == 413:
            sys.exit("ERROR 413: Banxico rechazo el lote por tamano. Reduce LOTE en banxico_sie.py.")
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            sys.exit(f"ERROR HTTP {r.status_code} al consultar Banxico: {r.text[:300]}")
        for s in r.json().get("bmx", {}).get("series", []):
            sid = s.get("idSerie")
            datos = [(_fecha(d["fecha"]), _num(d["dato"])) for d in s.get("datos", [])]
            porid[sid] = datos
    series = []
    for sid in ids:
        datos = porid.get(sid, [])
        if not datos:
            continue
        meta = SERIES.get(sid, {})
        series.append({"idSerie": sid, "nombre": meta.get("nombre", sid),
                       "flujo": meta.get("flujo", ""), "grupo": meta.get("grupo", ""),
                       "fechas": [d[0] for d in datos], "valores": [d[1] for d in datos]})
    return series


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token")
    ap.add_argument("--insecure", action="store_true",
                    help="Desactiva verificacion SSL solo si tu red/Windows bloquea los certificados de Banxico.")
    ap.add_argument("--export", action="store_true",
                    help="Tambien genera CSV/XLSX con las series mensuales.")
    args = ap.parse_args()
    token = leer_token(args.token)
    if not token:
        sys.exit("Falta el token. Ponlo en token.txt, en la variable BANXICO_TOKEN, o usa --token.\n"
                 "Token gratis: https://www.banxico.org.mx/SieAPIRest/service/v1/token")

    verify_ssl = not (args.insecure or os.environ.get("BANXICO_SSL_NO_VERIFY") == "1")
    if not verify_ssl:
        print("AVISO: verificacion SSL desactivada para esta descarga.")

    print("Descargando historia mensual completa desde el SIE...")
    series = descargar(token, verify_ssl=verify_ssl)

    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    data["series"] = series
    data["completo"] = True
    data["actualizado"] = datetime.now().strftime("%Y-%m-%d")
    data["fuente"] = ("Banco de Mexico - SIE (cuadros CE125, CA8, CA176). Historia mensual completa "
                      "via API REST. 100% datos oficiales, sin estimaciones.")
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    if args.export:
        import pandas as pd

        filas = [(fe, s["idSerie"], s["nombre"], s["flujo"], s["grupo"], va)
                 for s in series for fe, va in zip(s["fechas"], s["valores"])]
        df = pd.DataFrame(filas, columns=["fecha", "idSerie", "nombre", "flujo", "grupo", "valor_miles_usd"])
        df.to_csv(os.path.join(HERE, "data", "comercio_exterior.csv"), index=False, encoding="utf-8-sig")
        try:
            df.to_excel(os.path.join(HERE, "data", "comercio_exterior.xlsx"), sheet_name="Series", index=False)
        except Exception as e:
            print("Aviso Excel:", e)

    n = max((len(s["fechas"]) for s in series), default=0)
    print(f"OK. {len(series)} series, hasta {n} meses por serie. data/comercio_exterior.json actualizado (completo=True).")


if __name__ == "__main__":
    main()
