"""FastAPI application factory for the public read-only service."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import asynccontextmanager
import logging
import re
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from arancel_mx.api import API_VERSION
from arancel_mx.api.config import ApiSettings, load_settings
from arancel_mx.api.models import ErrorDetail, ErrorEnvelope
from arancel_mx.api.routes import router as service_router
from arancel_mx.consumer import Dataset
from arancel_mx.consumer.errors import (
    DatasetError,
    InvalidCodeError,
    QueryError,
    RecordNotFoundError,
)


logger = logging.getLogger(__name__)
DatasetLoader = Callable[[ApiSettings], Dataset]
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_API_DESCRIPTION = """
Public, read-only HTTP access to the verified `arancel-mx` dataset through the
versioned `/v1` contract.

The service is informational and is **not legal advice**. `search` and `suggest`
are retrieve-only helpers; this service **does not classify merchandise**. The API
does not expose dataset mutation, source capture, reconciliation, or publication
endpoints.
""".strip()


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


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build one sanitized error envelope without exposing exception details."""

    request_id = getattr(request.state, "request_id", None) or _request_id(None)
    payload = ErrorEnvelope(
        error=ErrorDetail(code=code, message=message, request_id=request_id)
    )
    response = JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
        headers=dict(headers) if headers is not None else None,
    )
    response.headers["X-Request-ID"] = request_id
    return response


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
        logger.info("loading verified dataset tag=%s", resolved_settings.dataset_tag)
        try:
            dataset = loader(resolved_settings)
        except Exception as exc:
            application.state.startup_error = exc.__class__.__name__
            logger.error(
                "dataset startup verification failed tag=%s error_type=%s",
                resolved_settings.dataset_tag,
                exc.__class__.__name__,
            )
            raise

        logger.info(
            "verified dataset ready tag=%s dataset_version=%s schema_version=%s",
            resolved_settings.dataset_tag,
            dataset.info.dataset_version,
            dataset.info.schema_version,
        )
        application.state.dataset = dataset
        application.state.ready = True
        try:
            yield
        finally:
            application.state.ready = False

    application = FastAPI(
        title="Arancel MX API",
        description=_API_DESCRIPTION,
        version=API_VERSION,
        license_info={"name": "Apache-2.0", "identifier": "Apache-2.0"},
        lifespan=lifespan,
    )
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

    @application.exception_handler(InvalidCodeError)
    async def invalid_code_handler(request: Request, exc: InvalidCodeError):
        return _error_response(
            request,
            status_code=400,
            code="invalid_code",
            message="Invalid tariff code.",
        )

    @application.exception_handler(RecordNotFoundError)
    async def record_not_found_handler(request: Request, exc: RecordNotFoundError):
        return _error_response(
            request,
            status_code=404,
            code="record_not_found",
            message="Tariff record not found.",
        )

    @application.exception_handler(QueryError)
    async def query_error_handler(request: Request, exc: QueryError):
        return _error_response(
            request,
            status_code=503,
            code="dataset_inconsistent",
            message="The verified dataset could not satisfy this query safely.",
        )

    @application.exception_handler(DatasetError)
    async def dataset_error_handler(request: Request, exc: DatasetError):
        return _error_response(
            request,
            status_code=503,
            code="dataset_unavailable",
            message="The verified dataset is unavailable.",
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return _error_response(
            request,
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            code = "route_not_found"
            message = "Route not found."
        elif exc.status_code == 405:
            code = "method_not_allowed"
            message = "Method not allowed."
        else:
            code = "http_error"
            message = "Request failed."
        return _error_response(
            request,
            status_code=exc.status_code,
            code=code,
            message=message,
            headers=exc.headers,
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None) or _request_id(None)
        logger.error(
            "unhandled API exception request_id=%s error_type=%s",
            request_id,
            exc.__class__.__name__,
        )
        return _error_response(
            request,
            status_code=500,
            code="internal_error",
            message="Internal server error.",
        )

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
