"""TripSage FastAPI Application.

This module initializes and configures the FastAPI application for TripSage,
including middleware, routers, exception handlers, and startup/shutdown events.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from tripsage.api.core.config import get_settings
from tripsage.api.core.exceptions import TripSageException
from tripsage.api.core.openapi import custom_openapi
from tripsage.api.middlewares.auth import AuthMiddleware
from tripsage.api.middlewares.logging import LoggingMiddleware
from tripsage.api.middlewares.rate_limit import RateLimitMiddleware
from tripsage.api.routers import (
    accommodations,
    auth,
    chat,
    destinations,
    flights,
    health,
    itineraries,
    keys,
    memory,
    trips,
)
from tripsage.api.services.key_monitoring import (
    KeyMonitoringService,
    KeyOperationRateLimitMiddleware,
)
from tripsage.mcp_abstraction import mcp_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown events.

    Args:
        app: The FastAPI application
    """
    # Startup: Initialize MCP Manager and other resources
    logger.info("Initializing MCP Manager on API startup")
    await mcp_manager.initialize_all_enabled()

    available_mcps = mcp_manager.get_available_mcps()
    initialized_mcps = mcp_manager.get_initialized_mcps()
    logger.info(f"Available MCPs: {available_mcps}")
    logger.info(f"Initialized MCPs: {initialized_mcps}")

    yield  # Application runs here

    # Shutdown: Clean up resources
    logger.info("Shutting down MCP Manager")
    await mcp_manager.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        The configured FastAPI application
    """
    settings = get_settings()

    # Create FastAPI app with OpenAPI configuration
    app = FastAPI(
        title="TripSage API",
        description="TripSage Travel Planning API",
        version="1.0.0",
        docs_url="/api/docs" if settings.environment != "production" else None,
        redoc_url="/api/redoc" if settings.environment != "production" else None,
        openapi_url="/api/openapi.json"
        if settings.environment != "production"
        else None,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware (order matters - first added is last executed)
    # Logging middleware should be first to log all requests
    app.add_middleware(LoggingMiddleware)

    # Rate limiting middleware
    use_redis = bool(settings.redis_url)
    app.add_middleware(RateLimitMiddleware, settings=settings, use_redis=use_redis)

    # Authentication middleware
    app.add_middleware(AuthMiddleware, settings=settings)

    # Add key operation rate limiting middleware
    key_monitoring_service = KeyMonitoringService(settings)
    app.add_middleware(
        KeyOperationRateLimitMiddleware, monitoring_service=key_monitoring_service
    )

    # Add exception handlers
    @app.exception_handler(TripSageException)
    async def tripsage_exception_handler(request: Request, exc: TripSageException):
        """Handle TripSage custom exceptions."""
        logger.error(
            f"TripSage exception: {exc.message}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions."""
        logger.warning(
            f"HTTP exception: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.detail,
                "error_code": f"http_{exc.status_code}",
                "details": {},
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions."""
        logger.exception(
            f"Unhandled exception: {str(exc)}",
            extra={
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
                "exception_type": type(exc).__name__,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Internal server error",
                "error_code": "internal_error",
                "details": {"type": type(exc).__name__} if settings.debug else {},
            },
        )

    # Include routers
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(keys.router, prefix="/api/user/keys", tags=["api_keys"])
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
    app.include_router(trips.router, prefix="/api/trips", tags=["trips"])
    app.include_router(flights.router, prefix="/api/flights", tags=["flights"])
    app.include_router(
        accommodations.router, prefix="/api/accommodations", tags=["accommodations"]
    )
    app.include_router(
        destinations.router, prefix="/api/destinations", tags=["destinations"]
    )
    app.include_router(
        itineraries.router, prefix="/api/itineraries", tags=["itineraries"]
    )
    app.include_router(memory.router, prefix="/api", tags=["memory"])

    # TODO: Include additional routers as they are implemented
    # app.include_router(users.router, prefix="/api/users", tags=["users"])

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
        port=8000,
        reload=True,
    )
