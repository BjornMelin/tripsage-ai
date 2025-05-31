"""
TripSage API main application entry point.

This module creates and configures the FastAPI application with all necessary
middleware, routes, and startup/shutdown events.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter

from api.middlewares.authentication import AuthenticationMiddleware
from api.middlewares.logging import LoggingMiddleware
from api.middlewares.metrics import MetricsMiddleware
from api.routers import (
    accommodations,
    auth,
    destinations,
    flights,
    itineraries,
    keys,
    trips,
)

# Note: startup/shutdown events removed as they relied on obsolete MCP dependencies
from tripsage_core.config.base_app_settings import settings
from tripsage_core.exceptions.exceptions import (
    CoreAgentError,
    CoreAuthenticationError,
    CoreAuthorizationError,
    CoreDatabaseError,
    CoreExternalAPIError,
    CoreKeyValidationError,
    CoreMCPError,
    CoreRateLimitError,
    CoreResourceNotFoundError,
    CoreServiceError,
    CoreTripSageError,
    CoreValidationError,
    format_exception,
)

# Configure root logger
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    # Create application
    app = FastAPI(
        title=settings.app_name,
        description="TripSage API for AI-powered travel planning",
        version="1.0.0",
        docs_url="/docs" if not settings.environment == "production" else None,
        redoc_url="/redoc" if not settings.environment == "production" else None,
        debug=settings.debug,
    )

    # Register error handlers
    register_exception_handlers(app)

    # Register middleware
    register_middleware(app)

    # Register routes
    register_routers(app)

    # Register startup and shutdown events
    register_event_handlers(app)

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers.

    Args:
        app: FastAPI application
    """

    def _format_details(details, include_debug: bool = True):
        """Helper to format exception details."""
        if not details:
            return None
        if not include_debug:
            return None
        return details.model_dump(exclude_none=True)

    # Authentication and Authorization Errors
    @app.exception_handler(CoreAuthenticationError)
    async def authentication_error_handler(
        request: Request, exc: CoreAuthenticationError
    ) -> JSONResponse:
        """Handle authentication errors."""
        logger.warning(f"Authentication error: {exc.message} [code={exc.code}]")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": exc.message,
                "details": _format_details(exc.details),
            },
        )

    @app.exception_handler(CoreAuthorizationError)
    async def authorization_error_handler(
        request: Request, exc: CoreAuthorizationError
    ) -> JSONResponse:
        """Handle authorization errors."""
        logger.warning(f"Authorization error: {exc.message} [code={exc.code}]")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": exc.message,
                "details": _format_details(exc.details),
            },
        )

    # Resource and Validation Errors
    @app.exception_handler(CoreResourceNotFoundError)
    async def resource_not_found_error_handler(
        request: Request, exc: CoreResourceNotFoundError
    ) -> JSONResponse:
        """Handle resource not found errors."""
        logger.info(f"Resource not found: {exc.message} [code={exc.code}]")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": exc.message,
                "details": _format_details(exc.details),
            },
        )

    @app.exception_handler(CoreValidationError)
    async def core_validation_error_handler(
        request: Request, exc: CoreValidationError
    ) -> JSONResponse:
        """Handle core validation errors."""
        logger.warning(f"Validation error: {exc.message} [code={exc.code}]")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": exc.message,
                "details": _format_details(exc.details),
            },
        )

    # Service and Infrastructure Errors
    @app.exception_handler(CoreServiceError)
    async def service_error_handler(
        request: Request, exc: CoreServiceError
    ) -> JSONResponse:
        """Handle service errors."""
        logger.error(f"Service error: {exc.message} [code={exc.code}]")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": exc.message,
                "details": _format_details(exc.details),
            },
        )

    @app.exception_handler(CoreRateLimitError)
    async def rate_limit_error_handler(
        request: Request, exc: CoreRateLimitError
    ) -> JSONResponse:
        """Handle rate limit errors."""
        logger.warning(f"Rate limit exceeded: {exc.message} [code={exc.code}]")

        # Add Retry-After header if specified in details
        headers = {}
        if exc.details and exc.details.additional_context.get("retry_after"):
            retry_after = exc.details.additional_context["retry_after"]
            headers["Retry-After"] = str(retry_after)

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": exc.message,
                "details": _format_details(exc.details),
            },
            headers=headers,
        )

    @app.exception_handler(CoreKeyValidationError)
    async def key_validation_error_handler(
        request: Request, exc: CoreKeyValidationError
    ) -> JSONResponse:
        """Handle API key validation errors."""
        logger.warning(f"API key validation error: {exc.message} [code={exc.code}]")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": exc.message,
                "details": _format_details(exc.details),
            },
        )

    @app.exception_handler(CoreDatabaseError)
    async def database_error_handler(
        request: Request, exc: CoreDatabaseError
    ) -> JSONResponse:
        """Handle database errors."""
        logger.error(f"Database error: {exc.message} [code={exc.code}]")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": "A database error occurred. Please try again later.",
                "details": _format_details(exc.details, settings.debug),
            },
        )

    @app.exception_handler(CoreExternalAPIError)
    async def external_api_error_handler(
        request: Request, exc: CoreExternalAPIError
    ) -> JSONResponse:
        """Handle external API errors."""
        logger.error(f"External API error: {exc.message} [code={exc.code}]")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": (
                    "An external service is currently unavailable. "
                    "Please try again later."
                ),
                "details": _format_details(exc.details, settings.debug),
            },
        )

    @app.exception_handler(CoreMCPError)
    async def mcp_error_handler(request: Request, exc: CoreMCPError) -> JSONResponse:
        """Handle MCP server errors."""
        logger.error(f"MCP error: {exc.message} [code={exc.code}]")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": (
                    "A service component is currently unavailable. "
                    "Please try again later."
                ),
                "details": _format_details(exc.details, settings.debug),
            },
        )

    @app.exception_handler(CoreAgentError)
    async def agent_error_handler(
        request: Request, exc: CoreAgentError
    ) -> JSONResponse:
        """Handle agent errors."""
        logger.error(f"Agent error: {exc.message} [code={exc.code}]")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": (
                    "The AI agent encountered an error processing your request. "
                    "Please try again."
                ),
                "details": _format_details(exc.details, settings.debug),
            },
        )

    # General Core TripSage Error (catch-all for any core exception not handled above)
    @app.exception_handler(CoreTripSageError)
    async def core_tripsage_error_handler(
        request: Request, exc: CoreTripSageError
    ) -> JSONResponse:
        """Handle general TripSage core errors."""
        logger.error(f"Core TripSage error: {exc.message} [code={exc.code}]")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": exc.message,
                "details": _format_details(exc.details),
            },
        )

    # FastAPI Request Validation Errors
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle FastAPI request validation errors."""
        logger.warning(f"Request validation error: {exc.errors()}")

        # Format validation errors in a user-friendly way
        formatted_errors = []
        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            formatted_errors.append(
                {
                    "field": field_path,
                    "message": error["msg"],
                    "type": error["type"],
                    "input": error.get("input"),
                }
            )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed. Please check your input data.",
                "details": {
                    "errors": formatted_errors,
                    "error_count": len(formatted_errors),
                },
            },
        )

    # Generic Exception Handler (catch-all for any unhandled exceptions)
    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle any unhandled exceptions."""
        logger.exception(f"Unhandled exception: {str(exc)}")

        # Use the format_exception utility to create a standardized response
        error_data = format_exception(exc)

        # In production, don't expose internal error details
        if not settings.debug:
            error_data = {
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "code": "INTERNAL_ERROR",
                "status_code": 500,
                "details": None,
            }

        return JSONResponse(
            status_code=error_data.get("status_code", 500),
            content={
                "error": error_data.get("code", "INTERNAL_ERROR"),
                "message": error_data.get("message", "An unexpected error occurred"),
                "details": error_data.get("details") if settings.debug else None,
            },
        )


