"""Authentication middleware for FastAPI.

This module provides middleware for authentication in FastAPI,
supporting both JWT token and API key authentication.
"""

import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from tripsage.api.core.config import Settings, get_settings
from tripsage.api.core.dependencies import get_settings_dependency
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# API key scheme for key-based authentication
api_key_header = APIKeyHeader(name="X-API-Key")


class TokenData(BaseModel):
    """Pydantic model for JWT token data."""

    sub: str  # Subject (usually user ID)
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    user_id: str
    scopes: list[str] = []


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication.

    This middleware handles JWT token and API key authentication.
    """

    def __init__(self, app: ASGIApp, settings: Optional[Settings] = None):
        """Initialize AuthMiddleware.

        Args:
            app: The ASGI application
            settings: API settings or None to use the default
        """
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process the request/response and handle authentication.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
            The response from the next middleware or endpoint
        """
        # Skip authentication for certain paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)

        # Try different authentication methods
        user_id = None
        auth_method = None

        # Check for JWT token
        token = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            try:
                token_value = token.replace("Bearer ", "")
                token_data = self._decode_jwt_token(token_value)
                user_id = token_data.user_id
                auth_method = "jwt"
            except AuthenticationError:
                # JWT authentication failed, try next method
                pass

        # Check for API key if JWT auth failed
        if not user_id:
            api_key = request.headers.get("X-API-Key")
            if api_key:
                try:
                    # Here you would validate the API key against your database
                    # This is a placeholder for the actual implementation
                    # user_id = await self._validate_api_key(api_key)
                    # auth_method = "api_key"

                    # For now, just raise an error (API key validation not implemented)
                    raise AuthenticationError("API key validation not implemented")
                except AuthenticationError as err:
                    # API key authentication failed
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication credentials",
                        headers={"WWW-Authenticate": "Bearer"},
                    ) from err

        # If no authentication method succeeded
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Set authenticated user in request state
        request.state.user_id = user_id
        request.state.auth_method = auth_method

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
        # Skip authentication for docs, health check, and login/register endpoints
        skip_paths = [
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/api/health",
            "/api/auth/token",
            "/api/auth/register",
        ]

        for skip_path in skip_paths:
            if path.startswith(skip_path):
                return True

        return False

    def _decode_jwt_token(self, token: str) -> TokenData:
        """Decode and validate a JWT token.

        Args:
            token: The JWT token to decode

        Returns:
            TokenData with the decoded token data

        Raises:
            AuthenticationError: If the token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=["HS256"],
            )

            # Validate the token data
            if "sub" not in payload or "user_id" not in payload:
                raise AuthenticationError("Invalid token payload")

            # Check if token is expired
            if (
                "exp" in payload
                and datetime.now(datetime.UTC).timestamp() > payload["exp"]
            ):
                raise AuthenticationError("Token expired")

            return TokenData(**payload)
        except JWTError as err:
            raise AuthenticationError("Invalid token") from err


def create_access_token(
    data: Dict,
    settings: Settings,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a new JWT access token.

    Args:
        data: The data to encode in the token
        settings: API settings
        expires_delta: Optional expiration timedelta, defaults to settings value

    Returns:
        The encoded JWT token
    """
    to_encode = data.copy()

    # Set expiration
    if expires_delta:
        expire = datetime.now(datetime.UTC) + expires_delta
    else:
        expire = datetime.now(datetime.UTC) + timedelta(
            minutes=settings.token_expiration_minutes
        )

    # Add standard JWT claims
    to_encode.update(
        {
            "exp": expire.timestamp(),
            "iat": datetime.now(datetime.UTC).timestamp(),
        }
    )

    # Encode the token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm="HS256",
    )

    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> str:
    """Get the current authenticated user from the JWT token.

    This dependency function can be used in endpoint handlers.

    Args:
        token: The JWT token

    Returns:
        The user ID from the token

    Raises:
        HTTPException: If the token is invalid
    """
    settings = get_settings_dependency()

    try:
        # Decode the token
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )

        # Get the user ID
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user_id
    except JWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


async def get_current_api_key(
    api_key: str = Depends(api_key_header),
) -> str:
    """Get the API key from the request header.

    This dependency function can be used in endpoint handlers.

    Args:
        api_key: The API key from the header

    Returns:
        The API key

    Raises:
        HTTPException: If the API key is invalid
    """
    # This is a placeholder for actual API key validation
    # You would typically validate the API key against your database
    # and return the associated user ID or API key ID

    # For now, we'll just raise an error
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key validation not implemented",
    )
