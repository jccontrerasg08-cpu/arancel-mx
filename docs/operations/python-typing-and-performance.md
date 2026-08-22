# Tipado gradual, rendimiento y atribución del ecosistema Python

## Propósito

Este proyecto usa Python y sus herramientas de tipado para mejorar la mantenibilidad de sus límites técnicos. Estas herramientas **no** certifican datos oficiales, clasificación, origen, RRNA, contribuciones ni pedimentos. Toda decisión de comercio exterior conserva sus fuentes, revisión y límites de producto propios.

## Tipado gradual

La CI usa Python 3.11 y ejecuta `python -m mypy src/arancel_mx`. El proyecto conserva una línea base temporal de hallazgos estrictos mediante `python -m scripts.check_type_error_budget`. La comprobación permite mantener o reducir los hallazgos ya revisados, pero bloquea cualquier aumento de los códigos `arg-type` y `attr-defined`.

| Código de mypy | Línea base inicial | Política |
|---|---:|---|
| `arg-type` | 33 | No puede aumentar; se reduce por módulo y con pruebas. |
| `attr-defined` | 3 | No puede aumentar; se reduce por módulo y con pruebas. |

Las reducciones deben empezar en las fronteras con mayor valor de contrato: `release`, `pipeline`, `benchmark` y `api`. No se eliminan exclusiones globales hasta que el módulo correspondiente quede tipado y su suite funcional esté aprobada.

Para evitar resultados distintos a CI, el desarrollo local de tipado debe usar el runtime y las restricciones declaradas por el repositorio. La instalación global del sistema puede contener stubs que no sean compatibles con Python 3.11.

## Rendimiento

`python/pyperformance` es una referencia para una fase futura, separada y no bloqueante. Antes de usarla se debe definir una línea base de hardware, versión de Python, sistema operativo, afinidad de CPU y cargas representativas de arancel-mx. Sus resultados sólo informarán regresiones técnicas de serialización, búsqueda o rutas HTTP; no determinan exactitud de datos ni criterios regulatorios.

## Atribución y reutilización responsable

La adopción actual reutiliza configuraciones, especificaciones públicas y prácticas, no código copiado de los repositorios citados. Si en el futuro se incorpora código de terceros, la solicitud de integración debe identificar archivo, versión, licencia, aviso de atribución y compatibilidad con la licencia Apache-2.0 de arancel-mx antes de su incorporación.

| Proyecto | Uso actual | Licencia o referencia | Límite |
|---|---|---|---|
| [mypy](https://github.com/python/mypy) | Dependencia de desarrollo y verificador estático. | [MIT y avisos del proyecto](https://github.com/python/mypy/blob/master/LICENSE). | No valida reglas de comercio exterior. |
| [CPython](https://github.com/python/cpython) | Runtime y biblioteca estándar de Python. | [PSF License](https://github.com/python/cpython/blob/main/LICENSE). | No se copia código del intérprete. |
| [typing](https://github.com/python/typing) | Especificación para anotaciones compatibles con Python 3.11. | [Especificación de typing](https://typing.python.org/en/latest/spec/meta.html). | Las anotaciones no validan datos en runtime. |
| [typeshed](https://github.com/python/typeshed) | Stubs indirectos usados por el verificador. | [Licencia y avisos](https://github.com/python/typeshed/blob/main/LICENSE). | No se incluyen stubs manualmente sin una necesidad reproducida. |
| [pyperformance](https://github.com/python/pyperformance) | Referencia para benchmarks futuros. | [MIT](https://github.com/python/pyperformance/blob/main/LICENSE). | No es un benchmark funcional ni regulatorio. |

## Referencias

[1]: https://mypy.readthedocs.io/en/stable/ "Documentación de mypy"
[2]: https://docs.python.org/3.11/library/typing.html "typing en Python 3.11"
[3]: https://pyperformance.readthedocs.io/ "Documentación de pyperformance"
[4]: https://github.com/python/devguide "Python Developer's Guide"
[5]: https://peps.python.org/ "Python Enhancement Proposals"