def register_middleware(app: FastAPI) -> None:
    """Register middleware.

    Args:
        app: FastAPI application
    """
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"]
        if settings.debug
        else ["https://tripsage.ai", "https://app.tripsage.ai"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(LoggingMiddleware)

    # Add authentication middleware (conditionally)
    if not settings.debug:
        app.add_middleware(AuthenticationMiddleware)


def register_routers(app: FastAPI) -> None:
    """Register API routers.

    Args:
        app: FastAPI application
    """
    # Create API router with prefix
    api_router = APIRouter(prefix="/api/v1")

    # Include all domain routers
    api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    api_router.include_router(trips.router, prefix="/trips", tags=["Trips"])
    api_router.include_router(flights.router, prefix="/flights", tags=["Flights"])
    api_router.include_router(
        accommodations.router, prefix="/accommodations", tags=["Accommodations"]
    )
    api_router.include_router(
        destinations.router, prefix="/destinations", tags=["Destinations"]
    )
    api_router.include_router(
        itineraries.router, prefix="/itineraries", tags=["Itineraries"]
    )
    api_router.include_router(keys.router, prefix="/keys", tags=["API Keys"])

    # Include the API router in the main app
    app.include_router(api_router)

    # Add health check endpoint directly to main app
    @app.get("/health", include_in_schema=False)
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}


def register_event_handlers(app: FastAPI) -> None:
    """Register startup and shutdown event handlers.

    Args:
        app: FastAPI application
    """
    # Note: Startup/shutdown events removed as they relied on obsolete MCP dependencies


# Create application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn

    # Run the application with uvicorn when executed directly
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
