"""TripSage FastAPI Application.

This module initializes and configures the FastAPI application for TripSage,
including middleware, routers, exception handlers, and startup/shutdown events.
"""

import logging
import traceback
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from tripsage.api.core.config import get_settings
from tripsage.api.core.openapi import custom_openapi
from tripsage.api.middlewares import (
    AuthenticationMiddleware,
    EnhancedRateLimitMiddleware,
    LoggingMiddleware,
)
from tripsage.api.routers import (
    accommodations,
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
    CoreAuthorizationError,
    CoreExternalAPIError,
    CoreKeyValidationError,
    CoreMCPError,
    CoreRateLimitError,
    CoreResourceNotFoundError,
    CoreTripSageError,
    CoreValidationError,
)
from tripsage_core.services.infrastructure.key_monitoring_service import (
    KeyMonitoringService,
    KeyOperationRateLimitMiddleware,
)

logger = logging.getLogger(__name__)


def format_error_response(
    exc: CoreTripSageError,
    request: Request,
    is_agent_request: bool = False,
) -> dict[str, Any]:
    """Format error response based on consumer type.

    Args:
        exc: The exception to format
        request: The request object
        is_agent_request: Whether this is an agent request needing detailed error data

    Returns:
        Formatted error response dictionary
    """
    # Base response structure
    response = {
        "status": "error",
        "message": exc.message,
        "error_code": exc.code,
        "error_type": exc.__class__.__name__.replace("Core", "")
        .replace("Error", "")
        .lower(),
    }

    # Add correlation ID if available
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        response["correlation_id"] = correlation_id

    # Format details based on consumer type
    if is_agent_request:
        # Agents get full error details for debugging
        response["details"] = exc.details.model_dump(exclude_none=True)
        response["status_code"] = exc.status_code
        response["traceback_hint"] = (
            f"{exc.__class__.__module__}.{exc.__class__.__name__}"
        )
    else:
        # Frontend gets user-friendly filtered details
        details = exc.details.model_dump(exclude_none=True)
        # Remove sensitive internal details for frontend
        filtered_details = {
            k: v
            for k, v in details.items()
            if k not in ["request_id", "operation", "additional_context"]
        }
        if filtered_details:
            response["details"] = filtered_details

    # Add retry guidance based on error type
    retry_guidance = {
        "authentication": "Please check your authentication credentials and try again",
        "key_validation": (
            f"Verify your {exc.details.service or 'API'} key is correct and has "
            "required permissions"
        ),
        "rate_limit": (
            f"Wait {exc.details.additional_context.get('retry_after', 60)} seconds "
            "before retrying"
        ),
        "mcp_service": (
            "The external service is temporarily unavailable. Please try again later"
        ),
        "external_api": "External service error. Check service status and try again",
        "validation": (
            "Check the request parameters and ensure they meet the required format"
        ),
        "resource_not_found": "The requested resource was not found",
        "authorization": "You don't have permission to access this resource",
        "database": "A database error occurred. Please try again later",
        "service": "An internal service error occurred. Please try again",
    }

    response["retry_guidance"] = retry_guidance.get(
        response["error_type"],
        "An error occurred. Please check your request and try again",
    )

    return response


