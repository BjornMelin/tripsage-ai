"""Enhanced authentication middleware for FastAPI.

This module provides robust authentication middleware supporting both JWT tokens
(for frontend) and API Keys (for agents), populating request.state.principal
with authenticated entity information. Includes comprehensive audit logging
for all authentication events.
"""

import logging
from datetime import datetime, timezone
from typing import Callable, Optional, Union

from fastapi import Request, Response
from pydantic import BaseModel, ConfigDict
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
from tripsage_core.services.business.api_key_service import ApiKeyService
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditOutcome,
    AuditSeverity,
    audit_api_key,
    audit_authentication,
    audit_security_event,
)

logger = logging.getLogger(__name__)


class Principal(BaseModel):
    """Represents an authenticated principal (user or agent)."""

    id: str
    type: str  # "user" or "agent"
    email: Optional[str] = None
    service: Optional[str] = None  # For API keys
    auth_method: str  # "jwt" or "api_key"
    scopes: list[str] = []
    metadata: dict = {}

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="ignore",
        # Use exclude_unset to avoid potential serialization issues
        exclude_unset=True,
    )

    @property
    def user_id(self) -> str:
        """Get user ID (alias for id field)."""
        return self.id


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
        key_service: Optional[ApiKeyService] = None,
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
                from tripsage_core.config import get_settings
                from tripsage_core.services.business.api_key_service import (
                    ApiKeyService,
                )
                from tripsage_core.services.infrastructure.cache_service import (
                    get_cache_service,
                )
                from tripsage_core.services.infrastructure.database_service import (
                    get_database_service,
                )

                db = await get_database_service()
                cache = await get_cache_service()
                settings = get_settings()
                self.key_service = ApiKeyService(db=db, cache=cache, settings=settings)

            self._services_initialized = True

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        """Process the request and handle authentication with enhanced security.

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

        # Enhanced security: validate request headers
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
                # Enhanced security: validate token format
                if not self._validate_token_format(token):
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
                    message=f"JWT authentication failed: {str(e)}",
                    endpoint=request.url.path,
                    method=request.method,
                    error_type=type(e).__name__,
                )

                logger.warning(
                    f"JWT authentication failed: {e}",
                    extra={
                        "ip_address": self._get_client_ip(request),
                        "user_agent": request.headers.get("User-Agent", "Unknown")[:200],
                        "path": request.url.path,
                    },
                )

        # Try API key authentication if JWT failed
        if not principal:
            api_key_header = request.headers.get("X-API-Key")
            if api_key_header:
                try:
                    # Enhanced security: validate API key format
                    if not self._validate_api_key_format(api_key_header):
                        raise KeyValidationError("Invalid API key format")
                    principal = await self._authenticate_api_key(api_key_header)

                    # Log successful API key authentication
                    if principal:
                        # Extract service from principal metadata
                        service = principal.service or "unknown"
                        key_id = principal.metadata.get("key_id", "unknown")

                        await audit_api_key(
                            event_type=AuditEventType.API_KEY_VALIDATION_SUCCESS,
                            outcome=AuditOutcome.SUCCESS,
                            key_id=key_id,
                            service=service,
                            ip_address=self._get_client_ip(request),
                            message="API key authentication successful",
                            endpoint=request.url.path,
                            method=request.method,
                        )

                except (AuthenticationError, KeyValidationError) as e:
                    auth_error = e
                    user_agent = request.headers.get("User-Agent", "Unknown")[:200]

                    # Extract service and key_id for failed authentication audit
                    service = "unknown"
                    key_id = "unknown"
                    try:
                        if api_key_header and api_key_header.startswith("sk_"):
                            parts = api_key_header.split("_")
                            if len(parts) >= 3:
                                service = parts[1]
                                key_id = parts[2]
                    except Exception:
                        pass

                    # Log failed API key authentication
                    await audit_api_key(
                        event_type=AuditEventType.API_KEY_VALIDATION_FAILED,
                        outcome=AuditOutcome.FAILURE,
                        key_id=key_id,
                        service=service,
                        ip_address=self._get_client_ip(request),
                        message=f"API key authentication failed: {str(e)}",
                        endpoint=request.url.path,
                        method=request.method,
                        error_type=type(e).__name__,
                    )

                    logger.warning(
                        f"API key authentication failed: {e}",
                        extra={
                            "ip_address": self._get_client_ip(request),
                            "user_agent": user_agent,
                            "path": request.url.path,
                        },
                    )

        # If no authentication succeeded
        if not principal:
            # Log failed authentication attempt
            user_agent = request.headers.get("User-Agent", "Unknown")[:200]
            error_msg = str(auth_error) if auth_error else "No credentials provided"

            # Log comprehensive authentication failure
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
            else:
                # Generic not authenticated error
                return Response(
                    content="Authentication required",
                    status_code=HTTP_401_UNAUTHORIZED,
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Set authenticated principal in request state
        request.state.principal = principal

        # Enhanced logging with security context
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

            from tripsage_core.config import get_settings

            settings = get_settings()

            # Local JWT validation for performance
            payload = jwt.decode(
                token,
                settings.database_jwt_secret.get_secret_value(),
                algorithms=["HS256"],
                audience="authenticated",
                leeway=30,  # Allow 30 seconds clock skew
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
        except jwt.InvalidTokenError as e:
            logger.error(f"JWT InvalidTokenError: {e}")
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
            # Extract key ID and service from the API key format
            # Format: "sk_<service>_<key_id>_<secret>"
            parts = api_key.split("_")
            if len(parts) < 4 or parts[0] != "sk":
                raise KeyValidationError("Invalid API key format")

            service = parts[1]
            key_id = parts[2]
            # The rest is the secret
            secret = "_".join(parts[3:])

            # Validate the API key using the key management service
            if self.key_service:
                # Reconstruct the full API key for validation
                full_key = f"sk_{service}_{key_id}_{secret}"

                # Validate the key with the appropriate service
                from tripsage_core.services.business.api_key_service import ServiceType

                service_type = ServiceType(service) if service in [e.value for e in ServiceType] else ServiceType.OPENAI
                validation_result = await self.key_service.validate_api_key(service=service_type, key_value=full_key)

                if not validation_result.is_valid:
                    raise KeyValidationError(validation_result.message or "Invalid API key")

                # Retrieve key metadata if available
                key_metadata = validation_result.details

                # Create principal for validated API key
                return Principal(
                    id=f"agent_{service}_{key_id}",
                    type="agent",
                    service=service,
                    auth_method="api_key",
                    scopes=[f"{service}:*"],  # Grant all scopes for the service
                    metadata={
                        "key_id": key_id,
                        "service": service,
                        "validated_at": datetime.now(timezone.utc).isoformat(),
                        **key_metadata,  # Additional metadata
                    },
                )
            else:
                # Fallback validation if key service is not available
                if len(secret) < 20:
                    raise KeyValidationError("Invalid API key")

                # Create principal with limited validation
                return Principal(
                    id=f"agent_{service}_{key_id}",
                    type="agent",
                    service=service,
                    auth_method="api_key",
                    scopes=[f"{service}:*"],
                    metadata={
                        "key_id": key_id,
                        "service": service,
                        "validation_mode": "fallback",
                    },
                )

        except (AuthenticationError, KeyValidationError):
            raise
        except Exception as e:
            logger.error(f"API key authentication error: {e}")
            raise AuthenticationError("Invalid API key") from e

    def _create_auth_error_response(self, error: Union[AuthenticationError, KeyValidationError]) -> Response:
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

    def _validate_token_format(self, token: str) -> bool:
        """Validate JWT token format.

        Args:
            token: JWT token string

        Returns:
            True if format is valid, False otherwise
        """
        if not token or not isinstance(token, str):
            return False

        # Check length bounds
        if len(token) < 20 or len(token) > 4096:
            return False

        # Check for null bytes and control characters
        if "\x00" in token or any(ord(c) < 32 for c in token if c not in "\t\n\r"):
            return False

        # Basic JWT format check (three parts separated by dots)
        parts = token.split(".")
        if len(parts) != 3:
            return False

        # Each part should be base64url encoded (basic check)
        base64url_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_="
        for part in parts:
            if not part or not all(c in base64url_chars for c in part):
                return False

        return True

    def _validate_api_key_format(self, api_key: str) -> bool:
        """Validate API key format.

        Args:
            api_key: API key string

        Returns:
            True if format is valid, False otherwise
        """
        if not api_key or not isinstance(api_key, str):
            return False

        # Check length bounds
        if len(api_key) < 10 or len(api_key) > 512:
            return False

        # Check for null bytes and control characters
        if "\x00" in api_key or any(ord(c) < 32 for c in api_key):
            return False

        # Basic format check for our API key format: sk_service_keyid_secret
        if api_key.startswith("sk_"):
            parts = api_key.split("_")
            if len(parts) >= 4:
                return True

        # Allow other formats but they must be printable ASCII
        return all(32 <= ord(c) <= 126 for c in api_key)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with proper header precedence.

        Args:
            request: The HTTP request

        Returns:
            Client IP address
        """
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
        if hasattr(request.client, "host"):
            return request.client.host

        return "unknown"

    def _is_valid_ip_format(self, ip: str) -> bool:
        """Check if string is a valid IP address format.

        Args:
            ip: IP address string

        Returns:
            True if valid IP format, False otherwise
        """
        try:
            from ipaddress import AddressValueError, ip_address

            ip_address(ip)
            return True
        except (ValueError, AddressValueError):
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
