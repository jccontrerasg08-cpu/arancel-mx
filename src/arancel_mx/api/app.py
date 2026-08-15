"""FastAPI application factory for the public read-only service."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
import re
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from arancel_mx.api.config import ApiSettings, load_settings
from arancel_mx.api.routes import router as service_router
from arancel_mx.consumer import Dataset


DatasetLoader = Callable[[ApiSettings], Dataset]
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _load_dataset(settings: ApiSettings) -> Dataset:
    """Resolve and verify the configured immutable dataset release."""

    return Dataset.version(
        settings.dataset_tag,
        cache_dir=settings.cache_dir,
        timeout=settings.timeout,
        offline=False,
    )


def _request_id(value: str | None) -> str:
    """Preserve a small safe caller ID or generate a local opaque ID."""

    if value is not None and _REQUEST_ID.fullmatch(value) is not None:
        return value
    return uuid4().hex


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
        application.state.settings = resolved_settings
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
    application.state.settings = None
    application.state.ready = False
    application.state.startup_error = None

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = _request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    application.include_router(service_router)

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
