# API de Python

La API pública de Python es intencionalmente limitada durante la serie `0.x`.

La superficie mínima garantizada hoy es que el paquete puede importarse y reportar su versión:

```python
import arancel_mx

print(arancel_mx.__version__)
```

El CLI también puede invocarse mediante:

```bash
python -m arancel_mx --help
```

## Qué no se promete todavía

No se presenta como estable una API de búsqueda, clasificación automática ni navegación programática HS6 ↔ MX8 ↔ NICO10. Esas capacidades permanecen sujetas a evolución hasta que existan interfaces públicas, tests de compatibilidad y documentación específica.

Para consumo analítico actual, los artefactos CSV/JSON/DuckDB son un contrato más apropiado que importar módulos internos de `pipeline`, `sources`, `storage` o `release`.

Los módulos internos pueden cambiar durante `0.x` aunque estén visibles en el código fuente.
