"""Persistence for normalized tariff data."""

from .duckdb import connect, ensure_tariff_schema, init_tariff_db

__all__ = ["connect", "ensure_tariff_schema", "init_tariff_db"]
