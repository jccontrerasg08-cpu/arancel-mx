# Fuentes oficiales

## Dominios

- `diputados.gob.mx`: ledger de la LIGIE, texto vigente, reformas y documentos asociados.
- `dof.gob.mx`: evidencia oficial de publicación y vigencia.
- `snice.gob.mx`: libros operativos de LIGIE, NICO y modificaciones publicados por la Secretaría de Economía.

## Registro versionado

`src/arancel_mx/sources/source_registry.json` define por conjunto: clave, versión del registro, página canónica, papel de la fuente, autoridad jurídica, autoridad de descubrimiento, texto consolidado, fecha efectiva y reglas de clasificación.

Cambiar el registro requiere revisión porque modifica qué documentos pueden entrar al pipeline.

## Lista permitida y descubrimiento

Los adaptadores aceptan únicamente hosts oficiales y clasifican enlaces según el registro. Redirecciones, extensiones inesperadas, páginas auxiliares y enlaces fuera de dominio no se convierten automáticamente en fuentes legales.

## Identidad de captura

Una captura registra URL final, SHA-256, tamaño, tipo de medio, fecha de recuperación y procedencia. Un parseo sólo puede reutilizarse cuando coinciden el hash de fuente y las versiones de parser, esquema y registro.

## Prioridad

La publicación jurídica y el texto legal tienen prioridad para vigencia; los libros operativos aportan estructura utilizable. Una discrepancia se conserva y bloquea la publicación en lugar de resolverse silenciosamente.

## Fixtures offline

Las pruebas usan fragmentos mínimos y sanitizados en `tests/fixtures/`. No hacen solicitudes de red. Cada cambio de parser debe incluir un fixture reproducible o una construcción sintética equivalente.

