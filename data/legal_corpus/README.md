# Corpus documental para el asistente

Coloca aqui documentos en `.md`, `.markdown`, `.txt`, `.csv`, `.tsv`, `.json` o `.jsonl` para que el asistente Groq los use como referencia local.

Archivos base incluidos:

- `operacion-comex-base.md`: datos minimos, formato de respuesta y checklist operativo.
- `fuentes-oficiales-comex-mx.md`: indice de fuentes oficiales para LIGIE/TIGIE-NICO, NOMs, tratados, DOF, SAT, ANAM, VUCEM y SNICE.
- `casos-tipo-comex.md`: plantillas anonimizadas para few-shot por recuperacion.
- `requisitos-pais-ejemplo.csv`: ejemplo de matriz tabular recuperable.

Sugerencia de archivos propios:

- `ley-aduanera.md`
- `reglamento-ley-aduanera.md`
- `rgce-2026.md`
- `anexo-22.md`
- `tigie-nico-notas.md`
- `noms-comercio-exterior.md`
- `criterios-anam-sat.md`

Formato recomendado:

```md
# Ley Aduanera

## Articulo 36

Texto...

## Articulo 36-A

Texto...
```

Comandos utiles:

```bash
python comex.py legal-corpus-status
python comex.py legal-corpus-search "identificador del Anexo 22 para NOM"
python comex.py rag-search "requisitos exportacion Estados Unidos Incoterm"
python comex.py rag-audit
```

El dashboard recupera automaticamente fragmentos relevantes de estos archivos para cada pregunta del asistente.
Ejecuta `rag-audit` cuando agregues documentos externos; alerta patrones tipo prompt injection, exfiltracion, secretos o ejecucion de codigo.

PDFs, Office e imagenes: por ahora extrae el texto o tabla a Markdown/CSV/JSON y guardalo aqui. Agrega RAG-Anything/MinerU solo cuando necesites parsing multimodal real.

Para casos reales, agrega 20-50 ejemplos anonimizados con este formato:

```md
## Caso: nombre corto

Entrada:
- ...

Respuesta esperada:
- ...

Decision / criterio:
- ...
```
