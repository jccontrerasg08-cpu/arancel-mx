# HS, fracción mexicana y NICO

`arancel-mx` mantiene separados los niveles internacionales del Sistema Armonizado y las extensiones nacionales mexicanas.

```text
HS2
 ↓
HS4
 ↓
HS6
 ↓
fracción MX8
 ↓
NICO10
```

## HS2 / HS4 / HS6

Los primeros seis dígitos pertenecen a la jerarquía del Sistema Armonizado. `HS6` es el nivel internacional comparable entre países dentro de una misma versión HS.

## Fracción MX8

México extiende HS6 a una fracción arancelaria nacional de ocho dígitos. Una `fraccion8` debe conservar su padre HS6.

## NICO10

El NICO agrega dos dígitos a la fracción mexicana. Un `nico10` debe conservar:

```text
fraccion8
nico2
nico10
```

Un NICO no es equivalente a una extensión nacional de diez dígitos de otro país.

## Validaciones

El pipeline valida relaciones padre-hijo y bloquea registros huérfanos. También mantiene separados vigencia de clasificación y vigencia de tarifas, porque una descripción, un código o una tasa pueden cambiar en momentos distintos.
