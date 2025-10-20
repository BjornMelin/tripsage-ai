"""Database connection utilities with security hardening and robust error handling.

This module provides secure URL parsing, connection validation, and retry logic
for database connections, specifically designed for PostgreSQL/Supabase integration.
"""

import asyncio
import logging
import secrets
import time
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any
from urllib.parse import ParseResult, quote_plus, unquote_plus, urlparse

from pydantic import BaseModel, Field, ValidationError


logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class DatabaseURLParsingError(Exception):
    """Raised when database URL parsing fails."""


class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""


class DatabaseValidationError(Exception):
    """Raised when database connection validation fails."""


class ConnectionCredentials(BaseModel):
    """Secure model for database connection credentials."""

    scheme: str = Field(..., description="Database scheme (postgresql, postgres)")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    hostname: str = Field(..., description="Database hostname")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    database: str = Field(default="postgres", description="Database name")
    query_params: dict[str, str] = Field(
        default_factory=dict, description="Query parameters"
    )

    class Config:
        """Pydantic configuration."""

        frozen = True

    def to_connection_string(self, mask_password: bool = False) -> str:
        """Convert credentials to connection string.

        Args:
            mask_password: Whether to mask the password in the output

        Returns:
            Database connection string
        """
        password = "***MASKED***" if mask_password else quote_plus(self.password)
        encoded_username = quote_plus(self.username)

        url = f"{self.scheme}://{encoded_username}:{password}@{self.hostname}:{self.port}/{self.database}"

        if self.query_params:
            query_string = "&".join(
                [
                    f"{quote_plus(k)}={quote_plus(v)}"
                    for k, v in self.query_params.items()
                ]
            )
            url += f"?{query_string}"

        return url

    def sanitized_for_logging(self) -> str:
        """Get sanitized connection string safe for logging."""
        return self.to_connection_string(mask_password=True)


class DatabaseURLParser:
    """Secure database URL parser with comprehensive validation.

    This parser handles PostgreSQL connection URLs with proper security
    validation, special character encoding, and error handling.
    """

    VALID_SCHEMES = frozenset(["postgresql", "postgres"])

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse_url(self, url: str) -> ConnectionCredentials:
        """Parse database URL into secure credentials object.

        Args:
            url: Database connection URL to parse

        Returns:
            Parsed and validated connection credentials

        Raises:
            DatabaseURLParsingError: If URL parsing fails
            ValidationError: If parsed components are invalid
        """
        try:
            self._validate_url_security(url)
            parsed = urlparse(url)

            # Extract and validate components
            components = self._extract_components(parsed)

            # Create validated credentials object
            credentials = ConnectionCredentials(**components)

            self.logger.debug(
                "Successfully parsed database URL for hostname: %s",
                credentials.hostname,
            )

            return credentials

        except ValidationError as e:
            error_msg = f"Invalid database URL components: {e}"
            self.logger.exception(error_msg)
            raise DatabaseURLParsingError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to parse database URL: {e}"
            self.logger.exception(error_msg)
            raise DatabaseURLParsingError(error_msg) from e

    def _validate_url_security(self, url: str) -> None:
        """Validate URL for security issues.

        Args:
            url: URL to validate

        Raises:
            DatabaseURLParsingError: If URL fails security validation
        """
        if not url or not isinstance(url, str):
            raise DatabaseURLParsingError("URL must be a non-empty string")

        # Check for leading/trailing whitespace (CVE-2023-24329 mitigation)
        if url != url.strip():
            raise DatabaseURLParsingError("URL contains leading/trailing whitespace")

        # Check for control characters
        import re

        if re.search(r"[\x00-\x1f\x7f-\x9f]", url):
            raise DatabaseURLParsingError("URL contains suspicious control characters")

        # Basic URL structure validation
        if "://" not in url:
            raise DatabaseURLParsingError("URL must contain scheme separator '://'")

    def _extract_components(self, parsed: ParseResult) -> dict[str, Any]:
        """Extract and validate URL components.

        Args:
            parsed: Parsed URL result

        Returns:
            Dictionary of validated components

        Raises:
            DatabaseURLParsingError: If components are invalid
        """
        # Validate scheme
        if not parsed.scheme or parsed.scheme.lower() not in self.VALID_SCHEMES:
            schemes_list = ", ".join(self.VALID_SCHEMES)
            raise DatabaseURLParsingError(
                f"Invalid scheme '{parsed.scheme}'. Must be one of: {schemes_list}"
            )

        # Validate hostname
        if not parsed.hostname:
            raise DatabaseURLParsingError("Hostname is required")

        # Validate username
        if not parsed.username:
            raise DatabaseURLParsingError("Username is required")

        # Validate password
        if not parsed.password:
            raise DatabaseURLParsingError("Password is required")

        # Extract database name
        database = "postgres"  # Default
        if parsed.path and len(parsed.path) > 1:
            database = unquote_plus(parsed.path[1:])  # Remove leading slash and decode

        # Parse query parameters
        query_params = {}
        if parsed.query:
            for param in parsed.query.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    query_params[unquote_plus(key)] = unquote_plus(value)
                else:
                    query_params[unquote_plus(param)] = ""

        return {
            "scheme": parsed.scheme.lower(),
            "username": unquote_plus(parsed.username),
            "password": unquote_plus(parsed.password),
            "hostname": parsed.hostname,
            "port": parsed.port or 5432,
            "database": database,
            "query_params": query_params,
        }


