"""A tiny PDF with the structure of the SE rules document: heading, annex 2.4.1 table, next annex."""

from functools import lru_cache

import pymupdf

ANNEX_FILENAME = "ACUERDO-REGLAS-SE-02ABRIL2026-BIBLIOTECA_20260520-20260520.pdf"
ANNEX_URL = f"https://www.snice.gob.mx/~oracle/SNICE_DOCS/{ANNEX_FILENAME}"
ANNEX_NOM = "NOM-EM-004-SAG/ZOO-2020"


@lru_cache(maxsize=1)
def annex_pdf_bytes() -> bytes:
    document = pymupdf.open()

    intro = document.new_page()
    intro.insert_text((91, 100), "Indice del acuerdo")

    heading = document.new_page()
    heading.insert_text((91, 80), "ANEXO 2.4.1")
    heading.insert_text((91, 100), "1.-")
    heading.insert_text((91, 130), "Fracción")
    heading.insert_text((91, 142), "arancelaria/N")
    heading.insert_text((130, 142), "ICO")
    heading.insert_text((161, 142), "Descripción")
    heading.insert_text((380, 142), "NOM")
    heading.draw_rect(pymupdf.Rect(375, 120, 376.2, 700), fill=(0, 0, 0))
    heading.insert_text((91, 180), "0101.21.01")
    heading.insert_text((161, 180), "Reproductores de raza pura")
    heading.insert_text((380, 180), ANNEX_NOM)

    following = document.new_page()
    following.insert_text((91, 80), "ANEXO 2.5.1")

    content = document.tobytes()
    document.close()
    return content
