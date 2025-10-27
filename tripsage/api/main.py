"""TripSage FastAPI Application.

This module initializes and configures the FastAPI application for TripSage,
including middleware, routers, exception handlers, and startup/shutdown events.
"""

import logging
import os
import re
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from tripsage.api.core.config import Settings, get_settings
from tripsage.api.core.openapi import custom_openapi as build_openapi_schema
from tripsage.api.limiting import install_rate_limiting
from tripsage.api.middlewares import (
    LoggingMiddleware,
)
from tripsage.api.routers import (
    accommodations,
    activities,
    attachments,
    auth,
    chat,
    config,
    dashboard,
    destinations,
    flights,
    health,
    itineraries,
    keys,
    memory,
    search,
    trips,
    users,
)

# Removed ServiceRegistry: use direct lifespan-managed instances
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreExternalAPIError,
    CoreKeyValidationError,
    CoreRateLimitError,
    CoreTripSageError,
    CoreValidationError,
)
from tripsage_core.observability.otel import setup_otel
from tripsage_core.services.external_apis.google_maps_service import GoogleMapsService


logger: logging.Logger = logging.getLogger(__name__)


def format_error_response(exc: CoreTripSageError, _request: Request) -> dict[str, Any]:
    """Format error response with simple, consistent structure."""
    class_name = exc.__class__.__name__
    base_name = class_name.removeprefix("Core").removesuffix("Error")
    snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", base_name).lower()
    return {
        "error": True,
        "message": exc.message,
        "code": exc.code,
        "type": snake_case,
    }


