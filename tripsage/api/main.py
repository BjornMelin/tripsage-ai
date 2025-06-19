"""TripSage FastAPI Application.

This module initializes and configures the FastAPI application for TripSage,
including middleware, routers, exception handlers, and startup/shutdown events.
"""

import logging
from contextlib import asynccontextmanager
# No typing imports needed - using Python 3.13 built-in types

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from tripsage.api.core.config import get_settings
from tripsage.api.core.openapi import custom_openapi
from tripsage.api.middlewares import (
    EnhancedRateLimitMiddleware,
    # AuthenticationMiddleware,  # Temporarily disabled - awaiting Supabase Auth
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
    dashboard_realtime,
    destinations,
    flights,
    health,
    itineraries,
    keys,
    memory,
    search,
    trips,
    users,
    websocket,
)
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreExternalAPIError,
    CoreKeyValidationError,
    CoreMCPError,
    CoreRateLimitError,
    CoreTripSageError,
    CoreValidationError,
)
from tripsage_core.services.infrastructure.key_monitoring_service import (
    KeyMonitoringService,
    KeyOperationRateLimitMiddleware,
)
from tripsage_core.services.infrastructure.websocket_broadcaster import (
    websocket_broadcaster,
)
from tripsage_core.services.infrastructure.websocket_manager import websocket_manager
from tripsage_core.services.mcp_service import mcp_manager

logger = logging.getLogger(__name__)


def format_error_response(exc: CoreTripSageError, request: Request) -> dict[str, str | bool]:
    """Format error response with simple, consistent structure.

    Modern approach - single error format for all consumers.
    """
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
    # Startup: Initialize MCP Manager and WebSocket Services
    logger.info("Initializing MCP Manager on API startup")
    await mcp_manager.initialize_all_enabled()

    available_mcps = mcp_manager.get_available_mcps()
    initialized_mcps = mcp_manager.get_initialized_mcps()
    logger.info(f"Available MCPs: {available_mcps}")
    logger.info(f"Initialized MCPs: {initialized_mcps}")

    # Initialize WebSocket Broadcaster first
    logger.info("Starting WebSocket Broadcaster")
    await websocket_broadcaster.start()

    # Initialize WebSocket Manager with broadcaster integration
    logger.info("Starting WebSocket Manager with broadcaster integration")
    websocket_manager.broadcaster = websocket_broadcaster
    await websocket_manager.start()

    yield  # Application runs here

    # Shutdown: Clean up resources (reverse order)
    logger.info("Stopping WebSocket Manager")
    await websocket_manager.stop()

    logger.info("Stopping WebSocket Broadcaster")
    await websocket_broadcaster.stop()

    logger.info("Shutting down MCP Manager")
    await mcp_manager.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        The configured FastAPI application
    """
    settings = get_settings()

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

    # Configure CORS with unified settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware (order matters - first added is last executed)
    # Logging middleware should be first to log all requests
    app.add_middleware(LoggingMiddleware)

    # Enhanced rate limiting middleware with security monitoring
    use_dragonfly = bool(settings.redis_url)
    app.add_middleware(
        EnhancedRateLimitMiddleware, settings=settings, use_dragonfly=use_dragonfly
    )

    # Enhanced authentication middleware supporting JWT and API keys
    # Temporarily disabled - awaiting Supabase Auth
    # app.add_middleware(AuthenticationMiddleware, settings=settings)

    # Add key operation rate limiting middleware
    key_monitoring_service = KeyMonitoringService(settings)
    app.add_middleware(
        KeyOperationRateLimitMiddleware,
        monitoring_service=key_monitoring_service,
    )

    # Simplified exception handlers
    @app.exception_handler(CoreAuthenticationError)
    async def authentication_error_handler(
        request: Request, exc: CoreAuthenticationError
    ):
        """Handle authentication errors."""
        logger.error(
            f"Authentication error: {exc.message}", extra={"path": request.url.path}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc, request),
        )

    @app.exception_handler(CoreKeyValidationError)
    async def key_validation_error_handler(
        request: Request, exc: CoreKeyValidationError
    ):
        """Handle API key validation errors."""
        logger.error(
            f"Key validation error: {exc.message}", extra={"path": request.url.path}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc, request),
        )

    @app.exception_handler(CoreRateLimitError)
    async def rate_limit_error_handler(request: Request, exc: CoreRateLimitError):
        """Handle rate limit errors."""
        logger.warning(
            f"Rate limit exceeded: {exc.message}", extra={"path": request.url.path}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc, request),
            headers={"Retry-After": "60"},
        )

    @app.exception_handler(CoreMCPError)
    async def mcp_error_handler(request: Request, exc: CoreMCPError):
        """Handle MCP server errors."""
        logger.error(f"MCP error: {exc.message}", extra={"path": request.url.path})
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc, request),
        )

    @app.exception_handler(CoreExternalAPIError)
    async def external_api_error_handler(request: Request, exc: CoreExternalAPIError):
        """Handle external API errors."""
        logger.error(
            f"External API error: {exc.message}", extra={"path": request.url.path}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc, request),
        )

    @app.exception_handler(CoreValidationError)
    async def validation_error_handler(request: Request, exc: CoreValidationError):
        """Handle validation errors."""
        logger.warning(
            f"Validation error: {exc.message}", extra={"path": request.url.path}
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=format_error_response(exc, request),
        )

    @app.exception_handler(CoreTripSageError)
    async def core_tripsage_error_handler(request: Request, exc: CoreTripSageError):
        """Handle all other core TripSage exceptions."""
        logger.error(f"Core error: {exc.message}", extra={"path": request.url.path})
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc, request),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
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
            f"Validation errors: {len(errors)}", extra={"path": request.url.path}
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
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions."""
        logger.warning(
            f"HTTP {exc.status_code}: {exc.detail}", extra={"path": request.url.path}
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
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other unhandled exceptions."""
        logger.exception(
            f"Unhandled exception: {exc}", extra={"path": request.url.path}
        )

        content = {
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
    app.include_router(websocket.router, prefix="/api", tags=["websocket"])

    app.include_router(users.router, prefix="/api/users", tags=["users"])
    app.include_router(config.router, prefix="/api", tags=["configuration"])
    app.include_router(dashboard.router, tags=["dashboard"])
    app.include_router(dashboard_realtime.router, tags=["dashboard-realtime"])

    # Set custom OpenAPI schema
    app.openapi = lambda: custom_openapi(app)

    logger.info(f"FastAPI application configured with {len(app.routes)} routes")
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "tripsage.api.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
