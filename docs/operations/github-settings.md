# Configuración de GitHub en producción

Este runbook es la lista de comprobación del mantenedor para la configuración del repositorio que no se puede imponer desde el código versionado. Define el límite de producción esperado de `arancel-mx`; **no** afirma que un ajuste esté activo hasta que un mantenedor lo verifique en la interfaz de GitHub.

El código del repositorio asume:

- el check estable `test` de GitHub Actions;
- permisos de workflow de sólo lectura por defecto, con escrituras limitadas al job que las necesita;
- releases de datos inmutables;
- la rama `main` protegida;
- GitHub Pages servido desde la rama `gh-pages`.

El workflow se muestra como `CI`, pero los rulesets de GitHub exigen el contexto que emite el check run, que es el nombre del job: `test`.

Los nombres de botones y opciones se citan en **negrita** tal como aparecen en la interfaz de GitHub, que está en inglés.

## 1. Permisos de Actions

Ruta en la interfaz: **Settings → Actions → General**.

1. Abre **Workflow permissions**.
2. Selecciona **Read repository contents and packages permissions** como permiso por defecto.
3. No cambies el valor por defecto del repositorio a lectura y escritura amplias. El workflow de producción concede escrituras sólo a los jobs que las necesitan.
4. **Allow GitHub Actions to create and approve pull requests** puede quedar activo para que la automatización de mantenimiento abra PRs.
5. Comprueba que ningún workflow del proyecto apruebe por sí mismo PRs de código o de datos. La revisión y el merge siguen la política normal de `main`.

Límite esperado del repositorio, idéntico a los bloques `permissions` de `.github/workflows/`:

```text
GITHUB_TOKEN por defecto (todos los workflows): contents read

CI / test: contents read
CI / fastapi-cloud-runtime: contents read
CI / browser-smoke: contents read

Official data pipeline / build-and-verify: contents read
Official data pipeline / publish: contents write + attestations write + id-token write + pages write
Official data pipeline / notify: contents read + issues write

Published bundle canary / verify-published-bundle: contents read

Publish Python package / validate-tag, build-once, external-certification-matrix: contents read
Publish Python package / publish-testpypi, publish-pypi: contents read + id-token write

Production certification / offline: contents read
Production certification / release-boundary: contents write
Production certification / issue-boundary: contents read + issues write
```

En `publish`, `contents: write` crea la release inmutable y actualiza la rama `gh-pages`, `attestations: write` e `id-token: write` firman la attestation SLSA y `pages: write` solicita el build de GitHub Pages. Cada escritura vive dentro del job que la necesita; ningún workflow concede permisos de escritura a nivel de workflow. El contrato se verifica offline en `tests/test_workflow_hardening.py`, de modo que un cambio que amplíe el alcance falla en `test` antes de llegar a `main`.

### Schedules

| Workflow | Cron (UTC) | Frecuencia |
|---|---|---|
| **Official data pipeline** (`official-data-pipeline.yml`) | `17 11 * * *` | Diario, 11:17 UTC. Sin cambios de fuente termina como `no_change`. |
| **Published bundle canary** (`published-bundle-canary.yml`) | `47 12 * * *` | Diario, 12:47 UTC, después del pipeline. |

GitHub deshabilita automáticamente los workflows programados de un repositorio público después de **60 días sin actividad** y avisa al mantenedor. Si un schedule deja de ejecutarse, revisa primero **Settings → Actions** y la pestaña **Actions** en busca del aviso de schedule deshabilitado antes de investigar el pipeline; reactivarlo es un paso manual. Las ejecuciones programadas no reinician ese reloj: hace falta un commit o un PR.

## 2. Inmutabilidad de releases

Ruta en la interfaz: **Settings → General → Releases**.

1. Localiza los controles de protección e inmutabilidad de releases.
2. Activa **Enable release immutability** antes de permitir la publicación autónoma desde `main`.
3. Confirma que ninguna release o tag `data-YYYY.MM.DD` existente está pensada para sobrescribirse. Un segundo cambio el mismo día debe fallar cerrado con `release_tag_collision` en lugar de mutar una release pública.

Este ajuste es requisito para tratar GitHub Releases como canal público e inmutable del dataset.

## 3. Ruleset de la rama `main`

Ruta en la interfaz: **Settings → Rules → Rulesets**.

Crea o edita el ruleset de producción con estos valores:

1. **Enforcement: Active**.
2. **Target: `main`**, o la rama por defecto del repositorio cuando resuelva a `main`.
3. Activa **Require a pull request before merging**.
4. Agrega el check de estado requerido **`test`**.
5. Source: **GitHub Actions**.
6. Activa **Require branches to be up to date before merging** para ese check.
7. Activa **Require conversation resolution before merging**.
8. Activa **Block force pushes**.
9. Activa **Block deletions**.
10. Activa **Require linear history** sólo cuando la estrategia squash-only de la sección siguiente esté activa.
11. No concedas a un workflow un bypass para publicar datos. El workflow de producción publica releases y la rama `gh-pages`; nunca escribe commits en `main`.

El check de estado requerido exacto es **`test`**. GitHub Actions emite ese contexto desde el job `test` de `.github/workflows/ci.yml`; el workflow se muestra como `CI`. Si GitHub pide elegir un check del historial reciente, selecciona `test` con GitHub Actions como origen.

