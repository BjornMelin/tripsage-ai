"""API Key Service for TripSage.

Provides API key creation, storage, validation, encryption, and audit logging.

Features:
- Bring Your Own Key (BYOK) support
- Pydantic V2 model usage (ConfigDict)
- Tenacity-based retry for validation
- Validation and monitoring
- Envelope encryption for key storage
- Audit logging for key operations
"""

# pylint: disable=too-many-lines, R1705

import asyncio
import base64
import binascii
import hashlib
import hmac
import logging
import uuid
from collections.abc import Awaitable
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, Optional, Protocol

import httpx
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import Depends
from pydantic import (
    ConfigDict,
    Field,
    computed_field,
    field_validator,
)

from tripsage_core.exceptions import (
    RECOVERABLE_ERRORS,
    CoreServiceError as ServiceError,
)
from tripsage_core.infrastructure.retry_policies import tripsage_retry
from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditOutcome,
    audit_api_key,
)
from tripsage_core.services.infrastructure.cache_service import (
    get_cache_service,
)
from tripsage_core.services.infrastructure.database_operations_mixin import (
    DatabaseOperationsMixin,
)
from tripsage_core.services.infrastructure.database_service import (
    get_database_service,
)
from tripsage_core.services.infrastructure.error_handling_mixin import (
    ErrorHandlingMixin,
)
from tripsage_core.services.infrastructure.logging_mixin import LoggingMixin
from tripsage_core.services.infrastructure.validation_mixin import ValidationMixin
from tripsage_core.utils.error_handling_utils import tripsage_safe_execute


class _TxProtocol(Protocol):
    """Minimal DB transaction protocol used by this service."""

    async def __aenter__(self) -> "_TxProtocol":
        """Enter the transaction context manager."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        """Exit the transaction context manager."""
        ...

    def insert(self, table: str, payload: dict[str, Any]) -> None:
        """Queue an insert operation for execution."""
        ...

    def delete(self, table: str, criteria: dict[str, Any]) -> None:
        """Queue a delete operation for execution."""
        ...

    async def execute(self) -> list[list[dict[str, Any]]]:
        """Execute queued operations and return batched results."""
        ...


class ApiKeyDatabaseProtocol(Protocol):
    """DB surface area required by ApiKeyService."""

    def transaction(self, user_id: str | None = None) -> _TxProtocol:
        """Open a batched transaction context."""
        ...

    async def get_user_api_keys(self, user_id: str) -> list[dict[str, Any]]:
        """Return API key rows for the given user."""
        ...

    async def get_api_key_by_id(
        self, key_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Return an API key row by id or ``None``."""
        ...

    async def get_api_key(self, user_id: str, service: str) -> dict[str, Any] | None:
        """Return a user's API key row for a service or ``None``."""
        ...

    async def update_api_key_last_used(self, key_id: str) -> bool:
        """Update last-used metadata, returning success state."""
        ...


if TYPE_CHECKING:
    from tripsage_core.config import Settings
    from tripsage_core.services.infrastructure.cache_service import CacheService


logger = logging.getLogger(__name__)

ENCRYPTION_ERRORS = (InvalidToken, ValueError, TypeError, binascii.Error)


class ServiceType(str, Enum):
    """Supported external service types."""

    OPENAI = "openai"
    WEATHER = "weather"
    GOOGLEMAPS = "googlemaps"
    FLIGHTS = "flights"
    ACCOMMODATION = "accommodation"
    WEBCRAWL = "webcrawl"
    CALENDAR = "calendar"
    EMAIL = "email"


class ValidationStatus(str, Enum):
    """API key validation status."""

    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    RATE_LIMITED = "rate_limited"
    SERVICE_ERROR = "service_error"
    FORMAT_ERROR = "format_error"


class ServiceHealthStatus(str, Enum):
    """Service health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ApiKeyCreateRequest(TripSageModel):
    """Modern request model for API key creation with Pydantic V2 optimizations."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        frozen=False,
        # Performance optimizations
        use_enum_values=True,
        validate_default=True,
        # Zero-copy optimizations where possible
        arbitrary_types_allowed=False,
        extra="forbid",  # Strict validation for security
    )

    name: str = Field(
        min_length=1, max_length=100, description="Descriptive name for the key"
    )
    service: ServiceType = Field(description="Service name")
    key_value: str = Field(min_length=1, description="The actual API key", alias="key")
    description: str | None = Field(
        default=None, max_length=500, description="Optional description"
    )
    expires_at: datetime | None = Field(
        default=None, description="Optional expiration date"
    )

    @field_validator("key_value")
    @classmethod
    def validate_key_format(cls, v: str) -> str:
        """Basic key format validation."""
        if len(v.strip()) < 8:
            raise ValueError("API key must be at least 8 characters long")
        return v.strip()


class ApiKeyResponse(TripSageModel):
    """Modern response model with computed fields."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        # Performance optimizations
        validate_default=True,
        frozen=True,  # Immutable response objects for safety
        extra="forbid",
        # Serialization optimizations
        ser_json_timedelta="float",
        ser_json_bytes="base64",
    )

    id: str = Field(description="Key ID")
    name: str = Field(description="Key name")
    service: ServiceType = Field(description="Service name")
    description: str | None = Field(default=None, description="Key description")
    is_valid: bool = Field(description="Validation status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    expires_at: datetime | None = Field(
        default=None, description="Expiration timestamp"
    )
    last_used: datetime | None = Field(default=None, description="Last usage timestamp")
    last_validated: datetime | None = Field(
        default=None, description="Last validation timestamp"
    )
    usage_count: int = Field(default=0, description="Number of times used")

    @computed_field
    @property
    def is_expired(self) -> bool:
        """Check if the key is expired."""
        if not self.expires_at:
            return False
        return datetime.now(UTC) > self.expires_at

    @computed_field
    @property
    def expires_in_days(self) -> int | None:
        """Days until expiration."""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.now(UTC)
        return max(0, delta.days)


class ApiValidationResult(TripSageModel):
    """Unified result model for API key validation and service health checks."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        validate_default=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=False,
    )

    is_valid: bool | None = Field(default=None)
    status: ValidationStatus | None = Field(default=None)
    health_status: ServiceHealthStatus | None = Field(default=None)
    service: ServiceType
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = Field(default=0.0)
    validated_at: datetime | None = Field(default_factory=lambda: datetime.now(UTC))
    checked_at: datetime | None = Field(default=None)
    rate_limit_info: dict[str, Any] | None = Field(default=None)
    quota_info: dict[str, Any] | None = Field(default=None)
    capabilities: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def success_rate_category(self) -> str:
        """Categorize validation success or mark as unknown when not applicable."""
        if self.is_valid:
            return "success"
        if self.is_valid is False:
            return "failure"
        return "unknown"

    @computed_field
    @property
    def is_healthy(self) -> bool | None:
        """Report health status when available."""
        if self.health_status is None:
            return None
        return self.health_status == ServiceHealthStatus.HEALTHY