class ConnectionCircuitBreaker:
    """Circuit breaker for database connections to prevent cascade failures.

    Implements the circuit breaker pattern to protect against sustained
    database connection failures.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = ConnectionState.CLOSED
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def call(self, operation, *args, **kwargs):
        """Execute operation with circuit breaker protection.

        Args:
            operation: Async function to execute
            *args: Operation arguments
            **kwargs: Operation keyword arguments

        Returns:
            Operation result

        Raises:
            DatabaseConnectionError: If circuit is open
        """
        if self.state == ConnectionState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = ConnectionState.HALF_OPEN
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                failure_time = time.time() - self.last_failure_time
                raise DatabaseConnectionError(
                    f"Circuit breaker is OPEN - last failure {failure_time:.1f}s ago"
                )

        try:
            result = await operation(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful operation."""
        if self.state == ConnectionState.HALF_OPEN:
            self.logger.info("Circuit breaker closing after successful recovery")

        self.failure_count = 0
        self.state = ConnectionState.CLOSED

    def _on_failure(self) -> None:
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = ConnectionState.OPEN
            self.logger.exception(
                "Circuit breaker opening after %s failures", self.failure_count
            )


class ExponentialBackoffRetry:
    """Exponential backoff retry logic for database operations.

    Implements exponential backoff with jitter to prevent thundering herd
    problems during connection recovery.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        """Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Exponential backoff factor
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._random = secrets.SystemRandom()

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.backoff_factor**attempt)

        if self.jitter:
            jitter_amount = self._random.uniform(0, 0.1) * delay
            delay += jitter_amount

        return min(delay, self.max_delay)

    async def execute_with_retry(self, operation, *args, **kwargs):
        """Execute operation with exponential backoff retry.

        Args:
            operation: Async function to execute
            *args: Operation arguments
            **kwargs: Operation keyword arguments

        Returns:
            Operation result

        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                result = await operation(*args, **kwargs)
                if attempt > 0:
                    self.logger.info("Operation succeeded on attempt %s", attempt + 1)
                return result

            except Exception as e:
                last_exception = e

                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    self.logger.warning(
                        "Attempt %s failed, retrying in %.2fs: %s",
                        attempt + 1,
                        delay,
                        e,
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.exception(
                        "All %s attempts failed. Last error", self.max_retries + 1
                    )

        raise last_exception


class DatabaseConnectionValidator:
    """Database connection validator with health checks.

    Provides comprehensive connection validation including basic connectivity,
    extension availability, and performance checks.
    """

    def __init__(self, timeout: float = 10.0):
        """Initialize validator.

        Args:
            timeout: Connection timeout in seconds
        """
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def validate_connection(self, credentials: ConnectionCredentials) -> bool:
        """Validate database connection with comprehensive checks.

        Args:
            credentials: Database connection credentials

        Returns:
            True if connection is valid and healthy

        Raises:
            DatabaseValidationError: If validation fails
        """
        try:
            # Import here to avoid circular imports
            import asyncpg

            # Determine SSL mode
            ssl_mode = (
                "require"
                if credentials.query_params.get("sslmode") == "require"
                else "prefer"
            )

            # Create connection with timeout
            conn = await asyncio.wait_for(
                asyncpg.connect(
                    host=credentials.hostname,
                    port=credentials.port,
                    user=credentials.username,
                    password=credentials.password,
                    database=credentials.database,
                    ssl=ssl_mode,
                ),
                timeout=self.timeout,
            )

            try:
                # Basic connectivity test
                await conn.fetchval("SELECT 1")

                # Check PostgreSQL version
                version = await conn.fetchval("SELECT version()")
                self.logger.debug("Connected to: %s", version)

                # Check for pgvector extension (if needed for Mem0)
                has_vector = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )

                if has_vector:
                    self.logger.debug("pgvector extension is available")
                else:
                    self.logger.warning(
                        "pgvector extension not found - may impact vector operations"
                    )

                return True

            finally:
                await conn.close()

        except TimeoutError as e:
            error_msg = f"Connection validation timed out after {self.timeout}s"
            self.logger.exception(error_msg)
            raise DatabaseValidationError(error_msg) from e
        except Exception as e:
            error_msg = f"Connection validation failed: {e}"
            self.logger.exception(error_msg, extra={"hostname": credentials.hostname})
            raise DatabaseValidationError(error_msg) from e


class SecureDatabaseConnectionManager:
    """Comprehensive database connection manager with security and resilience.

    Combines URL parsing, validation, retry logic, and circuit breaking
    into a single, production-ready connection management solution.
    """

    def __init__(
        self,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: float = 60.0,
        validation_timeout: float = 10.0,
    ):
        """Initialize connection manager.

        Args:
            max_retries: Maximum retry attempts for operations
            circuit_breaker_threshold: Failures before opening circuit
            circuit_breaker_timeout: Circuit breaker recovery timeout
            validation_timeout: Connection validation timeout
        """
        self.url_parser = DatabaseURLParser()
        self.validator = DatabaseConnectionValidator(timeout=validation_timeout)
        self.retry_handler = ExponentialBackoffRetry(max_retries=max_retries)
        self.circuit_breaker = ConnectionCircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=circuit_breaker_timeout,
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def parse_and_validate_url(self, url: str) -> ConnectionCredentials:
        """Parse and validate database URL with full security checks.

        Args:
            url: Database connection URL

        Returns:
            Validated connection credentials

        Raises:
            DatabaseURLParsingError: If URL parsing fails
            DatabaseValidationError: If connection validation fails
        """
        # Parse URL securely
        credentials = self.url_parser.parse_url(url)

        # Validate connection with retry and circuit breaker
        async def validation_operation():
            return await self.validator.validate_connection(credentials)

        await self.circuit_breaker.call(
            self.retry_handler.execute_with_retry, validation_operation
        )

        self.logger.info(
            "Database URL parsed and validated successfully",
            extra={"hostname": credentials.hostname, "database": credentials.database},
        )

        return credentials

    @asynccontextmanager
    async def get_validated_connection(self, url: str):
        """Get validated database connection as async context manager.

        Args:
            url: Database connection URL

        Yields:
            Validated database connection

        Raises:
            DatabaseURLParsingError: If URL parsing fails
            DatabaseValidationError: If connection validation fails
            DatabaseConnectionError: If circuit breaker is open
        """
        credentials = await self.parse_and_validate_url(url)

        # Import here to avoid circular imports
        import asyncpg

        async def connect_operation():
            # Determine SSL mode
            ssl_mode = (
                "require"
                if credentials.query_params.get("sslmode") == "require"
                else "prefer"
            )

            return await asyncpg.connect(
                host=credentials.hostname,
                port=credentials.port,
                user=credentials.username,
                password=credentials.password,
                database=credentials.database,
                ssl=ssl_mode,
            )

        conn = await self.circuit_breaker.call(
            self.retry_handler.execute_with_retry, connect_operation
        )

        try:
            yield conn
        finally:
            await conn.close()


# Convenience functions for backward compatibility
async def parse_database_url(url: str) -> ConnectionCredentials:
    """Parse database URL with security validation.

    Args:
        url: Database connection URL

    Returns:
        Parsed and validated connection credentials
    """
    parser = DatabaseURLParser()
    return parser.parse_url(url)


async def validate_database_connection(url: str) -> bool:
    """Validate database connection.

    Args:
        url: Database connection URL

    Returns:
        True if connection is valid
    """
    manager = SecureDatabaseConnectionManager()
    try:
        await manager.parse_and_validate_url(url)
        return True
    except (DatabaseURLParsingError, DatabaseValidationError, DatabaseConnectionError):
        return False