## 4. Pull requests y merge

Ruta en la interfaz: **Settings → General → Pull Requests**.

Configura:

- **Squash merging: ON**.
- **Merge commits: OFF**.
- **Rebase merging: OFF**.
- **Automatically delete head branches: ON**.
- **Always suggest updating pull request branches: ON**.
- El auto-merge es opcional. Si se activa, úsalo sólo cuando `test` sea requerido y para PRs de mantenimiento ya revisados que cumplan el ruleset.

El merge squash-only mantiene `main` compatible con el historial lineal y evita que las ramas de automatización queden como ruido permanente.

## 5. Advanced Security

Ruta en la interfaz: **Settings → Advanced Security**.

Activa los controles disponibles para este repositorio público:

1. **Dependabot alerts: ON**.
2. **Dependabot security updates: ON**.
3. **Secret scanning: ON**, donde esté disponible.
4. **Push protection: ON**, donde esté disponible.
5. **Code scanning → Default setup: ON**, donde esté disponible.
6. **Private vulnerability reporting: ON**.

La configuración de Dependabot está versionada en `.github/dependabot.yml`; estos ajustes activan las capacidades de seguridad y alertas correspondientes donde GitHub las ofrece.

## 6. Orden de activación en producción

Sigue este orden antes de permitir que la publicación programada modifique GitHub Releases:

1. Confirma que `test` pasó sobre la implementación vigente.
2. Configura los permisos por defecto de Actions como sólo lectura.
3. Activa la inmutabilidad de releases.
4. Activa el merge squash-only.
5. Activa el ruleset de `main` y selecciona `test` de GitHub Actions como requerido.
6. Activa los controles de Advanced Security disponibles.
7. Ejecuta manualmente **Official data pipeline** con `publish=false` e inspecciona el resultado del build, `pipeline-result.json`, la procedencia del manifest y el artifact generado.
8. Sólo con el dry-run sano, permite una ejecución confiable en `main` con `publish=true` o la siguiente ejecución programada.
9. Después de la primera publicación, configura GitHub Pages (sección 7).

## 7. GitHub Pages

Ruta en la interfaz: **Settings → Pages**.

La rama `gh-pages` la crea la primera ejecución del job `publish` que llega al paso **Publish static data API to gh-pages**; antes de eso no aparece en el selector.

1. En **Build and deployment → Source**, selecciona **Deploy from a branch**.
2. En **Branch**, selecciona `gh-pages` y la carpeta `/ (root)`, y guarda.
3. Comprueba que `https://jccontrerasg08-cpu.github.io/arancel-mx/v1/meta.json` responde con el `dataset_tag` de la última release y que `https://arancel-mx.vercel.app/data/v1/meta.json` devuelve lo mismo a través del rewrite de Vercel.

El árbol incluye `.nojekyll`, así que Pages sirve los archivos sin procesarlos. Si Pages no está configurado, el job `publish` deja la advertencia `gh-pages updated, but the Pages build request failed` y la release sigue publicada; la API estática se actualiza en la siguiente publicación una vez configurado Pages.

## Lista de verificación

Marca cada punto sólo después de comprobarlo en la interfaz del repositorio.

- [ ] **Settings → Actions → General** usa **Read repository contents and packages permissions** por defecto.
- [ ] La creación de PRs por Actions se permite sólo si hace falta; ningún workflow aprueba por sí mismo un PR de código o de datos.
- [ ] **Settings → General → Releases** tiene **Enable release immutability** activo.
- [ ] **Settings → Rules → Rulesets** tiene un ruleset activo sobre `main`.
- [ ] El ruleset de `main` exige un pull request antes del merge.
- [ ] El check de estado requerido es exactamente **`test`**.
- [ ] El origen del check requerido es **GitHub Actions**.
- [ ] Las ramas deben estar actualizadas antes del merge.
- [ ] Se exige resolver las conversaciones.
- [ ] Los force pushes y el borrado de ramas están bloqueados.
- [ ] Se exige historial lineal, con el merge squash-only activo.
- [ ] Squash merging: ON.
- [ ] Merge commits: OFF.
- [ ] Rebase merging: OFF.
- [ ] Automatically delete head branches: ON.
- [ ] Always suggest updating pull request branches: ON.
- [ ] Dependabot alerts: ON.
- [ ] Dependabot security updates: ON.
- [ ] Secret scanning: ON, donde esté disponible.
- [ ] Push protection: ON, donde esté disponible.
- [ ] Code scanning → Default setup: ON, donde esté disponible.
- [ ] Private vulnerability reporting: ON.
- [ ] **Settings → Pages** publica desde la rama `gh-pages`, carpeta `/ (root)`.
- [ ] Un dry-run manual confiable con `publish=false` terminó sin mutar el repositorio, releases ni issues.
- [ ] Tras el primer ciclo en vivo sano, se verificaron en la ejecución del workflow la release o el `no_change`, la API estática en Pages y la recuperación de las alertas de automatización.

## Relacionado

- [Proceso de release](../release-process.md)
- [Arquitectura](../architecture.md)
- [Política de lint de seguridad](security-lint.md)
- [Certificación de producción](../production-certification.md)
