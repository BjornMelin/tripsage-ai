"""Enhanced authentication middleware for FastAPI.

This module provides robust authentication middleware supporting both JWT tokens
(for frontend) and API Keys (for agents), populating request.state.principal
with authenticated entity information.
"""

import logging
from typing import Callable, Optional, Union

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED
from starlette.types import ASGIApp

from tripsage.api.core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)
from tripsage_core.exceptions.exceptions import (
    CoreKeyValidationError as KeyValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.services.business.key_management_service import KeyManagementService

logger = logging.getLogger(__name__)


class Principal(TripSageModel):
    """Represents an authenticated principal (user or agent)."""

    id: str
    type: str  # "user" or "agent"
    email: Optional[str] = None
    service: Optional[str] = None  # For API keys
    auth_method: str  # "jwt" or "api_key"
    scopes: list[str] = []
    metadata: dict = {}


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware for JWT and API Key authentication.

    This middleware handles:
    - JWT token authentication for frontend users
    - API key authentication for agents and services
    - Populating request.state.principal with authenticated entity info
    - Proper error responses for different authentication failures
    """

    def __init__(
        self,
        app: ASGIApp,
        settings: Optional[Settings] = None,
        key_service: Optional[KeyManagementService] = None,
    ):
        """Initialize AuthenticationMiddleware.

        Args:
            app: The ASGI application
            settings: API settings or None to use the default
            key_service: Key management service for API key handling
        """
        super().__init__(app)
        self.settings = settings or get_settings()
        self.key_service = key_service

        # Lazy initialization of services
        self._services_initialized = False

    async def _ensure_services(self):
        """Ensure services are initialized (lazy loading)."""
        if not self._services_initialized:
            if self.key_service is None:
                from tripsage_core.services.business.key_management_service import (
                    get_key_management_service,
                )

                self.key_service = await get_key_management_service()

            self._services_initialized = True

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process the request and handle authentication.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
            The response from the next middleware or endpoint
        """
        # Skip authentication for certain paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)

        # Ensure services are initialized
        await self._ensure_services()

        # Try to authenticate the request
        principal = None
        auth_error = None

        # Try JWT authentication first (Bearer token)
        authorization_header = request.headers.get("Authorization")
        if authorization_header and authorization_header.startswith("Bearer "):
            try:
                token = authorization_header.replace("Bearer ", "")
                principal = await self._authenticate_jwt(token)
            except AuthenticationError as e:
                auth_error = e
                logger.debug(f"JWT authentication failed: {e}")

        # Try API key authentication if JWT failed
        if not principal:
            api_key_header = request.headers.get("X-API-Key")
            if api_key_header:
                try:
                    principal = await self._authenticate_api_key(api_key_header)
                except (AuthenticationError, KeyValidationError) as e:
                    auth_error = e
                    logger.debug(f"API key authentication failed: {e}")

        # If no authentication succeeded
        if not principal:
            if auth_error:
                # Return specific error if we have one
                return self._create_auth_error_response(auth_error)
            else:
                # Generic not authenticated error
                return Response(
                    content="Authentication required",
                    status_code=HTTP_401_UNAUTHORIZED,
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Set authenticated principal in request state
        request.state.principal = principal

        # Log successful authentication
        logger.info(
            "Request authenticated",
            extra={
                "principal_id": principal.id,
                "principal_type": principal.type,
                "auth_method": principal.auth_method,
                "path": request.url.path,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )

        # Continue with the request
        response = await call_next(request)
        return response

    def _should_skip_auth(self, path: str) -> bool:
        """Check if authentication should be skipped for a path.

        Args:
            path: The request path

        Returns:
            True if authentication should be skipped, False otherwise
        """
        # Skip authentication for public endpoints
        skip_paths = [
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/api/health",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/reset-password",
            "/api/auth/token",  # OAuth2 token endpoint
        ]

        for skip_path in skip_paths:
            if path.startswith(skip_path):
                return True

        return False

    async def _authenticate_jwt(self, token: str) -> Principal:
        """Authenticate using JWT token.

        Args:
            token: JWT token

        Returns:
            Authenticated principal

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Use the new Supabase auth validation
            import jwt

            from tripsage_core.config.base_app_settings import get_settings

            settings = get_settings()

            # Local JWT validation for performance
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )

            # Extract user data from token
            user_id = payload["sub"]
            email = payload.get("email")
            role = payload.get("role", "authenticated")

            # Create principal from token data
            return Principal(
                id=user_id,
                type="user",
                email=email,
                auth_method="jwt",
                scopes=[],
                metadata={
                    "role": role,
                    "aud": payload.get("aud", "authenticated"),
                },
            )

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired") from None
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token") from None
        except Exception as e:
            logger.error(f"JWT authentication error: {e}")
            raise AuthenticationError("Invalid authentication token") from e

    async def _authenticate_api_key(self, api_key: str) -> Principal:
        """Authenticate using API key.

        Args:
            api_key: API key value

        Returns:
            Authenticated principal

        Raises:
            AuthenticationError: If authentication fails
            KeyValidationError: If key validation fails
        """
        try:
            # For API keys, we need to identify which user/service owns the key
            # This is a simplified implementation - in production, you'd have a
            # more sophisticated API key lookup system

            # Extract key ID and secret from the API key format
            # Format: "sk_<service>_<key_id>_<secret>"
            parts = api_key.split("_")
            if len(parts) < 4 or parts[0] != "sk":
                raise KeyValidationError("Invalid API key format")

            service = parts[1]
            key_id = parts[2]
            # The rest is the secret
            secret = "_".join(parts[3:])

            # TODO: Implement actual API key validation logic
            # For now, we'll create a mock principal for valid-looking keys
            if len(secret) < 20:
                raise KeyValidationError("Invalid API key")

            # Create principal for API key
            return Principal(
                id=f"agent_{service}_{key_id}",
                type="agent",
                service=service,
                auth_method="api_key",
                scopes=[f"{service}:*"],  # Grant all scopes for the service
                metadata={
                    "key_id": key_id,
                    "service": service,
                },
            )

        except (AuthenticationError, KeyValidationError):
            raise
        except Exception as e:
            logger.error(f"API key authentication error: {e}")
            raise AuthenticationError("Invalid API key") from e

    def _create_auth_error_response(
        self, error: Union[AuthenticationError, KeyValidationError]
    ) -> Response:
        """Create an authentication error response.

        Args:
            error: The authentication error

        Returns:
            HTTP response with error details
        """
        if isinstance(error, KeyValidationError):
            return Response(
                content=f"API key validation failed: {error.message}",
                status_code=HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            return Response(
                content=f"Authentication failed: {error.message}",
                status_code=HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )
