"""FastAPI application factory for the public read-only service."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from arancel_mx.api.config import ApiSettings, load_settings
from arancel_mx.consumer import Dataset


DatasetLoader = Callable[[ApiSettings], Dataset]


def _load_dataset(settings: ApiSettings) -> Dataset:
    """Resolve and verify the configured immutable dataset release."""

    return Dataset.version(
        settings.dataset_tag,
        cache_dir=settings.cache_dir,
        timeout=settings.timeout,
        offline=False,
    )


def create_app(
    *,
    settings: ApiSettings | None = None,
    dataset_loader: DatasetLoader | None = None,
) -> FastAPI:
    """Create an import-safe app whose dataset is loaded only during lifespan."""

    loader = dataset_loader or _load_dataset

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.ready = False
        application.state.startup_error = None
        resolved_settings = settings if settings is not None else load_settings()
        try:
            dataset = loader(resolved_settings)
        except Exception as exc:
            application.state.startup_error = exc.__class__.__name__
            raise

        application.state.dataset = dataset
        application.state.ready = True
        try:
            yield
        finally:
            application.state.ready = False

    application = FastAPI(title="Arancel MX API", lifespan=lifespan)
    application.state.dataset = None
    application.state.ready = False
    application.state.startup_error = None

    @application.get("/readyz")
    def readiness():
        dataset = application.state.dataset
        if not application.state.ready or dataset is None:
            return JSONResponse({"status": "not_ready"}, status_code=503)
        return {
            "status": "ready",
            "dataset_version": dataset.info.dataset_version,
        }

    return application


app = create_app()