class ApiKeyService(
    DatabaseOperationsMixin, ValidationMixin, LoggingMixin, ErrorHandlingMixin
):
    """API key service for TripSage following KISS principles.

    Provides key management, validation, and security features with clean
    dependency injection and atomic operations.
    """

    def __init__(
        self,
        db: ApiKeyDatabaseProtocol,
        cache: Optional["CacheService"] = None,
        settings: Optional["Settings"] = None,
        validation_timeout: int = 10,
    ):
        """Initialize the API key service with injected dependencies.

        Args:
            db: Database service instance (required)
            cache: Cache service instance (optional)
            settings: Application settings (optional, will use defaults)
            validation_timeout: Request timeout for validation (default: 10s)
        """
        # Store concrete dependency privately; expose via typed property
        self._db: ApiKeyDatabaseProtocol = db
        self.cache = cache
        self.validation_timeout = validation_timeout

        # Use settings or get defaults
        if settings is None:
            from tripsage_core.config import get_settings

            settings = get_settings()

        self.settings = settings

        # Initialize encryption with settings
        self._initialize_encryption(settings.secret_key.get_secret_value())

        # HTTP client with simple configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(validation_timeout),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
        )

    # DatabaseOperationsMixin requires subclasses to provide a typed `db` property
    @property
    def db(self) -> ApiKeyDatabaseProtocol:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Database service accessor used by mixin operations."""
        return self._db

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit - cleanup resources."""
        await self.client.aclose()

    def _get_service_value(self, service: ServiceType | str) -> str:
        """Get string value from service type, handling both enum and string inputs.

        This helper method accommodates the Pydantic V2 use_enum_values=True
        optimization
        which may convert enums to strings during validation.

        Args:
            service: ServiceType enum or string value

        Returns:
            String representation of the service type
        """
        return service.value if isinstance(service, ServiceType) else str(service)

    def _initialize_encryption(self, master_secret: str) -> None:
        """Initialize envelope encryption.

        - PBKDF2 with 600,000 iterations (2025 NIST recommendation)
        - SHA-256 for key derivation
        - Secure salt management

        Args:
            master_secret: Master secret for key derivation (str or SecretStr)
        """
        # Salt hardened for 2025 security standards
        salt = b"tripsage_api_key_salt_v4_2025"

        # Use PBKDF2 with 2025 security standards (600k iterations)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,  # 2025 NIST recommended minimum
        )

        # master_secret is expected to be a plain string at this point
        secret_value = master_secret

        # Derive master key with enhanced security
        key_bytes = kdf.derive(secret_value.encode("utf-8"))
        self.master_key = base64.urlsafe_b64encode(key_bytes)
        self.master_cipher = Fernet(self.master_key)

    @tripsage_safe_execute(exception_class=ServiceError)
    async def create_api_key(
        self, user_id: str, key_data: ApiKeyCreateRequest
    ) -> ApiKeyResponse:
        """Create and store a new API key atomically.

        Args:
            user_id: User ID
            key_data: API key creation data

        Returns:
            Created API key information

        Raises:
            ServiceError: If creation fails
        """
        try:
            # Validate the API key first
            validation_result: ApiValidationResult = await self.validate_api_key(
                key_data.service, key_data.key_value
            )

            # Generate secure key ID and encrypt key
            key_id = str(uuid.uuid4())
            encrypted_key = self._encrypt_api_key(key_data.key_value)

            # Prepare database entry
            now = datetime.now(UTC)
            db_key_data: dict[str, str | bool | int | None] = {
                "id": key_id,
                "user_id": user_id,
                "name": key_data.name,
                "service": self._get_service_value(key_data.service),
                "encrypted_key": encrypted_key,
                "description": key_data.description,
                "is_valid": bool(validation_result.is_valid)
                if validation_result.is_valid is not None
                else False,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "expires_at": key_data.expires_at.isoformat()
                if key_data.expires_at
                else None,
                "last_validated": (
                    validation_result.validated_at.isoformat()
                    if validation_result.validated_at
                    else None
                ),
                "usage_count": 0,
            }

            # Persist using a single DB transaction to match service contract
            async with self.db.transaction() as tx:  # type: ignore[attr-defined]
                tx.insert("api_keys", db_key_data)
                tx.insert(
                    "api_key_usage_logs",
                    {
                        "key_id": key_id,
                        "user_id": user_id,
                        "service": self._get_service_value(key_data.service),
                        "operation": "create",
                        "timestamp": now.isoformat(),
                        "success": True,
                    },
                )
                tx_result = await tx.execute()
            # Capture primary insert row if provided by the DB implementation
            result = (
                tx_result[0][0] if tx_result and tx_result[0] else None
            ) or db_key_data

            # Audit log (fire-and-forget)
            asyncio.create_task(  # noqa: RUF006
                self._audit_key_creation(key_id, user_id, key_data, validation_result)
            )

            logger.info(
                "API key created successfully",
                extra={
                    "user_id": user_id,
                    "key_id": key_id,
                    "service": self._get_service_value(key_data.service),
                    "is_valid": validation_result.is_valid,
                },
            )

            # Invalidate cache for this service to ensure fresh validations
            if self.cache and self.settings.enable_api_key_caching:
                try:
                    # Clear all validation cache entries (simplified approach)
                    await self.cache.delete_pattern("api_validation:v3:*")
                    logger.debug(
                        "Invalidated validation cache after key creation",
                        extra={"service": self._get_service_value(key_data.service)},
                    )
                except (
                    httpx.RequestError,
                    httpx.TimeoutException,
                    ValueError,
                    TypeError,
                ) as cache_error:
                    logger.warning(
                        "Cache invalidation failed after key creation",
                        extra={
                            "service": self._get_service_value(key_data.service),
                            "error": str(cache_error),
                        },
                    )

            return self._db_result_to_response(result)

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to create API key",
                extra={
                    "user_id": user_id,
                    "service": self._get_service_value(key_data.service),
                    "error": str(error),
                },
            )
            raise ServiceError(f"Failed to create API key: {error!s}") from error

    @tripsage_safe_execute()
    async def list_user_keys(self, user_id: str) -> list[ApiKeyResponse]:
        """Get all API keys for a user."""
        # Validate user ID
        self._validate_user_id(user_id)

        results = await self.db.get_user_api_keys(user_id)
        return [self._db_result_to_response(result) for result in results]

    @tripsage_safe_execute()
    async def get_api_key(self, key_id: str, user_id: str) -> dict[str, Any] | None:
        """Get a specific API key by ID for a user."""
        # Validate user ID
        self._validate_user_id(user_id)

        return await self.db.get_api_key_by_id(key_id, user_id)

    @tripsage_safe_execute()
    async def get_key_for_service(
        self, user_id: str, service: ServiceType
    ) -> str | None:
        """Get decrypted API key for a specific service.

        Args:
            user_id: User ID
            service: Service type

        Returns:
            Decrypted API key or None if not found/expired
        """
        # Validate user ID
        self._validate_user_id(user_id)

        result = await self.db.get_api_key(user_id, self._get_service_value(service))
        if not result:
            return None

        # Check expiration
        if result.get("expires_at"):
            expires_at = datetime.fromisoformat(result["expires_at"])
            if datetime.now(UTC) > expires_at:
                logger.info(
                    "API key expired for user %s, service %s",
                    user_id,
                    self._get_service_value(service),
                )
                return None

        # Decrypt the API key
        decrypted_key = self._decrypt_api_key(result["encrypted_key"])

        # Update last used timestamp (fire-and-forget)
        asyncio.create_task(self.db.update_api_key_last_used(result["id"]))  # noqa: RUF006

        return decrypted_key

    @tripsage_safe_execute()
    @tripsage_retry(include_httpx_errors=True, attempts=3, max_delay=10.0)
    async def validate_api_key(
        self,
        service: ServiceType,
        key_value: str,
        user_id: str | None = None,
    ) -> ApiValidationResult:
        """Validate API key with caching and retry logic.

        Checks cache first (5-minute TTL), then performs service-specific validation.
        Retries on network errors with exponential backoff (up to 3 attempts).
        Uses tenacity for retry logic with exponential backoff on network errors.

        Args:
            service: Service type determining validation endpoint and checks.
            key_value: API key to validate (minimum 8 chars, service-specific format).
            user_id: Optional user ID for audit logging and rate limiting.

        Returns:
            ApiValidationResult with validation status, capabilities, and metadata.
        """
        start_time = datetime.now(UTC)

        # Check cache first if enabled
        if self.cache and self.settings.enable_api_key_caching:
            cache_key = self._validation_cache_key(service, key_value)
            try:
                cached_raw = await self.cache.get_json(cache_key)
                if isinstance(cached_raw, dict) and cached_raw:
                    logger.debug(
                        "Cache hit for API key validation",
                        extra={
                            "service": self._get_service_value(service),
                            "cache_key": cache_key,
                        },
                    )
                    # Return cached result with updated latency
                    latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
                    # Handle enum conversion for cached results
                    cached_copy: dict[str, Any] = dict(cached_raw)
                    # Remove computed fields that shouldn't be in constructor
                    cached_copy.pop("success_rate_category", None)
                    cached_copy.pop("is_healthy", None)
                    # Update latency_ms
                    cached_copy["latency_ms"] = latency_ms
                    if "status" in cached_copy and isinstance(
                        cached_copy["status"], str
                    ):
                        cached_copy["status"] = ValidationStatus(cached_copy["status"])
                    if "service" in cached_copy and isinstance(
                        cached_copy["service"], str
                    ):
                        cached_copy["service"] = ServiceType(cached_copy["service"])
                    if (
                        "health_status" in cached_copy
                        and cached_copy["health_status"] is not None
                        and isinstance(cached_copy["health_status"], str)
                    ):
                        cached_copy["health_status"] = ServiceHealthStatus(
                            cached_copy["health_status"]
                        )
                    try:
                        return ApiValidationResult(**cached_copy)
                    except (ValueError, TypeError, KeyError) as validation_error:
                        logger.warning(
                            "Cached result validation error, proceeding "
                            "with fresh validation",
                            extra={
                                "service": self._get_service_value(service),
                                "error": str(validation_error),
                            },
                        )
                        raise  # Re-raise to be caught by outer except
            except (
                httpx.RequestError,
                httpx.TimeoutException,
                ValueError,
                TypeError,
            ) as cache_error:
                logger.warning(
                    "Cache read error, proceeding with validation",
                    extra={
                        "service": self._get_service_value(service),
                        "error": str(cache_error),
                    },
                )

        try:
            # Perform service validation using libraries where available
            result = await self._validate_api_key(service, key_value)

            # Calculate latency
            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            # Create final result
            final_result = ApiValidationResult(
                is_valid=result.is_valid,
                status=result.status,
                service=result.service,
                message=result.message,
                details=result.details,
                latency_ms=latency_ms,
                validated_at=result.validated_at,
                rate_limit_info=result.rate_limit_info,
                quota_info=result.quota_info,
                capabilities=result.capabilities,
            )

            # Cache successful validations if enabled
            if (
                self.cache
                and self.settings.enable_api_key_caching
                and final_result.is_valid
            ):
                cache_key = self._validation_cache_key(service, key_value)
                try:
                    await self.cache.set_json(
                        cache_key, final_result.model_dump(mode="json"), ttl=300
                    )  # 5 minutes
                    logger.debug(
                        "Cached API key validation result",
                        extra={
                            "service": self._get_service_value(service),
                            "cache_key": cache_key,
                        },
                    )
                except (
                    httpx.RequestError,
                    httpx.TimeoutException,
                    ValueError,
                    TypeError,
                ) as cache_error:
                    logger.warning(
                        "Cache write error, validation still successful",
                        extra={
                            "service": self._get_service_value(service),
                            "error": str(cache_error),
                        },
                    )

            return final_result

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "API key validation error for %s",
                self._get_service_value(service),
                extra={
                    "service": self._get_service_value(service),
                    "error": str(error),
                },
            )

            return ApiValidationResult(
                is_valid=False,
                status=ValidationStatus.SERVICE_ERROR,
                service=service,
                message=f"Validation error: {error!s}",
                latency_ms=(datetime.now(UTC) - start_time).total_seconds() * 1000,
            )

    @tripsage_safe_execute()
    async def check_service_health(self, service: ServiceType) -> ApiValidationResult:
        """Check the health of an external service.

        Args:
            service: The service to check

        Returns:
            ApiValidationResult populated with health-specific metadata. Validation
            fields (`is_valid`, `status`, `validated_at`) are set to ``None`` while
            `health_status` and `checked_at` describe the probe outcome.
        """
        start_time = datetime.now(UTC)

        try:
            return await self._check_service_health_generic(service)

        except RECOVERABLE_ERRORS as error:
            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return ApiValidationResult(
                service=service,
                is_valid=None,
                status=None,
                health_status=ServiceHealthStatus.UNHEALTHY,
                message=f"Health check failed: {error!s}",
                details={"error": str(error)},
                latency_ms=latency_ms,
                validated_at=None,
                checked_at=datetime.now(UTC),
            )

    @tripsage_safe_execute()
    async def check_all_services_health(self) -> dict[ServiceType, ApiValidationResult]:
        """Run concurrent health checks for core external services.

        Notes:
            The `tripsage_safe_execute` decorator used on `check_service_health`
            obscures its return type from the type checker. To keep types
            precise without altering the decorator, we cast each coroutine to
            `Awaitable[ApiValidationResult]` before passing to `asyncio.gather`.
        """
        services = [ServiceType.OPENAI, ServiceType.WEATHER, ServiceType.GOOGLEMAPS]

        # Run health checks concurrently
        tasks: list[Awaitable[ApiValidationResult]] = [
            self.check_service_health(service) for service in services
        ]
        results: list[ApiValidationResult | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
        )

        health_status: dict[ServiceType, ApiValidationResult] = {}
        for service, result in zip(services, results, strict=False):
            if isinstance(result, BaseException):
                health_status[service] = ApiValidationResult(
                    service=service,
                    is_valid=None,
                    status=None,
                    health_status=ServiceHealthStatus.UNHEALTHY,
                    latency_ms=0,
                    message=f"Health check error: {result!s}",
                    validated_at=None,
                    checked_at=datetime.now(UTC),
                )
            else:
                health_status[service] = result

        return health_status

    @tripsage_safe_execute()
    async def delete_api_key(self, key_id: str, user_id: str) -> bool:
        """Delete an API key atomically.

        Args:
            key_id: API key ID
            user_id: User ID (for authorization)

        Returns:
            True if deleted successfully
        """
        # Verify ownership first
        key_data = await self.db.get_api_key_by_id(key_id, user_id)
        if not key_data:
            return False

        # Perform atomic delete using DB transaction
        success = True
        async with self.db.transaction() as tx:  # type: ignore[attr-defined]
            tx.delete("api_keys", {"id": key_id, "user_id": user_id})
            # Also record usage log in same transaction
            now = datetime.now(UTC)
            tx.insert(
                "api_key_usage_logs",
                {
                    "key_id": key_id,
                    "user_id": user_id,
                    "service": key_data.get("service"),
                    "operation": "delete",
                    "timestamp": now.isoformat(),
                    "success": True,
                },
            )
            await tx.execute()

        # Log operation
        now = datetime.now(UTC)

        # Audit log (fire-and-forget)
        asyncio.create_task(self._audit_key_deletion(key_id, user_id, key_data))  # noqa: RUF006

        logger.info(
            "API key deleted",
            extra={
                "key_id": key_id,
                "user_id": user_id,
                "service": key_data.get("service"),
            },
        )

        # Invalidate cache for this service to ensure fresh validations
        if self.cache and self.settings.enable_api_key_caching:
            try:
                # Clear all validation cache entries (simplified approach)
                await self.cache.delete_pattern("api_validation:v3:*")
                logger.debug(
                    "Invalidated validation cache after key deletion",
                    extra={"service": key_data.get("service")},
                )
            except (
                httpx.RequestError,
                httpx.TimeoutException,
                ValueError,
                TypeError,
            ) as cache_error:
                logger.warning(
                    "Cache invalidation failed after key deletion",
                    extra={
                        "service": key_data.get("service"),
                        "error": str(cache_error),
                    },
                )

        return success

    def _encrypt_api_key(self, key_value: str) -> str:
        """Encrypt API key using envelope encryption.

        Implementation features:
        - Envelope encryption with unique data keys per operation
        - Secure key material handling
        - Error handling and logging improvements
        - Base64 URL-safe encoding for storage compatibility

        Args:
            key_value: Plain API key to encrypt

        Returns:
            Base64-encoded encrypted API key with embedded data key

        Raises:
            ServiceError: If encryption fails
        """
        if not key_value:
            raise ServiceError("Cannot encrypt empty key value")

        try:
            # Generate unique data encryption key for this operation
            data_key = Fernet.generate_key()
            data_cipher = Fernet(data_key)

            # Encrypt the API key with the data key
            encrypted_key = data_cipher.encrypt(key_value.encode("utf-8"))

            # Encrypt the data key with master key (envelope encryption)
            encrypted_data_key = self.master_cipher.encrypt(data_key)

            # Combine with secure separator (enhanced from v3)
            separator = b"::v4::"
            combined = encrypted_data_key + separator + encrypted_key
            return base64.urlsafe_b64encode(combined).decode("ascii")

        except ENCRYPTION_ERRORS as error:
            logger.exception(
                "API key encryption failed",
                extra={
                    "error": str(error),
                    "key_length": len(key_value) if key_value else 0,
                },
            )
            raise ServiceError(
                "Encryption failed - unable to secure API key"
            ) from error

    def _decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key using envelope encryption (v4 format only).

        Args:
            encrypted_key: Base64-encoded encrypted API key (v4 format)

        Returns:
            Decrypted API key string

        Raises:
            ServiceError: If decryption fails or format is invalid
        """
        if not encrypted_key:
            raise ServiceError("Cannot decrypt empty encrypted key")

        try:
            # Decode from base64
            combined = base64.urlsafe_b64decode(encrypted_key.encode("ascii"))

            # Require v4 separator
            if b"::v4::" not in combined:
                raise ServiceError(
                    "Invalid encrypted key format - expected v4 separator"
                )
            parts = combined.split(b"::v4::", 1)

            if len(parts) != 2:
                raise ServiceError("Invalid encrypted key format - malformed structure")

            encrypted_data_key, encrypted_value = parts

            # Decrypt data key with master key
            data_key = self.master_cipher.decrypt(encrypted_data_key)

            # Decrypt API key with data key
            data_cipher = Fernet(data_key)
            decrypted_value = data_cipher.decrypt(encrypted_value)

            return decrypted_value.decode("utf-8")

        except ENCRYPTION_ERRORS as error:
            logger.exception(
                "API key decryption failed",
                extra={
                    "error": str(error),
                    "encrypted_key_length": len(encrypted_key) if encrypted_key else 0,
                },
            )
            raise ServiceError(
                "Decryption failed - unable to recover API key"
            ) from error

    # ------------------------------------------------------------------
    # Benchmark/test helpers
    # ------------------------------------------------------------------

    def encrypt_for_benchmark(self, key_value: str) -> str:
        """Expose encryption for performance benchmarks and diagnostics."""
        return self._encrypt_api_key(key_value)

    def decrypt_for_benchmark(self, encrypted_key: str) -> str:
        """Expose decryption for performance benchmarks and diagnostics."""
        return self._decrypt_api_key(encrypted_key)

    async def _validate_api_key(  # pylint: disable=too-many-return-statements
        self, service: ServiceType, key_value: str
    ) -> ApiValidationResult:
        """Simplified API key validation.

        Args:
            service: Service type to validate against
            key_value: API key to validate

        Returns:
            ApiValidationResult with validation outcome
        """
        try:
            if service == ServiceType.OPENAI:
                # Format check
                if not key_value.startswith("sk-"):
                    return ApiValidationResult(
                        is_valid=False,
                        status=ValidationStatus.FORMAT_ERROR,
                        service=ServiceType.OPENAI,
                        message="Invalid OpenAI key format",
                    )
                # Use OpenAI library for validation
                import openai

                client = openai.AsyncOpenAI(api_key=key_value)
                models = await client.models.list()
                return ApiValidationResult(
                    is_valid=True,
                    status=ValidationStatus.VALID,
                    service=ServiceType.OPENAI,
                    message="OpenAI API key is valid",
                    capabilities=["gpt-4", "gpt-3.5", "image-generation"],
                    details={"models_available": len(models.data)},
                )
            elif service == ServiceType.WEATHER:
                # Simple HTTP validation
                if len(key_value) < 16:
                    return ApiValidationResult(
                        is_valid=False,
                        status=ValidationStatus.FORMAT_ERROR,
                        service=ServiceType.WEATHER,
                        message="Weather API key too short",
                    )
                response = await self.client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"q": "London", "appid": key_value},
                    timeout=self.validation_timeout,
                )
                if response.status_code == 200:
                    return ApiValidationResult(
                        is_valid=True,
                        status=ValidationStatus.VALID,
                        service=ServiceType.WEATHER,
                        message="Weather API key is valid",
                        capabilities=["current", "forecast"],
                    )
                elif response.status_code == 401:
                    return ApiValidationResult(
                        is_valid=False,
                        status=ValidationStatus.INVALID,
                        service=ServiceType.WEATHER,
                        message="Invalid API key",
                    )
                else:
                    return ApiValidationResult(
                        is_valid=False,
                        status=ValidationStatus.SERVICE_ERROR,
                        service=ServiceType.WEATHER,
                        message=f"Unexpected response: {response.status_code}",
                    )
            elif service == ServiceType.GOOGLEMAPS:
                # Simple HTTP validation
                if len(key_value) < 20:
                    return ApiValidationResult(
                        is_valid=False,
                        status=ValidationStatus.FORMAT_ERROR,
                        service=ServiceType.GOOGLEMAPS,
                        message="Google Maps API key too short",
                    )
                response = await self.client.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params={"address": "test", "key": key_value},
                    timeout=self.validation_timeout,
                )
                data = response.json()
                if data.get("status") == "OK":
                    return ApiValidationResult(
                        is_valid=True,
                        status=ValidationStatus.VALID,
                        service=ServiceType.GOOGLEMAPS,
                        message="Google Maps API key is valid",
                        capabilities=["geocoding", "places", "directions"],
                    )
                else:
                    return ApiValidationResult(
                        is_valid=False,
                        status=ValidationStatus.INVALID,
                        service=ServiceType.GOOGLEMAPS,
                        message="Invalid API key",
                    )
            else:
                # Generic validation
                if len(key_value) < 10:
                    return ApiValidationResult(
                        is_valid=False,
                        status=ValidationStatus.FORMAT_ERROR,
                        service=service,
                        message="API key too short",
                    )
                return ApiValidationResult(
                    is_valid=True,
                    status=ValidationStatus.VALID,
                    service=service,
                    message="API key accepted (generic validation)",
                )
        except RECOVERABLE_ERRORS as error:
            return ApiValidationResult(
                is_valid=False,
                status=ValidationStatus.SERVICE_ERROR,
                service=service,
                message=f"Validation error: {error!s}",
            )

    def _validation_cache_key(self, service: ServiceType, key_value: str) -> str:
        """Compute deterministic cache key without exposing raw secrets."""
        material = f"{self._get_service_value(service)}:{key_value}".encode()
        secret_bytes = self.settings.secret_key.get_secret_value().encode("utf-8")
        digest = hmac.new(secret_bytes, material, hashlib.sha256).digest()
        encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        return f"api_validation:v3:{encoded}"

    async def _validate_googlemaps_key(self, key_value: str) -> ApiValidationResult:
        """Validate Google Maps API key with HTTP request."""
        if len(key_value) < 20:
            return ApiValidationResult(
                is_valid=False,
                status=ValidationStatus.FORMAT_ERROR,
                service=ServiceType.GOOGLEMAPS,
                message="Google Maps API key too short",
            )

        try:
            response = await self.client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={
                    "address": "1600 Amphitheatre Parkway, Mountain View, CA",
                    "key": key_value,
                },
                timeout=self.validation_timeout,
            )

            data = response.json()
            status = data.get("status", "")

            if status == "OK":
                return ApiValidationResult(
                    is_valid=True,
                    status=ValidationStatus.VALID,
                    service=ServiceType.GOOGLEMAPS,
                    message="Google Maps API key is valid",
                    capabilities=["geocoding", "places", "directions"],
                    details={"status": status},
                )
            elif status == "REQUEST_DENIED":
                return ApiValidationResult(
                    is_valid=False,
                    status=ValidationStatus.INVALID,
                    service=ServiceType.GOOGLEMAPS,
                    message="Invalid API key",
                )
            elif status == "OVER_QUERY_LIMIT":
                return ApiValidationResult(
                    is_valid=False,
                    status=ValidationStatus.RATE_LIMITED,
                    service=ServiceType.GOOGLEMAPS,
                    message="Query limit exceeded",
                )
            else:
                return ApiValidationResult(
                    is_valid=False,
                    status=ValidationStatus.SERVICE_ERROR,
                    service=ServiceType.GOOGLEMAPS,
                    message=f"API returned status: {status}",
                )
        except httpx.TimeoutException:
            return ApiValidationResult(
                is_valid=False,
                status=ValidationStatus.SERVICE_ERROR,
                service=ServiceType.GOOGLEMAPS,
                message="Validation request timed out",
            )

    def _validate_generic_key(
        self, service: ServiceType, key_value: str
    ) -> ApiValidationResult:
        """Generic validation for services without specific implementation."""
        if len(key_value) < 10:
            return ApiValidationResult(
                is_valid=False,
                status=ValidationStatus.FORMAT_ERROR,
                service=service,
                message="API key too short",
            )

        return ApiValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            service=service,
            message="API key accepted (generic validation)",
            details={"validation_type": "generic", "key_length": len(key_value)},
        )

    async def _check_service_health_generic(
        self, service: ServiceType
    ) -> ApiValidationResult:
        """Generic health check for services."""
        start_time = datetime.now(UTC)

        # Simple connectivity check - try to reach the service endpoint
        health_endpoints = {
            ServiceType.OPENAI: "https://api.openai.com/v1/models",
            ServiceType.WEATHER: "https://api.openweathermap.org/data/2.5/weather",
            ServiceType.GOOGLEMAPS: "https://maps.googleapis.com/maps/api/geocode/json",
        }

        endpoint = health_endpoints.get(service)
        if not endpoint:
            return ApiValidationResult(
                service=service,
                is_valid=None,
                status=None,
                health_status=ServiceHealthStatus.UNKNOWN,
                message="Health check not implemented",
                latency_ms=0,
                validated_at=None,
                checked_at=datetime.now(UTC),
            )

        try:
            # Quick health check with invalid credentials to test connectivity
            params = {"q": "test"} if "openweathermap" in endpoint else {}
            if "googleapis" in endpoint:
                params = {"address": "test", "key": "invalid"}

            response = await self.client.get(endpoint, params=params, timeout=5)
            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            # If we get any response (even 401/403), service is reachable
            if response.status_code in [200, 401, 403, 429]:
                return ApiValidationResult(
                    service=service,
                    is_valid=None,
                    status=None,
                    health_status=ServiceHealthStatus.HEALTHY,
                    message="Service is reachable",
                    latency_ms=latency_ms,
                    validated_at=None,
                    checked_at=datetime.now(UTC),
                )
            else:
                return ApiValidationResult(
                    service=service,
                    is_valid=None,
                    status=None,
                    health_status=ServiceHealthStatus.DEGRADED,
                    message=f"Unexpected status: {response.status_code}",
                    latency_ms=latency_ms,
                    validated_at=None,
                    checked_at=datetime.now(UTC),
                )
        except httpx.TimeoutException:
            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
            return ApiValidationResult(
                service=service,
                is_valid=None,
                status=None,
                health_status=ServiceHealthStatus.UNHEALTHY,
                message="Service timeout",
                latency_ms=latency_ms,
                validated_at=None,
                checked_at=datetime.now(UTC),
            )
        except RECOVERABLE_ERRORS as error:
            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
            return ApiValidationResult(
                service=service,
                is_valid=None,
                status=None,
                health_status=ServiceHealthStatus.UNHEALTHY,
                message=f"Health check error: {error!s}",
                latency_ms=latency_ms,
                validated_at=None,
                checked_at=datetime.now(UTC),
            )

    async def _audit_key_creation(
        self,
        key_id: str,
        user_id: str,
        key_data: ApiKeyCreateRequest,
        validation_result: ApiValidationResult,
    ) -> None:
        """Fire-and-forget audit logging for key creation."""
        try:
            await audit_api_key(
                event_type=AuditEventType.API_KEY_CREATED,
                outcome=AuditOutcome.SUCCESS,
                key_id=key_id,
                service=self._get_service_value(key_data.service),
                ip_address="127.0.0.1",
                message=(
                    f"API key created for service "
                    f"{self._get_service_value(key_data.service)}"
                ),
                key_name=key_data.name,
                user_id=user_id,
                validation_result=validation_result.is_valid,
            )
        except RECOVERABLE_ERRORS as error:
            logger.warning("Audit logging failed for key creation: %s", error)

    async def _audit_key_deletion(
        self, key_id: str, user_id: str, key_data: dict[str, Any]
    ) -> None:
        """Fire-and-forget audit logging for key deletion."""
        try:
            await audit_api_key(
                event_type=AuditEventType.API_KEY_DELETED,
                outcome=AuditOutcome.SUCCESS,
                key_id=key_id,
                service=key_data["service"],
                ip_address="127.0.0.1",
                message=f"API key deleted for service {key_data['service']}",
                user_id=user_id,
            )
        except RECOVERABLE_ERRORS as error:
            logger.warning("Audit logging failed for key deletion: %s", error)

    def _db_result_to_response(self, result: dict[str, Any]) -> ApiKeyResponse:
        """Convert database result to modern response model with optimized parsing.

        Uses efficient datetime parsing and optimized field access patterns
        for better performance with large datasets.

        Args:
            result: Database query result dictionary

        Returns:
            Optimized ApiKeyResponse instance
        """
        # Pre-process datetime fields for efficiency
        datetime_fields = {
            "created_at": result["created_at"],
            "updated_at": result["updated_at"],
            "expires_at": result.get("expires_at"),
            "last_used": result.get("last_used"),
            "last_validated": result.get("last_validated"),
        }

        # Convert datetime strings efficiently
        parsed_datetimes = {
            key: datetime.fromisoformat(value) if value else None
            for key, value in datetime_fields.items()
        }

        created = parsed_datetimes["created_at"] or datetime.now(UTC)
        updated = parsed_datetimes["updated_at"] or datetime.now(UTC)

        return ApiKeyResponse(
            id=result["id"],
            name=result["name"],
            service=ServiceType(result["service"]),
            description=result.get("description"),
            is_valid=result["is_valid"],
            created_at=created,
            updated_at=updated,
            expires_at=parsed_datetimes["expires_at"],
            last_used=parsed_datetimes["last_used"],
            last_validated=parsed_datetimes["last_validated"],
            usage_count=result["usage_count"],
        )


# Dependency functions for FastAPI


async def get_api_key_service(
    db: Annotated[ApiKeyDatabaseProtocol, Depends(get_database_service)],
    cache: Annotated[Optional["CacheService"], Depends(get_cache_service)] = None,
) -> ApiKeyService:
    """Dependency injection for ApiKeyService.

    Args:
        db: Database service (injected)
        cache: Cache service (injected, optional)

    Returns:
        Configured ApiKeyService instance
    """
    return ApiKeyService(db=db, cache=cache)


# Type alias for easier use in endpoints
ApiKeyServiceDep = Annotated[ApiKeyService, Depends(get_api_key_service)]
