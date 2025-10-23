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
import logging
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, Optional

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
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tripsage_core.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditOutcome,
    audit_api_key,
)
from tripsage_core.services.infrastructure.cache_service import (
    get_cache_service,
)
from tripsage_core.services.infrastructure.database_service import (
    get_database_service,
)


if TYPE_CHECKING:
    from tripsage_core.config import Settings
    from tripsage_core.services.infrastructure.cache_service import CacheService
    from tripsage_core.services.infrastructure.database_service import DatabaseService


logger = logging.getLogger(__name__)

RECOVERABLE_ERRORS = (
    ServiceError,
    httpx.HTTPError,
    asyncio.TimeoutError,
    ConnectionError,
    ValueError,
    RuntimeError,
)

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
        if self.is_valid is True:
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


class ApiKeyService:
    """Simplified API key service for TripSage following KISS principles.

    Provides key management, validation, and security features with clean
    dependency injection and atomic operations.
    """

    def __init__(
        self,
        db: "DatabaseService",
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
        self.db = db
        self.cache = cache
        self.validation_timeout = validation_timeout

        # Use settings or get defaults
        if settings is None:
            from tripsage_core.config import get_settings

            settings = get_settings()

        # Initialize encryption with settings
        self._initialize_encryption(settings.secret_key.get_secret_value())

        # HTTP client with simple configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(validation_timeout),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
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
            validation_result = await self.validate_api_key(
                key_data.service, key_data.key_value
            )

            # Generate secure key ID and encrypt key
            key_id = str(uuid.uuid4())
            encrypted_key = self._encrypt_api_key(key_data.key_value)

            # Prepare database entry
            now = datetime.now(UTC)
            db_key_data = {
                "id": key_id,
                "user_id": user_id,
                "name": key_data.name,
                "service": self._get_service_value(key_data.service),
                "encrypted_key": encrypted_key,
                "description": key_data.description,
                "is_valid": validation_result.is_valid,
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

            # Atomic transaction: create key + log operation
            async with self.db.transaction() as tx:
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
                results = await tx.execute()

            result = results[0][0]  # First operation (create_api_key) result

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

    async def list_user_keys(self, user_id: str) -> list[ApiKeyResponse]:
        """Get all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            List of user's API keys
        """
        results = await self.db.get_user_api_keys(user_id)
        return [self._db_result_to_response(result) for result in results]

    async def get_api_key(self, key_id: str, user_id: str) -> dict[str, Any] | None:
        """Get a specific API key by ID.

        Args:
            key_id: API key ID
            user_id: User ID for ownership verification

        Returns:
            API key data if found and owned by user, None otherwise
        """
        return await self.db.get_api_key_by_id(key_id, user_id)

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
        result = await self.db.get_api_key_for_service(
            user_id, self._get_service_value(service)
        )
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
        asyncio.create_task(  # noqa: RUF006
            self.db.update_api_key_last_used(result["id"])
        )

        return decrypted_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True,
    )
    async def validate_api_key(
        self,
        service: ServiceType,
        key_value: str,
        user_id: str | None = None,
    ) -> ApiValidationResult:
        """Validate an API key with retry patterns and caching.

        This method implements a robust validation pipeline:
        1. Checks cache for recent validation results (5-minute TTL)
        2. Performs service-specific validation with proper retry logic
        3. Handles various response codes and error conditions
        4. Caches successful validations for performance
        5. Returns detailed validation metadata including capabilities

        The validation uses tenacity for retry logic with exponential backoff
        on network errors (TimeoutException, ConnectError) with up to 3 attempts.

        Args:
            service: The service type to validate against. Determines which
                validation endpoint and format checks are applied.
            key_value: The API key value to validate. Must meet minimum
                length requirements (8+ characters generally, service-specific
                format requirements for some services).
            user_id: Optional user identifier for audit logging and rate
                limiting. When provided, enables user-specific tracking.

        Returns:
            ApiValidationResult: Validation response containing:
                - is_valid: Boolean validation status
                - status: Detailed status (VALID, INVALID, RATE_LIMITED, etc.)
                - message: Human-readable validation message
                - latency_ms: Validation request latency
                - capabilities: List of detected API capabilities
                - rate_limit_info: Rate limiting metadata (if applicable)
                - quota_info: Usage quota information (if available)
                - details: Service-specific validation details

        Note:
            This method is decorated with @retry for automatic retry on
            network failures. The retry policy uses exponential backoff
            with a maximum of 3 attempts and delays between 1-10 seconds.

        Example:
            >>> result = await service.validate_api_key(
            ...     ServiceType.OPENAI, "sk-...", "user-123"
            ... )
            >>> if result.is_valid:
            ...     print(f"Valid key with capabilities: {result.capabilities}")
            >>> else:
            ...     print(f"Validation failed: {result.message}")
        """
        start_time = datetime.now(UTC)

        try:
            # Check cache for recent validation
            if self.cache:
                cached_result = await self._get_cached_validation(service, key_value)
                if cached_result:
                    return cached_result

            # Perform service-specific validation
            if service == ServiceType.OPENAI:
                result = await self._validate_openai_key(key_value)
            elif service == ServiceType.WEATHER:
                result = await self._validate_weather_key(key_value)
            elif service == ServiceType.GOOGLEMAPS:
                result = await self._validate_googlemaps_key(key_value)
            elif service == ServiceType.FLIGHTS:
                result = await self._validate_flights_key(key_value)
            else:
                result = await self._validate_generic_key(service, key_value)

            # Calculate latency and create new result with latency included
            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            # Create new ApiValidationResult with latency (since original is frozen)
            result_with_latency = ApiValidationResult(
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

            # Cache successful validation
            if result_with_latency.is_valid and self.cache:
                await self._cache_validation_result(
                    service, key_value, result_with_latency
                )

            return result_with_latency

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

    async def _request_with_backoff(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """Execute HTTP requests with backoff helper and safe fallback."""
        try:
            from tripsage_core.utils.outbound import request_with_backoff

            return await request_with_backoff(self.client, method, url, **kwargs)
        except (RuntimeError, ImportError) as error:
            logger.warning(
                "request_with_backoff unavailable; using direct client call",
                extra={"error": str(error), "url": url},
            )
            client_method = getattr(self.client, method.lower())
            try:
                return await client_method(url, **kwargs)
            except Exception as request_error:  # noqa: BLE001
                raise httpx.HTTPError(str(request_error)) from request_error

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
            if service == ServiceType.OPENAI:
                return await self._check_openai_health()
            if service == ServiceType.WEATHER:
                return await self._check_weather_health()
            if service == ServiceType.GOOGLEMAPS:
                return await self._check_googlemaps_health()
            return ApiValidationResult(
                service=service,
                is_valid=None,
                status=None,
                health_status=ServiceHealthStatus.UNKNOWN,
                message="Health check not implemented for this service",
                latency_ms=0,
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
                message=f"Health check failed: {error!s}",
                details={"error": str(error)},
                latency_ms=latency_ms,
                validated_at=None,
                checked_at=datetime.now(UTC),
            )

    async def check_all_services_health(self) -> dict[ServiceType, ApiValidationResult]:
        """Check health of all supported services concurrently.

        Returns:
            Dictionary of service health check results
        """
        services = [ServiceType.OPENAI, ServiceType.WEATHER, ServiceType.GOOGLEMAPS]

        # Run health checks concurrently
        tasks = [self.check_service_health(service) for service in services]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        health_status: dict[ServiceType, ApiValidationResult] = {}
        for service, result in zip(services, results, strict=False):
            if isinstance(result, ApiValidationResult):
                health_status[service] = result
            else:
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

        return health_status

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

        # Atomic transaction: delete key + log operation
        now = datetime.now(UTC)
        async with self.db.transaction() as tx:
            tx.delete("api_keys", {"id": key_id, "user_id": user_id})
            tx.insert(
                "api_key_usage_logs",
                {
                    "key_id": key_id,
                    "user_id": user_id,
                    "service": key_data["service"],
                    "operation": "delete",
                    "timestamp": now.isoformat(),
                    "success": True,
                },
            )
            results = await tx.execute()

        success = len(results[0]) > 0  # Check if deletion was successful

        if success:
            # Audit log (fire-and-forget)
            asyncio.create_task(  # noqa: RUF006
                self._audit_key_deletion(key_id, user_id, key_data)
            )

            logger.info(
                "API key deleted",
                extra={
                    "key_id": key_id,
                    "user_id": user_id,
                    "service": key_data["service"],
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

    async def _validate_openai_key(self, key_value: str) -> ApiValidationResult:
        """Validate OpenAI API key with optimized error handling.

        Args:
            key_value: The API key to validate

        Returns:
            ApiValidationResult with validation data
        """
        # Fast format validation
        if not key_value.startswith("sk-"):
            return ApiValidationResult(
                is_valid=False,
                status=ValidationStatus.FORMAT_ERROR,
                service=ServiceType.OPENAI,
                message="Invalid OpenAI key format (should start with 'sk-')",
            )

        try:
            response = await self._request_with_backoff(
                "GET",
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key_value}"},
                timeout=self.validation_timeout,
            )

            # Optimized response handling with early returns
            if response.status_code == 401:
                return ApiValidationResult(
                    is_valid=False,
                    status=ValidationStatus.INVALID,
                    service=ServiceType.OPENAI,
                    message="Invalid API key - authentication failed",
                )

            if response.status_code == 429:
                return self._handle_rate_limit_response(response, ServiceType.OPENAI)

            if response.status_code == 200:
                return self._process_openai_success_response(response)

            # Default error case
            return ApiValidationResult(
                is_valid=False,
                status=ValidationStatus.SERVICE_ERROR,
                service=ServiceType.OPENAI,
                message=f"Unexpected response: {response.status_code}",
                details={"status_code": response.status_code},
            )

        except httpx.TimeoutException:
            return ApiValidationResult(
                is_valid=False,
                status=ValidationStatus.SERVICE_ERROR,
                service=ServiceType.OPENAI,
                message="Validation request timed out",
            )

    async def _validate_weather_key(self, key_value: str) -> ApiValidationResult:
        """Validate weather API key."""
        if len(key_value) < 16:
            return ApiValidationResult(
                is_valid=False,
                status=ValidationStatus.FORMAT_ERROR,
                service=ServiceType.WEATHER,
                message="Weather API key too short (minimum 16 characters)",
            )

        try:
            response = await self._request_with_backoff(
                "GET",
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": "London", "appid": key_value},
                timeout=self.validation_timeout,
            )

            if response.status_code == 200:
                data = response.json()

                # Extract quota information if available
                quota_info = {}
                if "X-RateLimit-Limit" in response.headers:
                    quota_info = {
                        "limit": response.headers.get("X-RateLimit-Limit"),
                        "remaining": response.headers.get("X-RateLimit-Remaining"),
                    }

                return ApiValidationResult(
                    is_valid=True,
                    status=ValidationStatus.VALID,
                    service=ServiceType.WEATHER,
                    message="Weather API key is valid",
                    quota_info=quota_info,
                    capabilities=["current", "forecast", "historical"],
                    details={
                        "api_version": "2.5",
                        "test_location": data.get("name"),
                    },
                )

            elif response.status_code == 401:
                return ApiValidationResult(
                    is_valid=False,
                    status=ValidationStatus.INVALID,
                    service=ServiceType.WEATHER,
                    message="Invalid API key",
                )

            elif response.status_code == 429:
                return ApiValidationResult(
                    is_valid=False,
                    status=ValidationStatus.RATE_LIMITED,
                    service=ServiceType.WEATHER,
                    message="API rate limit exceeded",
                )

            else:
                return ApiValidationResult(
                    is_valid=False,
                    status=ValidationStatus.SERVICE_ERROR,
                    service=ServiceType.WEATHER,
                    message=f"Unexpected response: {response.status_code}",
                )

        except httpx.TimeoutException:
            return ApiValidationResult(
                is_valid=False,
                status=ValidationStatus.SERVICE_ERROR,
                service=ServiceType.WEATHER,
                message="Validation request timed out",
            )

    async def _validate_googlemaps_key(self, key_value: str) -> ApiValidationResult:
        """Validate Google Maps API key."""
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
                # Capability checking
                capabilities = await self._check_googlemaps_capabilities(key_value)

                return ApiValidationResult(
                    is_valid=True,
                    status=ValidationStatus.VALID,
                    service=ServiceType.GOOGLEMAPS,
                    message="Google Maps API key is valid",
                    capabilities=capabilities,
                    details={
                        "apis_tested": ["geocoding"],
                        "status": status,
                    },
                )

            elif status == "REQUEST_DENIED":
                error_message = data.get("error_message", "API key is invalid")
                return ApiValidationResult(
                    is_valid=False,
                    status=ValidationStatus.INVALID,
                    service=ServiceType.GOOGLEMAPS,
                    message=f"Invalid API key: {error_message}",
                    details={"error": error_message},
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
                    details={"status": status},
                )

        except httpx.TimeoutException:
            return ApiValidationResult(
                is_valid=False,
                status=ValidationStatus.SERVICE_ERROR,
                service=ServiceType.GOOGLEMAPS,
                message="Validation request timed out",
            )

    async def _validate_flights_key(self, key_value: str) -> ApiValidationResult:
        """Validate flights API key (placeholder for specific implementation)."""
        return await self._validate_generic_key(ServiceType.FLIGHTS, key_value)

    async def _validate_generic_key(
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

        # Generic validation
        return ApiValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            service=service,
            message="API key accepted (generic validation)",
            details={"validation_type": "generic", "key_length": len(key_value)},
        )

    async def _check_openai_health(self) -> ApiValidationResult:
        """Check OpenAI service health."""
        start_time = datetime.now(UTC)

        try:
            response = await self.client.get(
                "https://status.openai.com/api/v2/status.json",
                timeout=5,  # Quick health check
            )

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            if response.status_code == 200:
                data = response.json()
                status_indicator = data.get("status", {}).get("indicator", "none")

                if status_indicator == "none":
                    health_status = ServiceHealthStatus.HEALTHY
                elif status_indicator == "minor":
                    health_status = ServiceHealthStatus.DEGRADED
                else:
                    health_status = ServiceHealthStatus.UNHEALTHY

                return ApiValidationResult(
                    service=ServiceType.OPENAI,
                    is_valid=None,
                    status=None,
                    health_status=health_status,
                    latency_ms=latency_ms,
                    message=data.get("status", {}).get("description", "Unknown"),
                    details={
                        "indicator": status_indicator,
                        "updated_at": data.get("page", {}).get("updated_at"),
                    },
                    validated_at=None,
                    checked_at=datetime.now(UTC),
                )

            return ApiValidationResult(
                service=ServiceType.OPENAI,
                is_valid=None,
                status=None,
                health_status=ServiceHealthStatus.UNKNOWN,
                latency_ms=latency_ms,
                message=f"Status check returned {response.status_code}",
                validated_at=None,
                checked_at=datetime.now(UTC),
            )

        except RECOVERABLE_ERRORS as error:
            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return ApiValidationResult(
                service=ServiceType.OPENAI,
                is_valid=None,
                status=None,
                health_status=ServiceHealthStatus.UNKNOWN,
                latency_ms=latency_ms,
                message=f"Health check error: {error!s}",
                details={"error": str(error)},
                validated_at=None,
                checked_at=datetime.now(UTC),
            )

    async def _check_weather_health(self) -> ApiValidationResult:
        """Check weather service health."""
        start_time = datetime.now(UTC)

        try:
            response = await self.client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": "London", "appid": "invalid"},
                timeout=5,
            )

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            # Service is healthy if it returns 401 (unauthorized) - means it's up
            if response.status_code in [200, 401]:
                return ApiValidationResult(
                    service=ServiceType.WEATHER,
                    is_valid=None,
                    status=None,
                    health_status=ServiceHealthStatus.HEALTHY,
                    latency_ms=latency_ms,
                    message="Weather API is operational",
                    validated_at=None,
                    checked_at=datetime.now(UTC),
                )

            return ApiValidationResult(
                service=ServiceType.WEATHER,
                is_valid=None,
                status=None,
                health_status=ServiceHealthStatus.DEGRADED,
                latency_ms=latency_ms,
                message=f"Unexpected status code: {response.status_code}",
                details={"status_code": response.status_code},
                validated_at=None,
                checked_at=datetime.now(UTC),
            )

        except httpx.TimeoutException:
            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return ApiValidationResult(
                service=ServiceType.WEATHER,
                is_valid=None,
                status=None,
                health_status=ServiceHealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message="Service timeout",
                validated_at=None,
                checked_at=datetime.now(UTC),
            )

    async def _check_googlemaps_health(self) -> ApiValidationResult:
        """Check Google Maps service health."""
        start_time = datetime.now(UTC)

        try:
            response = await self.client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": "test", "key": "invalid"},
                timeout=5,
            )

            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            # Service is healthy if it returns proper error response
            if response.status_code == 200:
                data = response.json()
                if data.get("status") in ["REQUEST_DENIED", "INVALID_REQUEST"]:
                    return ApiValidationResult(
                        service=ServiceType.GOOGLEMAPS,
                        is_valid=None,
                        status=None,
                        health_status=ServiceHealthStatus.HEALTHY,
                        latency_ms=latency_ms,
                        message="Google Maps API is operational",
                        validated_at=None,
                        checked_at=datetime.now(UTC),
                    )

            return ApiValidationResult(
                service=ServiceType.GOOGLEMAPS,
                is_valid=None,
                status=None,
                health_status=ServiceHealthStatus.DEGRADED,
                latency_ms=latency_ms,
                message="Service may be experiencing issues",
                validated_at=None,
                checked_at=datetime.now(UTC),
            )

        except httpx.TimeoutException:
            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return ApiValidationResult(
                service=ServiceType.GOOGLEMAPS,
                is_valid=None,
                status=None,
                health_status=ServiceHealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message="Service timeout",
                validated_at=None,
                checked_at=datetime.now(UTC),
            )

    async def _check_googlemaps_capabilities(self, key_value: str) -> list[str]:
        """Check which Google Maps APIs are enabled for a key."""
        capabilities = []

        # Test different APIs with quick timeouts
        api_tests = [
            ("geocoding", "geocode/json", {"address": "test"}),
            ("places", "place/nearbysearch/json", {"location": "0,0", "radius": 1}),
            ("directions", "directions/json", {"origin": "A", "destination": "B"}),
        ]

        for capability, endpoint, params in api_tests:
            try:
                response = await self.client.get(
                    f"https://maps.googleapis.com/maps/api/{endpoint}",
                    params={**params, "key": key_value},
                    timeout=2,
                )

                data = response.json()
                # If we get OK or a specific error (not REQUEST_DENIED), API is enabled
                if data.get("status") != "REQUEST_DENIED":
                    capabilities.append(capability)

            except (
                TimeoutError,
                httpx.HTTPError,
                ValueError,
                ConnectionError,
                RuntimeError,
            ):
                # Ignore errors in capability checking
                pass

        return capabilities

    def _handle_rate_limit_response(
        self, response: httpx.Response, service: ServiceType
    ) -> ApiValidationResult:
        """Handle rate limit responses efficiently.

        Args:
            response: HTTP response object
            service: Service type being validated

        Returns:
            ApiValidationResult for rate limit scenario
        """
        headers = response.headers
        return ApiValidationResult(
            is_valid=False,
            status=ValidationStatus.RATE_LIMITED,
            service=service,
            message="Rate limit exceeded",
            rate_limit_info={
                "retry_after": headers.get("retry-after"),
                "limit": headers.get("x-ratelimit-limit"),
                "remaining": headers.get("x-ratelimit-remaining"),
                "reset": headers.get("x-ratelimit-reset"),
            },
        )

    def _process_openai_success_response(
        self, response: httpx.Response
    ) -> ApiValidationResult:
        """Process successful OpenAI API response efficiently.

        Args:
            response: Successful HTTP response from OpenAI

        Returns:
            ApiValidationResult with model capabilities
        """
        data = response.json()
        models = [model["id"] for model in data.get("data", [])]

        # Optimized capability detection using sets
        model_set = set(models)
        capabilities = []

        capability_checks = [
            ("gpt-4", lambda: any("gpt-4" in model for model in model_set)),
            ("gpt-3.5", lambda: any("gpt-3.5" in model for model in model_set)),
            ("image-generation", lambda: any("dall-e" in model for model in model_set)),
        ]

        for capability, check_func in capability_checks:
            if check_func():
                capabilities.append(capability)

        return ApiValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            service=ServiceType.OPENAI,
            message="OpenAI API key is valid",
            capabilities=capabilities,
            details={
                "models_available": len(models),
                "sample_models": models[:5],
            },
        )

    async def _get_cached_validation(
        self, service: ServiceType, key_value: str
    ) -> ApiValidationResult | None:
        """Get cached validation result if available using optimized JSON validation."""
        if not self.cache:
            return None

        try:
            # Create secure cache key
            key_hash = hashlib.sha256(
                f"{self._get_service_value(service)}:{key_value}".encode()
            ).hexdigest()
            cache_key = f"api_validation:v3:{key_hash}"  # v3 for new optimizations

            cached_data = await self.cache.get(cache_key)
            if cached_data:
                # Use Pydantic V2 optimized JSON validation
                return ApiValidationResult.model_validate_json(cached_data)

        except RECOVERABLE_ERRORS as error:
            logger.warning("Cache retrieval error: %s", error)

        return None

    async def _cache_validation_result(
        self, service: ServiceType, key_value: str, result: ApiValidationResult
    ) -> None:
        """Cache validation result with optimized JSON serialization."""
        if not self.cache:
            return

        try:
            key_hash = hashlib.sha256(
                f"{self._get_service_value(service)}:{key_value}".encode()
            ).hexdigest()
            cache_key = f"api_validation:v3:{key_hash}"  # v3 for new optimizations

            # Use Pydantic V2 optimized JSON serialization
            from typing import cast

            await cast(Any, self.cache).set(
                cache_key,
                result.model_dump_json(),  # Direct JSON serialization
                ex=300,  # Cache for 5 minutes
            )

        except RECOVERABLE_ERRORS as error:
            logger.warning("Cache storage error: %s", error)

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
                ip_address="127.0.0.1",  # Note: extract from request context
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
    db: Annotated["DatabaseService", Depends(get_database_service)],
    cache: Annotated[Optional["CacheService"], Depends(get_cache_service)] = None,
) -> ApiKeyService:
    """Modern dependency injection for ApiKeyService.

    Args:
        db: Database service (injected)
        cache: Cache service (injected, optional)

    Returns:
        Configured ApiKeyService instance
    """
    return ApiKeyService(db=db, cache=cache)


# Type alias for easier use in endpoints
ApiKeyServiceDep = Annotated[ApiKeyService, Depends(get_api_key_service)]