def is_agent_request(request: Request) -> bool:
    """Determine if the request is from an agent based on headers or path.

    Args:
        request: The request object

    Returns:
        True if this appears to be an agent request
    """
    # Check for agent-specific headers
    user_agent = request.headers.get("user-agent", "").lower()
    if any(agent in user_agent for agent in ["agent", "bot", "ai", "llm"]):
        return True

    # Check for agent-specific accept headers
    accept = request.headers.get("accept", "").lower()
    if "application/vnd.api+json" in accept:  # JSON API format often used by agents
        return True

    # Check for X-Consumer-Type header
    consumer_type = request.headers.get("x-consumer-type", "").lower()
    if consumer_type in ["agent", "ai", "bot"]:
        return True

    # Check for specific API paths that agents typically use
    agent_paths = ["/api/v1/chat", "/api/agents", "/api/memory"]
    if any(request.url.path.startswith(path) for path in agent_paths):
        return True

    return False


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

    # Enhanced rate limiting middleware with principal-based limits
    use_dragonfly = bool(settings.dragonfly.url)
    app.add_middleware(
        EnhancedRateLimitMiddleware, settings=settings, use_dragonfly=use_dragonfly
    )

    # Enhanced authentication middleware supporting JWT and API keys
    app.add_middleware(AuthenticationMiddleware, settings=settings)

    # Add key operation rate limiting middleware
    key_monitoring_service = KeyMonitoringService(settings)
    app.add_middleware(
        KeyOperationRateLimitMiddleware, monitoring_service=key_monitoring_service,
    )

    # Add exception handlers for detailed agent API error responses
    @app.exception_handler(CoreAuthenticationError)
    async def authentication_error_handler(
        request: Request, exc: CoreAuthenticationError,
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
            content=format_error_response(exc, request, is_agent_request(request)),
        )

    @app.exception_handler(CoreKeyValidationError)
    async def key_validation_error_handler(
        request: Request, exc: CoreKeyValidationError,
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
            content=format_error_response(exc, request, is_agent_request(request)),
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
        response_content = format_error_response(
            exc, request, is_agent_request(request),
        )
        response_content["retry_after"] = retry_after
        return JSONResponse(
            status_code=exc.status_code,
            content=response_content,
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
            content=format_error_response(exc, request, is_agent_request(request)),
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
                    "api_status_code",
                ),
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc, request, is_agent_request(request)),
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
            status_code=exc.status_code,
            content=format_error_response(exc, request, is_agent_request(request)),
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
            content=format_error_response(exc, request, is_agent_request(request)),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request, exc: RequestValidationError,
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
                },
            )

        logger.warning(
            f"Request validation error: {len(error_details)} validation errors",
            extra={
                "errors": error_details,
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )

        # Create a CoreValidationError to use our formatting
        validation_exc = CoreValidationError(
            message="Request validation failed",
            code="REQUEST_VALIDATION_ERROR",
            details={"additional_context": {"validation_errors": error_details}},
        )

        response_content = format_error_response(
            validation_exc, request, is_agent_request(request),
        )

        # Add validation errors to the response for both frontend and agents
        response_content["validation_errors"] = error_details

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response_content,
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

        # Map common HTTP errors to appropriate core exceptions
        if exc.status_code == 404:
            core_exc = CoreResourceNotFoundError(
                message=exc.detail or "Resource not found",
                code=f"HTTP_{exc.status_code}",
            )
        elif exc.status_code == 401:
            core_exc = CoreAuthenticationError(
                message=exc.detail or "Authentication required",
                code=f"HTTP_{exc.status_code}",
            )
        elif exc.status_code == 403:
            core_exc = CoreAuthorizationError(
                message=exc.detail or "Access forbidden", code=f"HTTP_{exc.status_code}",
            )
        else:
            core_exc = CoreTripSageError(
                message=exc.detail or f"HTTP {exc.status_code} error",
                code=f"HTTP_{exc.status_code}",
                status_code=exc.status_code,
            )

        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(core_exc, request, is_agent_request(request)),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other unhandled exceptions."""
        logger.exception(
            f"Unhandled exception: {exc!s}",
            extra={
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
                "exception_type": type(exc).__name__,
            },
        )

        # Create a generic CoreTripSageError for unexpected exceptions
        generic_exc = CoreTripSageError(
            message="Internal server error",
            code="INTERNAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                "additional_context": {
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc) if settings.debug else None,
                },
            },
        )

        response_content = format_error_response(
            generic_exc, request, is_agent_request(request),
        )

        # Add debug information if in debug mode
        if settings.debug:
            response_content["debug_info"] = {
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "traceback": traceback.format_exc()
                if is_agent_request(request)
                else None,
            }

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_content,
        )

    # Include routers
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(keys.router, prefix="/api/user/keys", tags=["api_keys"])
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
    app.include_router(trips.router, prefix="/api/trips", tags=["trips"])
    app.include_router(flights.router, prefix="/api/flights", tags=["flights"])
    app.include_router(
        accommodations.router, prefix="/api/accommodations", tags=["accommodations"],
    )
    app.include_router(
        destinations.router, prefix="/api/destinations", tags=["destinations"],
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
