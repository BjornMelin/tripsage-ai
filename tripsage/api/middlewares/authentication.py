"""Authentication middleware for FastAPI.

This module provides authentication middleware that validates Supabase-issued
JWT access tokens and populates request.state.principal with authenticated
entity information while emitting audit events.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED
from starlette.types import ASGIApp

from tripsage.api.core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditOutcome,
    AuditSeverity,
    audit_authentication,
    audit_security_event,
)
from tripsage_core.services.infrastructure.supabase_client import (
    verify_and_get_claims,
)


logger = logging.getLogger(__name__)


class Principal(BaseModel):
    """Represents an authenticated principal (user or agent)."""

    id: str
    type: str  # "user" or "agent"
    email: str | None = None
    service: str | None = None
    auth_method: str  # "jwt"
    scopes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="ignore",
    )

    @property
    def user_id(self) -> str:
        """Get user ID (alias for id field)."""
        return self.id


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for Supabase JWT flows.

    This middleware handles:
    - JWT token authentication for frontend users
    - Populating request.state.principal with authenticated entity info
    - Proper error responses tailored to each authentication failure
    """

    def __init__(
        self,
        app: ASGIApp,
        settings: Settings | None = None,
    ):
        """Initialize AuthenticationMiddleware.

        Args:
            app: The ASGI application
            settings: API settings or None to use the default
        """
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(  # pylint: disable=too-many-statements
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process the request and handle authentication with enhanced security.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
            The response from the next middleware or endpoint
        """
        if request.method.upper() == "OPTIONS":
            response = await call_next(request)
            self._add_security_headers(response)
            return response

        # Skip authentication for certain paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)

        # Perform header validation for security
        if not self._validate_request_headers(request):
            # Log suspicious header activity
            await audit_security_event(
                event_type=AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
                severity=AuditSeverity.HIGH,
                message="Suspicious request headers detected",
                actor_id="unknown",
                ip_address=self._get_client_ip(request),
                target_resource=request.url.path,
                risk_score=70,
                user_agent=request.headers.get("User-Agent"),
                method=request.method,
                headers_count=len(request.headers),
            )

            return Response(
                content="Invalid request headers",
                status_code=HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Try to authenticate the request
        principal = None
        auth_error = None

        # Try JWT authentication first (Bearer token)
        authorization_header = request.headers.get("Authorization")
        if authorization_header and authorization_header.startswith("Bearer "):
            try:
                token = authorization_header.replace("Bearer ", "")
                if not token:
                    raise AuthenticationError("Invalid token format")
                principal = await self._authenticate_jwt(token)

                # Log successful JWT authentication
                if principal:
                    await audit_authentication(
                        event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
                        outcome=AuditOutcome.SUCCESS,
                        user_id=principal.id,
                        ip_address=self._get_client_ip(request),
                        user_agent=request.headers.get("User-Agent"),
                        message="JWT authentication successful",
                        endpoint=request.url.path,
                        method=request.method,
                    )

            except AuthenticationError as e:
                auth_error = e

                # Log failed JWT authentication
                await audit_authentication(
                    event_type=AuditEventType.AUTH_LOGIN_FAILED,
                    outcome=AuditOutcome.FAILURE,
                    user_id="unknown",
                    ip_address=self._get_client_ip(request),
                    user_agent=request.headers.get("User-Agent"),
                    message=f"JWT authentication failed: {e!s}",
                    endpoint=request.url.path,
                    method=request.method,
                    error_type=type(e).__name__,
                )

                logger.warning(
                    "JWT authentication failed: %s",
                    e,
                    extra={
                        "ip_address": self._get_client_ip(request),
                        "user_agent": request.headers.get("User-Agent", "Unknown")[
                            :200
                        ],
                        "path": request.url.path,
                    },
                )

        # If no authentication succeeded
        if not principal:
            # Log failed authentication attempt
            user_agent = request.headers.get("User-Agent", "Unknown")[:200]
            error_msg = str(auth_error) if auth_error else "No credentials provided"

            # Log authentication failure
            await audit_security_event(
                event_type=AuditEventType.ACCESS_DENIED,
                severity=AuditSeverity.MEDIUM,
                message=f"Authentication required for {request.url.path}",
                actor_id="unauthenticated",
                ip_address=self._get_client_ip(request),
                target_resource=request.url.path,
                risk_score=30,
                user_agent=user_agent,
                method=request.method,
                error_details=error_msg,
            )

            logger.warning(
                "Authentication failed",
                extra={
                    "ip_address": self._get_client_ip(request),
                    "user_agent": user_agent,
                    "path": request.url.path,
                    "error": error_msg,
                },
            )

            if auth_error:
                # Return specific error if we have one
                return self._create_auth_error_response(auth_error)
            # Generic not authenticated error
            return Response(
                content="Authentication required",
                status_code=HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Set authenticated principal in request state
        request.state.principal = principal

        # Enrich logging with security context
        logger.info(
            "Request authenticated",
            extra={
                "principal_id": principal.id,
                "principal_type": principal.type,
                "auth_method": principal.auth_method,
                "path": request.url.path,
                "ip_address": self._get_client_ip(request),
                "user_agent": request.headers.get("User-Agent", "Unknown")[:200],
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )

        # Continue with the request
        response = await call_next(request)

        # Add security headers to response
        self._add_security_headers(response)

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
            "/openapi.json",
            "/api/health",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/reset-password",
            "/api/auth/token",  # OAuth2 token endpoint
        ]

        return any(path.startswith(skip_path) for skip_path in skip_paths)

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
            claims = await verify_and_get_claims(token)
            user_id = str(claims.get("sub"))
            if not user_id:
                raise AuthenticationError("Invalid authentication token")

            email = claims.get("email")
            role = claims.get("role", "authenticated")

            metadata: dict[str, Any] = {
                "role": role,
                "aud": claims.get("aud", "authenticated"),
                "supabase_claims": claims,
            }

            return Principal(
                id=user_id,
                type="user",
                email=email,
                auth_method="jwt",
                scopes=[],
                metadata=metadata,
            )

        except AuthenticationError:
            raise
        except Exception as exc:  # pragma: no cover - logged for observability
            logger.exception("Supabase JWT authentication error")
            raise AuthenticationError("Invalid authentication token") from exc

    def _create_auth_error_response(self, error: AuthenticationError) -> Response:
        """Create an authentication error response.

        Args:
            error: The authentication error

        Returns:
            HTTP response with error details
        """
        return Response(
            content=f"Authentication failed: {error.message}",
            status_code=HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _validate_request_headers(self, request: Request) -> bool:
        """Validate request headers for security.

        Args:
            request: The HTTP request

        Returns:
            True if headers are valid, False otherwise
        """
        # Check for excessively long headers (potential DoS)
        for name, value in request.headers.items():
            if len(name) > 256 or len(value) > 8192:
                logger.warning(
                    "Excessively long header detected",
                    extra={
                        "header_name": name[:100],
                        "header_length": len(value),
                        "ip_address": self._get_client_ip(request),
                    },
                )
                return False

            # Check for suspicious patterns in headers
            suspicious_patterns = [
                "<script",
                "javascript:",
                "data:",
                "eval(",
                "DROP TABLE",
                "UNION SELECT",
                "../",
                "\x00",
            ]

            combined_header = f"{name}:{value}".lower()
            for pattern in suspicious_patterns:
                if pattern.lower() in combined_header:
                    logger.warning(
                        "Suspicious pattern in header",
                        extra={
                            "header_name": name,
                            "pattern": pattern,
                            "ip_address": self._get_client_ip(request),
                        },
                    )
                    return False

        return True

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with proper header precedence."""
        # Check forwarded headers in order of preference
        forwarded_headers = [
            "X-Forwarded-For",
            "X-Real-IP",
            "CF-Connecting-IP",  # Cloudflare
            "X-Client-IP",
        ]

        for header in forwarded_headers:
            ip = request.headers.get(header)
            if ip:
                # Take first IP if comma-separated
                ip = ip.split(",")[0].strip()
                if self._is_valid_ip_format(ip):
                    return ip

        # Fall back to direct connection IP
        if request.client is not None and getattr(request.client, "host", None):
            return request.client.host  # type: ignore[no-any-return]

        return "unknown"

    def _is_valid_ip_format(self, ip: str) -> bool:
        """Check if string is a valid IP address format."""
        try:
            from ipaddress import ip_address

            ip_address(ip)
            return True
        except ValueError:
            return False

    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response.

        Args:
            response: HTTP response to modify
        """
        # Security headers to prevent various attacks
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        }

        # Only add headers that aren't already set
        for header, value in security_headers.items():
            if header not in response.headers:
                response.headers[header] = value
