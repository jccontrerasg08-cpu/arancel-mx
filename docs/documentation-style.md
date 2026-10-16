# Guía de estilo de la documentación

Reglas para que toda la documentación se lea como un solo proyecto. Aplican a `README.md`, `docs/` y a los archivos de gobierno de la raíz.

## Idioma

- La documentación se escribe en **español**.
- Excepciones:
  - `README.en.md`, que es el espejo en inglés de la portada;
  - `CHANGELOG.md`, que sigue [Keep a Changelog](https://keepachangelog.com/) en inglés para el público de PyPI;
  - `opensource-checklist.md`, que adapta una plantilla pública en inglés;
  - `LICENSE` y `NOTICE`.
- Los nombres técnicos se quedan como están: comandos, rutas, campos, nombres de workflow, `fail-closed`, `no_change`, `release`.
- Los nombres de archivo usan inglés en `kebab-case` (`consumer-quickstart.md`), como el resto del repositorio.

## Estructura de cada documento

1. **Título `#`** en español, sin el nombre del proyecto si no aporta.
2. **Un párrafo inicial** que diga qué cubre el documento y para quién es.
3. **Secciones `##`** ordenadas de lo general a lo particular.
4. **Sección final `## Relacionado`** con dos a cinco enlaces relativos.

Los runbooks numeran sus pasos. Las referencias usan tablas. Los diagramas son bloques `text` con flechas `→` o `↓`.

## Contenido

- **Describe el estado actual.** Lo que ya ocurrió va en `CHANGELOG.md` o en una [decisión](decisions/0000-template.md); no se conservan planes terminados, bitácoras de sesión ni listas de pendientes en `docs/`.
- **Una idea, un lugar.** Cada contrato tiene un documento canónico y los demás lo enlazan en lugar de repetirlo:

  | Tema | Documento canónico |
  |---|---|
  | Arquitectura | [architecture.md](architecture.md) |
  | Consumo por archivos, Python y HTTP | [external-consumption.md](external-consumption.md) |
  | Pipeline y publicación | [release-process.md](release-process.md) |
  | Fuentes | [sources.md](sources.md) |
  | Compatibilidad | [compatibility.md](compatibility.md) |
- **Evidencia, no promesas.** No se escribe «100 % actualizado» ni «garantizado». Se nombra la release, el hash o la prueba.
- **Frontera legal.** Cuando un texto pueda leerse como consejo, se aclara que `arancel-mx` no clasifica mercancías ni constituye asesoría legal.
- **Componentes deprecados.** Se nombran sólo en [operations/v1-sunset.md](operations/v1-sunset.md), en la [política de compatibilidad](compatibility.md) y en las decisiones. Los demás documentos describen únicamente la arquitectura vigente.

## Pruebas

Varias pruebas (`tests/test_brand_presentation.py`, `tests/consumer/test_docs_contract.py`, `tests/test_public_distribution.py`, entre otras) verifican frases, enlaces y encabezados de la documentación. Si cambias un contrato documentado, cambia la prueba en el mismo PR y explica por qué.

## Relacionado

- [Centro de documentación](README.md)
- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [Plantilla de decisión](decisions/0000-template.md)
