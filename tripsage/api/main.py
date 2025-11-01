"""TripSage FastAPI Application.

This module initializes and configures the FastAPI application for TripSage,
including middleware, routers, exception handlers, and startup/shutdown events.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from tripsage.api.core.config import get_settings
from tripsage.api.core.openapi import custom_openapi
from tripsage.api.limiting import install_rate_limiting
from tripsage.api.middlewares import (
    LoggingMiddleware,
)
from tripsage.api.middlewares.authentication import AuthenticationMiddleware
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
    memory,
    search,
    trips,
    users,
)

# Removed ServiceRegistry: use direct lifespan-managed instances
from tripsage.app_state import initialise_app_state, shutdown_app_state
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreExternalAPIError,
    CoreKeyValidationError,
    CoreRateLimitError,
    CoreTripSageError,
    CoreValidationError,
)
from tripsage_core.observability.otel import setup_otel


logger: "logging.Logger" = logging.getLogger(__name__)  # pylint: disable=no-member


def format_error_response(exc: CoreTripSageError, request: Request) -> dict[str, Any]:
    """Format error response with simple, consistent structure."""
    return {
        "error": True,
        "message": exc.message,
        "code": exc.code,
        "type": exc.__class__.__name__.replace("Core", "").replace("Error", "").lower(),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown events.

    Args:
        app: The FastAPI application
    """
    services, orchestrator = await initialise_app_state(app)

    # Instantiate shared agents after services are ready
    from tripsage.agents.chat import ChatAgent

    app.state.chat_agent = ChatAgent(
        services=services,
        orchestrator=orchestrator,
    )

    # Start database connection monitor for unified health reporting
    database_monitor = None
    try:
        db_service = services.database_service
        if db_service is None:
            raise RuntimeError("Database service unavailable during startup")
        from tripsage_core.services.infrastructure.database_monitor import (
            DatabaseConnectionMonitor,
        )

        database_monitor = DatabaseConnectionMonitor(
            database_service=db_service,
        )
        await database_monitor.start_monitoring()
        app.state.database_monitor = database_monitor
    except Exception:  # noqa: BLE001 - non-critical
        logger.warning("DatabaseConnectionMonitor initialization failed")

    try:
        yield  # Application runs here
    finally:
        if database_monitor is not None:
            await database_monitor.stop_monitoring()
            if hasattr(app.state, "database_monitor"):
                delattr(app.state, "database_monitor")
        if hasattr(app.state, "chat_agent"):
            delattr(app.state, "chat_agent")
        await shutdown_app_state(app)


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
    enable_asgi = getattr(settings, "enable_asgi_instrumentation", False)
    if getattr(settings, "enable_fastapi_instrumentation", False) and enable_asgi:
        enable_asgi = False
        logger.warning("FastAPI+ASGI instrumentation both enabled; disabling ASGI.")

    if not settings.is_testing:
        setup_otel(
            service_name="tripsage-api",
            service_version=settings.api_version,
            environment=settings.environment,
            enable_fastapi=False,  # instrument FastAPI via instrument_app below
            enable_asgi=enable_asgi,
            enable_httpx=getattr(settings, "enable_httpx_instrumentation", False),
            enable_redis=getattr(settings, "enable_redis_instrumentation", False),
        )

    # Create FastAPI app with unified configuration
    app = FastAPI(
        title=settings.api_title,
        description="TripSage AI Travel Planning API",
        version=settings.api_version,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Instrument FastAPI via instrument_app(app) after app creation
    if getattr(settings, "enable_fastapi_instrumentation", False):
        try:
            import importlib

            fastapi_inst = importlib.import_module(
                "opentelemetry.instrumentation.fastapi"
            )
            fastapi_inst.FastAPIInstrumentor().instrument_app(app)
        except ImportError:  # pragma: no cover - optional dep
            pass

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

    # Authentication middleware enforcing Supabase JWT access tokens
    app.add_middleware(AuthenticationMiddleware, settings=settings)

    # Inbound rate limiting handled via SlowAPI installed above

    # Simplified exception handlers
    @app.exception_handler(CoreAuthenticationError)
    async def authentication_error_handler(  # type: ignore[reportUnusedFunction]
        request: Request, exc: CoreAuthenticationError
    ):
        """Handle authentication errors."""
        logger.exception("Authentication error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc, request),
        )

    @app.exception_handler(CoreKeyValidationError)
    async def key_validation_error_handler(  # type: ignore[reportUnusedFunction]
        request: Request, exc: CoreKeyValidationError
    ):
        """Handle API key validation errors."""
        logger.exception("Key validation error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc, request),
        )

    @app.exception_handler(CoreRateLimitError)
    async def rate_limit_error_handler(request: Request, exc: CoreRateLimitError):  # type: ignore[reportUnusedFunction]
        """Handle rate limit errors."""
        logger.warning(
            "Rate limit exceeded: %s", exc.message, extra={"path": request.url.path}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc, request),
            headers={"Retry-After": "60"},
        )

    # CoreMCPError removed; MCP integrations map to CoreExternalAPIError now

    @app.exception_handler(CoreExternalAPIError)
    async def external_api_error_handler(request: Request, exc: CoreExternalAPIError):  # type: ignore[reportUnusedFunction]
        """Handle external API errors."""
        logger.exception("External API error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc, request),
        )

    @app.exception_handler(CoreValidationError)
    async def validation_error_handler(request: Request, exc: CoreValidationError):  # type: ignore[reportUnusedFunction]
        """Handle validation errors."""
        logger.warning(
            "Validation error: %s", exc.message, extra={"path": request.url.path}
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=format_error_response(exc, request),
        )

    @app.exception_handler(CoreTripSageError)
    async def core_tripsage_error_handler(request: Request, exc: CoreTripSageError):  # type: ignore[reportUnusedFunction]
        """Handle all other core TripSage exceptions."""
        logger.exception("Core error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc, request),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(  # type: ignore[reportUnusedFunction]
        request: Request, exc: RequestValidationError
    ):
        """Handle FastAPI request validation errors."""
        errors = [
            {
                "field": ".".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
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

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):  # type: ignore[reportUnusedFunction]
        """Handle HTTP exceptions."""
        logger.warning(
            "HTTP %s: %s", exc.status_code, exc.detail, extra={"path": request.url.path}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail or f"HTTP {exc.status_code} error",
                "code": f"HTTP_{exc.status_code}",
                "type": "http",
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):  # type: ignore[reportUnusedFunction]
        """Handle all other unhandled exceptions."""
        logger.exception("Unhandled exception", extra={"path": request.url.path})

        content: dict[str, Any] = {
            "error": True,
            "message": "Internal server error",
            "code": "INTERNAL_ERROR",
            "type": "internal",
        }

        # Add debug info in development
        if settings.debug:
            content["debug"] = {
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            }

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=content,
        )

    # Include routers
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
    # dashboard_realtime router is temporarily excluded pending module finalization
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

    # BYOK key CRUD is now implemented in Next.js routes; Python router removed

    app.include_router(users.router, prefix="/api/users", tags=["users"])
    app.include_router(config.router, prefix="/api", tags=["configuration"])

    # Set custom OpenAPI schema
    app.openapi = lambda: custom_openapi(app)

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
