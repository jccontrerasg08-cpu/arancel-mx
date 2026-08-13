# Arquitectura de arancel-mx

`arancel-mx` organiza el ciclo de datos arancelarios en seis capas:

1. `sources` registra autoridades, descubre documentos permitidos y captura bytes con identidad verificable.
2. `parsers` transforma XLS, XLSX y PDF offline, conservando hoja, fila y evidencia original.
3. `domain` normaliza jerarquía, tasas, vigencia y procedencia sin inventar valores jurídicos.
4. `storage` instala únicamente el esquema DuckDB del dominio arancelario.
5. `pipeline` materializa, valida, reconcilia y compara actualizaciones.
6. `release` verifica hashes y prepara archivos locales para una publicación explícitamente aprobada.
7. `consumer` consulta un DuckDB público ya verificado (`lookup`, `ficha`, `compare`, …). No captura fuentes ni publica releases.

La última versión válida no se sustituye cuando falta evidencia, falla una validación o no coinciden los hashes. Consulta [data-model.md](data-model.md), [sources.md](sources.md), [consumer-cli.md](consumer-cli.md) y [release-process.md](release-process.md) para los contratos detallados.