def register_exception_handlers(app: FastAPI, settings: Settings) -> None:
    """Attach structured exception handlers to the FastAPI application."""

    async def authentication_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        error = cast(CoreAuthenticationError, exc)
        logger.exception("Authentication error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=error.status_code,
            content=format_error_response(error, request),
        )

    async def key_validation_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        error = cast(CoreKeyValidationError, exc)
        logger.exception("Key validation error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=error.status_code,
            content=format_error_response(error, request),
        )

    async def rate_limit_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        error = cast(CoreRateLimitError, exc)
        logger.warning(
            "Rate limit exceeded: %s",
            error.message,
            extra={"path": request.url.path},
        )
        additional_context = (
            getattr(getattr(error, "details", None), "additional_context", {}) or {}
        )
        retry_after = additional_context.get("retry_after", 60)
        return JSONResponse(
            status_code=error.status_code,
            content=format_error_response(error, request),
            headers={"Retry-After": str(retry_after)},
        )

    async def external_api_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        error = cast(CoreExternalAPIError, exc)
        logger.exception("External API error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=error.status_code,
            content=format_error_response(error, request),
        )

    async def validation_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        error = cast(CoreValidationError, exc)
        logger.warning(
            "Validation error: %s",
            error.message,
            extra={"path": request.url.path},
        )
        return JSONResponse(
            status_code=error.status_code,
            content=format_error_response(error, request),
        )

    async def core_tripsage_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        error = cast(CoreTripSageError, exc)
        logger.exception("Core error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=error.status_code,
            content=format_error_response(error, request),
        )

    async def request_validation_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        validation_error = cast(RequestValidationError, exc)
        errors = [
            {
                "field": ".".join(str(value) for value in error_detail["loc"]),
                "message": error_detail["msg"],
                "type": error_detail["type"],
            }
            for error_detail in validation_error.errors()
        ]

        logger.warning(
            "Validation errors: %s", len(errors), extra={"path": request.url.path}
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "message": "Request validation failed",
                "code": "VALIDATION_ERROR",
                "type": "validation",
                "errors": errors,
            },
        )

    async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        http_error = cast(StarletteHTTPException, exc)
        detail_value: Any = http_error.detail
        if isinstance(detail_value, str):
            message = detail_value or f"HTTP {http_error.status_code} error"
        elif detail_value is None:
            message = f"HTTP {http_error.status_code} error"
        else:
            message = str(detail_value)
        logger.warning(
            "HTTP %s: %s",
            http_error.status_code,
            message,
            extra={"path": request.url.path},
        )
        return JSONResponse(
            status_code=http_error.status_code,
            content={
                "error": True,
                "message": message,
                "code": f"HTTP_{http_error.status_code}",
                "type": "http",
            },
        )

    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception", extra={"path": request.url.path})

        content: dict[str, Any] = {
            "error": True,
            "message": "Internal server error",
            "code": "INTERNAL_ERROR",
            "type": "internal",
        }

        if settings.debug:
            content["debug"] = {
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            }

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=content,
        )

    app.add_exception_handler(CoreAuthenticationError, authentication_error_handler)
    app.add_exception_handler(CoreKeyValidationError, key_validation_error_handler)
    app.add_exception_handler(CoreRateLimitError, rate_limit_error_handler)
    app.add_exception_handler(CoreExternalAPIError, external_api_error_handler)
    app.add_exception_handler(CoreValidationError, validation_error_handler)
    app.add_exception_handler(CoreTripSageError, core_tripsage_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown events.

    Args:
        app: The FastAPI application
    """
    # Startup: Initialize MCP Manager and WebSocket Services
    logger.info("Initializing MCP service on API startup")
    from tripsage_core.services.airbnb_mcp import AirbnbMCP

    app.state.mcp_service = AirbnbMCP()
    await app.state.mcp_service.initialize()

    # Initialize services (Cache, WebSocket, MCP) in DI-managed app.state
    logger.info("Initializing Cache service")
    from tripsage_core.services.infrastructure.cache_service import CacheService

    app.state.cache_service = CacheService()
    await app.state.cache_service.connect()

    # Initialize Google Maps service (DI-managed singleton for API lifespan)
    logger.info("Initializing Google Maps service")
    app.state.google_maps_service = GoogleMapsService()
    await app.state.google_maps_service.connect()
    # Services are reachable via request.app.state*

    # Start database connection monitor for unified health reporting
    try:
        from tripsage_core.services.infrastructure.database_monitor import (
            DatabaseConnectionMonitor,
        )
        from tripsage_core.services.infrastructure.database_service import (
            get_database_service,
        )

        db_service = await get_database_service()
        app.state.database_monitor = DatabaseConnectionMonitor(
            database_service=db_service
        )
        await app.state.database_monitor.start_monitoring()
    except Exception:  # noqa: BLE001 - do not break startup if monitor fails
        logger.warning("DatabaseConnectionMonitor initialization failed", exc_info=True)

    yield  # Application runs here

    # Shutdown: Clean up resources (reverse order)

    database_monitor = getattr(app.state, "database_monitor", None)
    if database_monitor is not None:
        logger.info("Stopping database monitor")
        try:
            await database_monitor.stop_monitoring()
        except Exception:  # noqa: BLE001 - log and continue cleanup
            logger.warning("Failed to stop database monitor", exc_info=True)

    cache_service = getattr(app.state, "cache_service", None)
    if cache_service is not None:
        logger.info("Disconnecting Cache service")
        try:
            await cache_service.disconnect()
        except Exception:  # noqa: BLE001 - log and continue cleanup
            logger.warning("Failed to disconnect cache service", exc_info=True)

    google_maps_service = getattr(app.state, "google_maps_service", None)
    if google_maps_service is not None:
        logger.info("Closing Google Maps service")
        try:
            await google_maps_service.close()
        except Exception:  # noqa: BLE001 - log and continue cleanup
            logger.warning("Failed to close Google Maps service", exc_info=True)

    mcp_service = getattr(app.state, "mcp_service", None)
    if mcp_service is not None:
        logger.info("Shutting down MCP Manager")
        try:
            await mcp_service.shutdown()
        except Exception:  # noqa: BLE001 - log and continue cleanup
            logger.warning("Failed to shut down MCP Manager", exc_info=True)


def create_app() -> FastAPI:  # pylint: disable=too-many-statements
    """Create and configure the FastAPI application.

    Returns:
        The configured FastAPI application
    """
    settings = get_settings()

    # Initialize OpenTelemetry once using settings-driven flags (skip in testing).
    # Prevent duplicate server spans by preferring FastAPI instrumentation when both
    # toggles are enabled: we instrument FastAPI after app creation below, so pass
    # enable_fastapi=False here and disable ASGI if FastAPI instr is enabled.
    enable_asgi = settings.enable_asgi_instrumentation
    fastapi_instrument_app: Callable[[FastAPI], None] | None = None
    if settings.enable_fastapi_instrumentation:
        try:
            import importlib

            fastapi_module = importlib.import_module(
                "opentelemetry.instrumentation.fastapi"
            )
            instrumentor_cls = getattr(fastapi_module, "FastAPIInstrumentor", None)
        except ImportError:  # pragma: no cover - optional dep
            logger.warning(
                "FastAPI instrumentation unavailable; retaining ASGI instrumentation."
            )
        else:
            if instrumentor_cls is None:
                logger.warning(
                    "FastAPI instrumentation module missing FastAPIInstrumentor; "
                    "retaining ASGI instrumentation."
                )
            else:
                fastapi_instrument_app = cast(
                    Callable[[FastAPI], None],
                    instrumentor_cls().instrument_app,
                )
                if enable_asgi:
                    enable_asgi = False
                    logger.warning(
                        "FastAPI+ASGI instrumentation both enabled; disabling ASGI."
                    )

    if not settings.is_testing:
        setup_otel(
            service_name="tripsage-api",
            service_version=settings.api_version,
            environment=settings.environment,
            enable_fastapi=False,  # instrument FastAPI via instrument_app below
            enable_asgi=enable_asgi,
            enable_httpx=settings.enable_httpx_instrumentation,
            enable_redis=settings.enable_redis_instrumentation,
        )

    # Create FastAPI app with unified configuration
    app = FastAPI(
        title=settings.api_title,
        description="TripSage AI Travel Planning API",
        version=settings.api_version,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.state.settings = settings

    # Instrument FastAPI via instrument_app(app) after app creation
    if fastapi_instrument_app is not None:
        fastapi_instrument_app(app)

    # Add OTEL trace/span correlation to logs (root logger)
    try:
        from tripsage_core.observability.log_correlation import (
            install_trace_log_correlation as _install_trace_log_correlation,
        )

        _install_trace_log_correlation()
    except Exception:  # noqa: BLE001 - never break startup on logging issues
        logger.warning("Trace log correlation not installed")

    # Configure CORS with unified settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware (order matters - first added is last executed)
    # Logging middleware first to log all requests
    app.add_middleware(LoggingMiddleware)

    # Install SlowAPI-based inbound rate limiting
    install_rate_limiting(app, settings)

    # Authentication middleware supporting JWT and API keys
    # Temporarily disabled - awaiting Supabase Auth
    # app.add_middleware(AuthenticationMiddleware, settings=settings)

    # Inbound rate limiting handled via SlowAPI installed above

    register_exception_handlers(app, settings)

    # Include routers
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
    # dashboard_realtime router is temporarily excluded pending module finalization
    app.include_router(keys.router, prefix="/api/user/keys", tags=["api_keys"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(
        attachments.router, prefix="/api/attachments", tags=["attachments"]
    )
    app.include_router(trips.router, prefix="/api/trips", tags=["trips"])
    app.include_router(flights.router, prefix="/api/flights", tags=["flights"])
    app.include_router(
        accommodations.router,
        prefix="/api/accommodations",
        tags=["accommodations"],
    )
    app.include_router(
        destinations.router,
        prefix="/api/destinations",
        tags=["destinations"],
    )
    app.include_router(
        itineraries.router, prefix="/api/itineraries", tags=["itineraries"]
    )
    app.include_router(activities.router, prefix="/api/activities", tags=["activities"])
    app.include_router(search.router, prefix="/api/search", tags=["search"])
    app.include_router(memory.router, prefix="/api", tags=["memory"])
    app.include_router(users.router, prefix="/api/users", tags=["users"])
    app.include_router(config.router, prefix="/api", tags=["configuration"])

    # Set custom OpenAPI schema
    def generate_openapi_schema() -> dict[str, Any]:
        """Generate OpenAPI schema."""
        openapi_factory = cast(
            Callable[[FastAPI], dict[str, Any]], build_openapi_schema
        )
        return openapi_factory(app)

    app.openapi = generate_openapi_schema

    logger.info("FastAPI application configured with %s routes", len(app.routes))
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("TRIPSAGE_API_HOST", "127.0.0.1")
    port = int(os.getenv("TRIPSAGE_API_PORT", "8001"))
    reload = os.getenv("TRIPSAGE_API_RELOAD", "true").lower() == "true"

    uvicorn.run(
        "tripsage.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )
