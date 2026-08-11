# CLI

El CLI público actual se expone como `arancel-mx` y como módulo `python -m arancel_mx`. Durante la serie 0.x el contrato estable es deliberadamente pequeño.

```bash
python -m arancel_mx --help
```

## `build`

Exporta artefactos desde una base DuckDB que ya fue validada:

```bash
python -m arancel_mx build \
  --database data/arancel.duckdb \
  --output-dir out/release
```

No sustituye la captura/reconciliación del pipeline oficial.

## `check-updates`

Comprueba el estado del ledger oficial registrado sin aceptar silenciosamente un nuevo estado:

```bash
python -m arancel_mx check-updates \
  --state-path data/update_state/ligie.json \
  --report-path out/update.json
```

Opcionalmente admite `--ledger-url`. `update` permanece sólo como alias obsoleto y read-only durante 0.x.

## `reconcile`

Reconcilia evidencia legal observada:

```bash
python -m arancel_mx reconcile \
  --ledger-json ledger.json \
  --dof-json dof.json \
  --snice-json snice.json
```

Una discrepancia material debe resolverse antes de considerar publicable un candidato.

## `release`

Verifica hashes y prepara el contrato local de publicación:

```bash
python -m arancel_mx release \
  --release-dir out/release \
  --source-dir data/raw/release \
  --latest-dir out/latest
```

La publicación automática real ocurre únicamente mediante el workflow de producción y sus gates.

## Códigos de salida

El CLI devuelve `0` para una ejecución aceptada. Errores de entrada, archivos ausentes, JSON inválido, errores HTTP manejados y validaciones de dominio retornan `2` con un mensaje en stderr.
