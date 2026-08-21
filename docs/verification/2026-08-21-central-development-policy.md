# Verificación — política de desarrollo verificable del Central Hub

**Fecha:** 2026-08-21  
**Estado:** confirmado dentro del alcance de repositorio  
**Ámbito:** política compartida, índice documental, flujo de contribución y prueba de presencia en `arancel-mx`.

## Resultado observado

Se añadió `docs/governance/DEVELOPMENT_POLICY.md` como fuente canónica para los controles compartidos de Central Hub y RFA. El documento exige evidencia antes del cambio, reversibilidad, contratos versionados, fuente de datos única, mínimo privilegio, manejo de excepciones y clasificación documental. Se enlazó desde `docs/README.md` y `CONTRIBUTING.md`.

La prueba `tests/test_governance_policy.py` hace fallar la suite si la política desaparece, si faltan secciones de control esenciales o si se pierde el enlace desde el índice técnico o el flujo de contribución.

| Comprobación | Resultado observado | Cobertura |
|---|---|---|
| `python -m pytest -q tests/test_governance_policy.py` | `2 passed` | Presencia, secciones obligatorias y enlaces de política. |
| `python -m pytest -q` | `1044 passed` | Suite completa disponible en el árbol de trabajo. |
| `python -m ruff check src tests scripts` | `All checks passed!` | Calidad y reglas de seguridad integradas del repositorio. |
| `python -m ruff check --select S src scripts` | `All checks passed!` | Reglas de seguridad aplicadas a código y scripts. |
| `git diff --check` | Aprobado | Espacios en blanco y formato de la diferencia. |

## Límites

Esta verificación confirma la presencia, el contenido estructural y los enlaces de una política versionada en el repositorio. No confirma que colaboradores externos sigan la política, que los controles de GitHub estén habilitados en tiempo real, ni que un despliegue de Vercel haya cambiado; esta modificación no altera artefactos de producción.

## Reversión

La reversión es un `git revert` del commit que incorpora la política y su prueba. La acción eliminaría una salvaguarda de proceso, por lo que requeriría revisión explícita y una actualización del índice documental.
