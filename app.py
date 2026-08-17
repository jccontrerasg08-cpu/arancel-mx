"""Vercel entrypoint for the public FastAPI application."""

from arancel_mx.api.app import app

__all__ = ["app"]
