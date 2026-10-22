# Política de lint de seguridad

Este documento describe cómo `arancel-mx` revisa la seguridad del código en cada cambio y qué excepciones están aprobadas. Está dirigido a contribuyentes y mantenedores que agregan código en `src/`, `scripts/` o `tests/`.

## Regla general

`arancel-mx` ejecuta las reglas `S` de Ruff, compatibles con Bandit, como parte del lint estándar. Así la revisión de seguridad vive en el mismo check requerido de CI que la sintaxis y la corrección, en lugar de depender de un escaneo manual ocasional. La selección de reglas está en `[tool.ruff.lint]` de `pyproject.toml`.

## Línea base

El comando obligatorio es:

```bash
python -m ruff check src tests scripts
```

Los módulos de producción en `src/` y los scripts operativos en `scripts/` no pueden tener hallazgos `S` sin revisar. CI ejecuta este mismo comando en el job `test`, de modo que un hallazgo nuevo hace fallar el check hasta que se corrige o recibe una supresión acotada y revisada.

## Excepciones revisadas

Estas excepciones son deliberadamente limitadas y se revisan cuando cambia el código afectado.

| Regla | Ubicación | Motivo |
|---|---|---|
| `S310` | `consumer/wco_support.py` | La URL de descarga de la OMA se construye sólo con la URL base HTTPS fija del paquete y un capítulo validado por rango o un nombre de archivo fijo. Se comprueba que la respuesta sea PDF antes de entrar de forma atómica a la caché local. |
| `S603` | `scripts/certify_package_install.py` | El script de certificación invoca sólo un entorno virtual temporal aislado, una distribución local verificada y rutas de sondeo locales al repositorio, después de validar todas las entradas. |
| `S603` | `scripts/certify_testpypi_candidate.py` | Usa un intérprete fijo y argumentos fijos de índice de paquetes o de metadatos instalados de confianza. |
| `S603` | `scripts/dependency_compatibility_probe.py` | La sonda ejecuta comandos sólo dentro de su entorno virtual temporal, con rutas validadas de distribución, dataset y repositorio. |
| `S608` | `pipeline/build.py` | El SQL dinámico usa allowlists estáticas de tablas internas, un contrato fijo de columnas públicas o una constante fija de orden de exportación. No se interpolan identificadores provistos por usuarios. |
| `S101`, `S105`, `S107`, `S603`, `S607`, `S108` | `tests/**/*.py` | Las aserciones de pytest, los tokens claramente sintéticos para probar la redacción de secretos y los fixtures controlados de procesos y rutas temporales son contratos de prueba, no comportamiento de producción. Esta excepción no cubre código de producción ni scripts. |

Cada supresión nueva `# noqa: S...` debe incluir su justificación en la misma línea y agregarse a esta tabla. Cuando sea práctico, se prefiere un cambio de código que elimine el hallazgo.

## Revisión del mantenedor

Antes de fusionar un cambio relacionado con seguridad, ejecuta el lint estándar, el lint enfocado en seguridad y las pruebas relevantes:

```bash
python -m ruff check src tests scripts
python -m ruff check --select S src scripts
python -m pytest -q
```

Los hallazgos de Dependabot, code scanning y secret scanning dependen de la configuración del repositorio, no del código versionado. Los mantenedores mantienen esos controles activos y revisan sus colas de alertas según la [configuración de GitHub](github-settings.md#5-advanced-security).

## Relacionado

- [Configuración de GitHub](github-settings.md)
- [Tipado gradual y rendimiento](python-typing-and-performance.md)
- [SECURITY.md](../../SECURITY.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
