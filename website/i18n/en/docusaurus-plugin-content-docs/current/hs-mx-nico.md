# HS, Mexican tariff fraction, and NICO

`arancel-mx` keeps international Harmonized System levels separate from Mexican national extensions.

```text
HS2
 ↓
HS4
 ↓
HS6
 ↓
Mexican MX8 tariff fraction
 ↓
NICO10
```

## HS2 / HS4 / HS6

The first six digits belong to the Harmonized System hierarchy. `HS6` is the internationally comparable level within the same HS version.

## Mexican MX8 tariff fraction

Mexico extends HS6 to an eight-digit national tariff fraction. A `fraccion8` must preserve its HS6 parent.

## NICO10

NICO adds two digits to the Mexican tariff fraction. A `nico10` preserves:

```text
fraccion8
nico2
nico10
```

A NICO is not equivalent to another country's ten-digit national extension.

## Validation

The pipeline validates parent-child relationships and blocks orphaned records. It also keeps classification validity separate from tariff-rate validity because a description, code, or rate may change at different times.
