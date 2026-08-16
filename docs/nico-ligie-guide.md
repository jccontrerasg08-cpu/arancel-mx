# NICO, fracción arancelaria y LIGIE: cómo leer datos verificables

La **LIGIE** establece la Tarifa de los Impuestos Generales de Importación y de Exportación y sus reglas de interpretación. En la estructura mexicana, una fracción arancelaria de 8 dígitos puede complementarse con un **NICO de 2 dígitos**, formando una identificación comercial de 10 dígitos. SNICE describe el NICO como un quinto par de dígitos añadido a la fracción arancelaria.[1]

> Esta guía explica una estructura de datos y una ruta de recuperación de evidencia. No es asesoría legal, no clasifica mercancías y no decide qué código corresponde a un producto concreto.

## Jerarquía de códigos

| Nivel | Longitud habitual | Ejemplo de forma | Uso de lectura |
|---|---:|---|---|
| Capítulo | 2 | `85` | Agrupación HS2. |
| Partida | 4 | `8517` | Agrupación HS4. |
| Subpartida | 6 | `851713` | Nivel internacional **HS6**. |
| Fracción | 8 | `85171301` | Fracción arancelaria de 8 dígitos en la tarifa mexicana. |
| NICO | 2 | `00` | NICO de 2 dígitos que aporta desagregación comercial. |
| Identificación comercial | 10 | `8517130100` | Combinación de fracción y NICO cuando existe en la release. |

La disponibilidad, vigencia y relación jerárquica se deben recuperar desde una release identificada; no se deben inferir a partir de la longitud del texto ni de un catálogo sin procedencia.

## Recuperar evidencia con una release fijada

Usa primero una release `data-YYYY.MM.DD`, no una referencia flotante. El ejemplo siguiente ilustra un flujo técnico; reemplaza el identificador por la release aprobada para tu proceso.

```bash
arancel-mx doctor --dataset data-2026.08.15
arancel-mx lookup 8517130100 --dataset data-2026.08.15 --format json
arancel-mx ficha 8517130100 --dataset data-2026.08.15
arancel-mx parent 8517130100 --dataset data-2026.08.15
arancel-mx provenance 8517130100 --dataset data-2026.08.15
```

En Python, el mismo patrón conserva la identidad de la release y evita depender de archivos locales no verificados:

```python
from arancel_mx import Dataset

catalog = Dataset.version("data-2026.08.15")
record = catalog.lookup("8517130100")
for source in catalog.provenance("8517130100"):
    print(source.source_document_id, source.source_url)
```

## Qué hacer cuando no existe una coincidencia

Un código que no aparece en una release no demuestra que el producto carezca de tratamiento legal ni autoriza a inventar una fracción. Revisa el contexto de la LIGIE, las Reglas Generales y Complementarias, las Notas Nacionales aplicables, y las fuentes oficiales pertinentes. Para una consulta interactiva oficial, usa el [Buscador de fracciones de VUCEM](https://www.ventanillaunica.gob.mx/vucem/Clasificador.html). Para localizar el texto publicado, usa el [DOF](https://www.dof.gob.mx/).

`search` y `suggest` ofrecen resultados retrieve-only. Son ayudas para recuperar evidencia documental dentro de la release y no sustituyen una clasificación humana respaldada por las fuentes aplicables.

## Referencias

[1]: https://www.snice.gob.mx/cs/avi/snice/nico.ligie.html "SNICE — NICO y LIGIE"
[2]: https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html "SNICE — LIGIE: Acerca de"
