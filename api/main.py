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

from api.core.config import settings
from api.middlewares.authentication import AuthenticationMiddleware
from api.middlewares.error_handling import ErrorHandlingMiddleware
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
from tripsage.api.dependencies import shutdown_event, startup_event
from tripsage_core.exceptions.exceptions import CoreTripSageError as TripSageError

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

    @app.exception_handler(TripSageError)
    async def tripsage_error_handler(
        request: Request, exc: TripSageError
    ) -> JSONResponse:
        """Handle TripSage-specific errors."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors."""
        errors = [
            {"loc": err["loc"], "msg": err["msg"], "type": err["type"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Validation error",
                "details": errors,
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
    app.add_middleware(ErrorHandlingMiddleware)

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
    app.add_event_handler("startup", startup_event)
    app.add_event_handler("shutdown", shutdown_event)


# Create application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn

    # Run the application with uvicorn when executed directly
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
