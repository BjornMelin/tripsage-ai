"""
Authentication middleware for FastAPI.

This middleware authenticates requests using JWT tokens or API keys.
"""

import logging
from typing import Optional

import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api.core.config import settings
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for authenticating requests.

    This middleware validates JWT tokens from the Authorization header
    or API keys from the X-API-Key header or api_key query parameter.

    It populates request.state.user with the authenticated user information
    if authentication is successful.
    """

    async def dispatch(self, request: Request, call_next):
        """Process the request and add authentication information.

        Args:
            request: The FastAPI request
            call_next: The next middleware or route handler

        Returns:
            The response from the next middleware or route handler
        """
        # Skip authentication for certain paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)

        # Try to authenticate
        try:
            # First check for API key
            api_key = self._get_api_key(request)
            if api_key:
                # Validate API key
                if self._validate_api_key(api_key):
                    # Set user information on request state
                    request.state.user = {
                        "id": "api_user",
                        "is_api": True,
                        "api_key": api_key,
                    }
                    return await call_next(request)

            # No valid API key found, try JWT token
            token = self._get_jwt_token(request)
            if token:
                # Validate JWT token
                user = self._validate_jwt_token(token)
                if user:
                    # Set user information on request state
                    request.state.user = user
                    return await call_next(request)

            # No authentication provided
            # If the route requires authentication,
            # it will be handled at the dependency level
            # For now, continue without user information
            return await call_next(request)

        except AuthenticationError as e:
            logger.warning(f"Authentication failed: {str(e)}")
            return JSONResponse(
                status_code=401,
                content={"error": "AUTHENTICATION_ERROR", "message": str(e)},
            )
        except Exception as e:
            logger.exception(f"Authentication middleware error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": "INTERNAL_ERROR", "message": "Internal server error"},
            )

    def _should_skip_auth(self, path: str) -> bool:
        """Check if authentication should be skipped for this path.

        Args:
            path: The request path

        Returns:
            True if authentication should be skipped, False otherwise
        """
        # Skip authentication for public endpoints
        public_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/token",
            "/api/v1/auth/refresh",
        ]

        # Check if the path matches any public path
        return any(path.startswith(public_path) for public_path in public_paths)

    def _get_api_key(self, request: Request) -> Optional[str]:
        """Get API key from request.

        Args:
            request: The FastAPI request

        Returns:
            API key if found, None otherwise
        """
        # Try to get API key from header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key

        # Try to get API key from query parameter
        api_key = request.query_params.get("api_key")
        if api_key:
            return api_key

        return None

    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key.

        Args:
            api_key: The API key to validate

        Returns:
            True if valid, False otherwise
        """
        # This is a simplified implementation
        # In a real system, you'd validate the API key against a database
        return api_key.startswith("tripsage_")

    def _get_jwt_token(self, request: Request) -> Optional[str]:
        """Get JWT token from request.

        Args:
            request: The FastAPI request

        Returns:
            JWT token if found, None otherwise
        """
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.replace("Bearer ", "")
        return None

    def _validate_jwt_token(self, token: str) -> Optional[dict]:
        """Validate JWT token.

        Args:
            token: The JWT token to validate

        Returns:
            User information if valid, None otherwise

        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            # Decode the JWT token
            payload = jwt.decode(
                token,
                settings.secret_key.get_secret_value(),
                algorithms=[settings.algorithm],
            )

            # Return user information
            return {
                "id": payload["sub"],
                "username": payload["username"],
                "is_api": False,
            }
        except jwt.ExpiredSignatureError as err:
            raise AuthenticationError("Token has expired") from err
        except jwt.InvalidTokenError as err:
            raise AuthenticationError("Invalid token") from err
