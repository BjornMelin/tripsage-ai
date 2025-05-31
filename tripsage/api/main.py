"""TripSage FastAPI Application.

This module initializes and configures the FastAPI application for TripSage,
including middleware, routers, exception handlers, and startup/shutdown events.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from tripsage.api.core.config import get_settings
from tripsage.api.core.openapi import custom_openapi
from tripsage.api.middlewares.auth import AuthMiddleware
from tripsage.api.middlewares.logging import LoggingMiddleware
from tripsage.api.middlewares.rate_limit import RateLimitMiddleware
from tripsage.api.routers import (
    accommodations,
    attachments,
    auth,
    chat,
    destinations,
    flights,
    health,
    # itineraries,  # Temporarily disabled due to model recursion issues
    keys,
    memory,
    trips,
    websocket,
)
from tripsage.mcp_abstraction import mcp_manager
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
from tripsage_core.services.infrastructure.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown events.

    Args:
        app: The FastAPI application
    """
    # Startup: Initialize MCP Manager and WebSocket Manager
    logger.info("Initializing MCP Manager on API startup")
    await mcp_manager.initialize_all_enabled()

    available_mcps = mcp_manager.get_available_mcps()
    initialized_mcps = mcp_manager.get_initialized_mcps()
    logger.info(f"Available MCPs: {available_mcps}")
    logger.info(f"Initialized MCPs: {initialized_mcps}")

    # Initialize WebSocket Manager
    logger.info("Starting WebSocket Manager")
    await websocket_manager.start()

    yield  # Application runs here

    # Shutdown: Clean up resources
    logger.info("Stopping WebSocket Manager")
    await websocket_manager.stop()

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
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        docs_url="/api/docs" if settings.environment != "production" else None,
        redoc_url="/api/redoc" if settings.environment != "production" else None,
        openapi_url="/api/openapi.json"
        if settings.environment != "production"
        else None,
        lifespan=lifespan,
    )

    # Configure CORS
    cors_config = settings.get_cors_config()
    app.add_middleware(
        CORSMiddleware,
        **cors_config,
    )

    # Add custom middleware (order matters - first added is last executed)
    # Logging middleware should be first to log all requests
    app.add_middleware(LoggingMiddleware)

    # Rate limiting middleware
    use_dragonfly = bool(settings.dragonfly.url)
    app.add_middleware(
        RateLimitMiddleware, settings=settings, use_dragonfly=use_dragonfly
    )

    # Authentication middleware
    app.add_middleware(AuthMiddleware, settings=settings)

    # Add key operation rate limiting middleware
    key_monitoring_service = KeyMonitoringService(settings)
    app.add_middleware(
        KeyOperationRateLimitMiddleware, monitoring_service=key_monitoring_service
    )

    # Add exception handlers for detailed agent API error responses
    @app.exception_handler(CoreAuthenticationError)
    async def authentication_error_handler(
        request: Request, exc: CoreAuthenticationError
    ):
        """Handle authentication errors with detailed agent context."""
        logger.error(
            f"Authentication error: {exc.message}",
            extra={
                "error_code": exc.code,
                "status_code": exc.status_code,
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
                "user_id": exc.details.user_id,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.code,
                "error_type": "authentication",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_guidance": (
                    "Check your authentication credentials and ensure they are valid"
                ),
            },
        )

    @app.exception_handler(CoreKeyValidationError)
    async def key_validation_error_handler(
        request: Request, exc: CoreKeyValidationError
    ):
        """Handle API key validation errors with service-specific guidance."""
        logger.error(
            f"API key validation error: {exc.message}",
            extra={
                "error_code": exc.code,
                "service": exc.details.service,
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.code,
                "error_type": "key_validation",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_guidance": (
                    f"Verify your {exc.details.service} API key is correct and has "
                    "required permissions"
                ),
            },
        )

    @app.exception_handler(CoreRateLimitError)
    async def rate_limit_error_handler(request: Request, exc: CoreRateLimitError):
        """Handle rate limit errors with retry information."""
        retry_after = exc.details.additional_context.get("retry_after", 60)
        logger.warning(
            f"Rate limit exceeded: {exc.message}",
            extra={
                "error_code": exc.code,
                "retry_after": retry_after,
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.code,
                "error_type": "rate_limit",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_after": retry_after,
                "retry_guidance": (
                    f"Wait {retry_after} seconds before making another request"
                ),
            },
            headers={"Retry-After": str(retry_after)},
        )

    @app.exception_handler(CoreMCPError)
    async def mcp_error_handler(request: Request, exc: CoreMCPError):
        """Handle MCP server errors with tool-specific context."""
        logger.error(
            f"MCP error: {exc.message}",
            extra={
                "error_code": exc.code,
                "service": exc.details.service,
                "tool": exc.details.additional_context.get("tool"),
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.code,
                "error_type": "mcp_service",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_guidance": (
                    "The external service is temporarily unavailable. "
                    "Try again in a few moments"
                ),
            },
        )

    @app.exception_handler(CoreExternalAPIError)
    async def external_api_error_handler(request: Request, exc: CoreExternalAPIError):
        """Handle external API errors with service context."""
        logger.error(
            f"External API error: {exc.message}",
            extra={
                "error_code": exc.code,
                "service": exc.details.service,
                "api_status_code": exc.details.additional_context.get(
                    "api_status_code"
                ),
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.code,
                "error_type": "external_api",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_guidance": (
                    "External service error. Check service status and try again"
                ),
            },
        )

    @app.exception_handler(CoreValidationError)
    async def validation_error_handler(request: Request, exc: CoreValidationError):
        """Handle validation errors with field-specific context."""
        logger.warning(
            f"Validation error: {exc.message}",
            extra={
                "error_code": exc.code,
                "field": exc.details.additional_context.get("field"),
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,  # Use 400 for validation errors
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.code,
                "error_type": "validation",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_guidance": (
                    "Check the request parameters and ensure they meet the "
                    "required format"
                ),
            },
        )

    @app.exception_handler(CoreTripSageError)
    async def core_tripsage_error_handler(request: Request, exc: CoreTripSageError):
        """Handle all other core TripSage exceptions."""
        logger.error(
            f"Core TripSage error: {exc.message}",
            extra={
                "error_code": exc.code,
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
                "error_code": exc.code,
                "error_type": "tripsage_error",
                "details": exc.details.model_dump(exclude_none=True),
                "retry_guidance": (
                    "An error occurred. Please check your request and try again"
                ),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle FastAPI request validation errors."""
        error_details = []
        for error in exc.errors():
            error_details.append(
                {
                    "field": ".".join(str(x) for x in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                    "input": error.get("input"),
                }
            )

        logger.warning(
            f"Request validation error: {len(error_details)} validation errors",
            extra={
                "errors": error_details,
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "message": "Request validation failed",
                "error_code": "REQUEST_VALIDATION_ERROR",
                "error_type": "validation",
                "details": {
                    "validation_errors": error_details,
                },
                "retry_guidance": (
                    "Check the request format and ensure all required fields are "
                    "provided correctly"
                ),
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
                "error_code": f"HTTP_{exc.status_code}",
                "error_type": "http",
                "details": {},
                "retry_guidance": "Check the request URL and method",
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other unhandled exceptions."""
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
                "error_code": "INTERNAL_ERROR",
                "error_type": "system",
                "details": {
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc)
                    if settings.debug
                    else "Internal error occurred",
                },
                "retry_guidance": (
                    "An unexpected error occurred. Please try again or contact support"
                ),
            },
        )

    # Include routers
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(keys.router, prefix="/api/user/keys", tags=["api_keys"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
    app.include_router(
        attachments.router, prefix="/api/attachments", tags=["attachments"]
    )
    app.include_router(trips.router, prefix="/api/trips", tags=["trips"])
    app.include_router(flights.router, prefix="/api/flights", tags=["flights"])
    app.include_router(
        accommodations.router, prefix="/api/accommodations", tags=["accommodations"]
    )
    app.include_router(
        destinations.router, prefix="/api/destinations", tags=["destinations"]
    )
    # app.include_router(
    #     itineraries.router, prefix="/api/itineraries", tags=["itineraries"]
    # )  # Temporarily disabled
    app.include_router(memory.router, prefix="/api", tags=["memory"])
    app.include_router(websocket.router, prefix="/api", tags=["websocket"])

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
        port=8001,
        reload=True,
    )
