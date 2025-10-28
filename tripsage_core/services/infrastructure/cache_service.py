"""Cache service for TripSage Core using Upstash Redis (HTTP, asyncio).

Library-first implementation built on ``upstash-redis`` async client:
- Connectionless HTTP client ideal for Vercel serverless environments
- Simple, typed wrappers around core Redis commands we actually use
- JSON helpers via stdlib ``json`` only (KISS; no bespoke codecs)
- TTL support through ``SET ex=...`` and ``EXPIRE``
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from typing import cast

from upstash_redis.asyncio import Redis as UpstashRedis

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.types import JSONObject, JSONValue


def _coerce_json_value(value: object) -> JSONValue:
    """Coerce arbitrary objects into JSON-compatible values."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return {str(key): _coerce_json_value(val) for key, val in mapping.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        seq = cast(Sequence[object], value)
        return [_coerce_json_value(item) for item in seq]
    return str(value)


logger = logging.getLogger(__name__)


class CacheService:
    """Upstash Redis (HTTP) cache service for core caching operations.

    Notes:
    - Uses ``UpstashRedis.from_env()``; expects ``UPSTASH_REDIS_REST_URL`` and
      ``UPSTASH_REDIS_REST_TOKEN`` to be present in the environment (Vercel
      integration sets these automatically).
    - Upstash is connectionless; ``connect()`` simply validates credentials via
      a ``PING`` and stores the client for reuse across calls.
    - API surface is intentionally minimal and aligned to used features.
    """  # pylint: disable=too-many-public-methods

    def __init__(self, settings: Settings | None = None):
        """Initialize the cache service.

        Args:
            settings: Application settings or None to use defaults
        """
        self.settings = settings or get_settings()
        self._client: UpstashRedis | None = None
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Check if the client is initialized and validated."""
        return self._is_connected and self._client is not None

    def _require_client(self) -> UpstashRedis:
        """Return the initialized Upstash client or raise a service error.

        Returns:
            UpstashRedis: Initialized Upstash client.

        Raises:
            CoreServiceError: If the client is not connected/initialized.
        """
        if self._client is None:
            raise CoreServiceError(
                message="Cache service not connected",
                code="CACHE_NOT_CONNECTED",
                service="CacheService",
            )
        return self._client

    async def connect(self) -> None:
        """Initialize the Upstash client from environment and validate with PING."""
        if self._is_connected:
            return
        try:
            # Prefer explicit settings if provided; otherwise use environment.
            url: str | None = getattr(self.settings, "upstash_redis_rest_url", None)
            token: str | None = getattr(self.settings, "upstash_redis_rest_token", None)
            if url and token:
                self._client = UpstashRedis(url=url, token=token)
            else:
                # Instantiate client using env provided by Vercel/Upstash integration.
                self._client = UpstashRedis.from_env()
            # Validate credentials/connectivity.
            await self._client.ping()
            self._is_connected = True
            logger.info("Connected to Upstash Redis (HTTP)")
        except Exception as e:
            self._client = None
            self._is_connected = False
            logger.exception("Failed to initialize Upstash Redis client")
            raise CoreServiceError(
                message=f"Failed to connect to cache service: {e!s}",
                code="CACHE_CONNECTION_FAILED",
                service="CacheService",
                details={"error": str(e)},
            ) from e

    async def disconnect(self) -> None:
        """No-op for Upstash. Clears local client reference."""
        self._client = None
        self._is_connected = False

    async def ensure_connected(self) -> None:
        """Ensure the service is connected, reconnect if necessary."""
        if not self.is_connected:
            await self.connect()

    # JSON operations
    async def set_json(
        self, key: str, value: JSONValue, ttl: int | None = None
    ) -> bool:
        """Store a JSON-serializable value in cache.

        Args:
            key: Cache key
            value: Value to store (must be JSON-serializable)
            ttl: Time to live in seconds (uses default if not specified)

        Returns:
            True if successful, False otherwise
        """
        await self.ensure_connected()
        try:
            ttl_seconds = ttl if ttl is not None else 3600
            json_value = json.dumps(value, default=str)
            client = self._require_client()
            result = await client.set(key, json_value, ex=ttl_seconds)
            return bool(result)
        except Exception as e:
            logger.exception("Failed to set JSON value for key %s", key)
            raise CoreServiceError(
                message=f"Failed to set cache value for key '{key}'",
                code="CACHE_SET_FAILED",
                service="CacheService",
                details={"key": key, "error": str(e)},
            ) from e

    async def get_json(
        self, key: str, default: JSONValue | None = None
    ) -> JSONValue | None:
        """Retrieve and deserialize a JSON value from cache.

        Args:
            key: Cache key
            default: Default value if key doesn't exist

        Returns:
            Deserialized value or default
        """
        await self.ensure_connected()
        try:
            client = self._require_client()
            value = await client.get(key)
            if value is None:
                return default
            return cast(JSONValue, json.loads(value))
        except json.JSONDecodeError:
            logger.exception("Failed to decode JSON value for key %s", key)
            return default
        except Exception as e:
            logger.exception("Failed to get JSON value for key %s", key)
            raise CoreServiceError(
                message=f"Failed to get cache value for key '{key}'",
                code="CACHE_GET_FAILED",
                service="CacheService",
                details={"key": key, "error": str(e)},
            ) from e

    # String operations

    async def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        """Set a string value in cache.

        Args:
            key: Cache key
            value: String value to store
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        await self.ensure_connected()
        try:
            ttl_seconds = ttl if ttl is not None else 3600
            client = self._require_client()
            return bool(await client.set(key, value, ex=ttl_seconds))
        except Exception as e:
            logger.exception("Failed to set key %s", key)
            raise CoreServiceError(
                message=f"Failed to set cache key '{key}'",
                code="CACHE_SET_FAILED",
                service="CacheService",
                details={"key": key, "error": str(e)},
            ) from e

    async def get(self, key: str) -> str | None:
        """Get a string value from cache.

        Args:
            key: Cache key

        Returns:
            The value as string or None if not found
        """
        await self.ensure_connected()
        try:
            client = self._require_client()
            value = await client.get(key)
            if isinstance(value, (bytes, bytearray)):
                return value.decode("utf-8")
            return value
        except Exception as e:
            logger.exception("Failed to get key %s", key)
            raise CoreServiceError(
                message=f"Failed to get cache key '{key}'",
                code="CACHE_GET_FAILED",
                service="CacheService",
                details={"key": key, "error": str(e)},
            ) from e

    # Key operations

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys from cache.

        Args:
            keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        await self.ensure_connected()
        try:
            client = self._require_client()
            return int(await client.delete(*keys))
        except Exception as e:
            logger.exception("Failed to delete keys %s", keys)
            raise CoreServiceError(
                message="Failed to delete cache keys",
                code="CACHE_DELETE_FAILED",
                service="CacheService",
                details={"keys": keys, "error": str(e)},
            ) from e

    async def exists(self, *keys: str) -> int:
        """Check if keys exist in cache.

        Args:
            keys: Keys to check

        Returns:
            Number of existing keys
        """
        await self.ensure_connected()
        try:
            client = self._require_client()
            return int(await client.exists(*keys))
        except Exception as e:
            logger.exception("Failed to check existence of keys %s", keys)
            raise CoreServiceError(
                message="Failed to check cache key existence",
                code="CACHE_EXISTS_FAILED",
                service="CacheService",
                details={"keys": keys, "error": str(e)},
            ) from e

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for a key.

        Args:
            key: Cache key
            seconds: Expiration time in seconds

        Returns:
            True if successful, False otherwise
        """
        await self.ensure_connected()
        try:
            client = self._require_client()
            return bool(await client.expire(key, seconds))
        except Exception as e:
            logger.exception("Failed to set expiration for key %s", key)
            raise CoreServiceError(
                message=f"Failed to set expiration for cache key '{key}'",
                code="CACHE_EXPIRE_FAILED",
                service="CacheService",
                details={"key": key, "seconds": seconds, "error": str(e)},
            ) from e

    async def ttl(self, key: str) -> int:
        """Get time to live for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        await self.ensure_connected()
        try:
            client = self._require_client()
            return int(await client.ttl(key))
        except Exception as e:
            logger.exception("Failed to get TTL for key %s", key)
            raise CoreServiceError(
                message=f"Failed to get TTL for cache key '{key}'",
                code="CACHE_TTL_FAILED",
                service="CacheService",
                details={"key": key, "error": str(e)},
            ) from e

    # Atomic operations

    async def incr(self, key: str) -> int | None:
        """Increment a counter in cache.

        Args:
            key: Counter key

        Returns:
            The new counter value or None if failed
        """
        await self.ensure_connected()
        try:
            client = self._require_client()
            return int(await client.incr(key))
        except Exception as e:
            logger.exception("Failed to increment key %s", key)
            raise CoreServiceError(
                message=f"Failed to increment cache key '{key}'",
                code="CACHE_INCR_FAILED",
                service="CacheService",
                details={"key": key, "error": str(e)},
            ) from e

    async def decr(self, key: str) -> int | None:
        """Decrement a counter in cache.

        Args:
            key: Counter key

        Returns:
            The new counter value or None if failed
        """
        await self.ensure_connected()
        try:
            client = self._require_client()
            return int(await client.decr(key))
        except Exception as e:
            logger.exception("Failed to decrement key %s", key)
            raise CoreServiceError(
                message=f"Failed to decrement cache key '{key}'",
                code="CACHE_DECR_FAILED",
                service="CacheService",
                details={"key": key, "error": str(e)},
            ) from e

    # Batch operations (no explicit pipelines in Upstash Python)

    async def mget(self, keys: list[str]) -> list[str | None]:
        """Get multiple values at once.

        Args:
            keys: List of keys to get

        Returns:
            List of values (None for missing keys)
        """
        await self.ensure_connected()
        try:
            if not keys:
                return []
            client = self._require_client()
            values = await client.mget(*keys)
            return [v if v is not None else None for v in values]
        except Exception as e:
            logger.exception("Failed to mget keys")
            raise CoreServiceError(
                message="Failed to get multiple cache keys",
                code="CACHE_MGET_FAILED",
                service="CacheService",
                details={"error": str(e)},
            ) from e

    async def mset(self, mapping: dict[str, str]) -> bool:
        """Set multiple key-value pairs at once.

        Args:
            mapping: Dictionary of key-value pairs

        Returns:
            True if successful
        """
        await self.ensure_connected()
        try:
            client = self._require_client()
            return bool(await client.mset(mapping))
        except Exception as e:
            logger.exception("Failed to mset")
            raise CoreServiceError(
                message="Failed to set multiple cache keys",
                code="CACHE_MSET_FAILED",
                service="CacheService",
                details={"error": str(e)},
            ) from e

    # Pattern-based operations

    async def keys(self, pattern: str = "*") -> list[str]:
        """Get all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            List of matching keys
        """
        await self.ensure_connected()
        try:
            client = self._require_client()
            keys = await client.keys(pattern)
            result: list[str] = []
            for k in keys:
                if isinstance(k, (bytes, bytearray)):
                    result.append(k.decode("utf-8"))
                else:
                    result.append(str(k))
            return result
        except Exception:
            logger.exception("Failed to get keys with pattern %s", pattern)
            return []

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.

        Args:
            pattern: Key pattern to delete

        Returns:
            Number of keys deleted
        """
        keys = await self.keys(pattern)
        if keys:
            return await self.delete(*keys)
        return 0

    # Cache management

    async def info(self) -> JSONObject:
        """Return server information details if available."""
        await self.ensure_connected()
        try:
            client = self._require_client()
            info_callable = getattr(client, "info", None)
            if info_callable is None or not callable(info_callable):
                return {"available": False, "details": "info command unsupported"}

            # Narrow type for type checkers; still guarded by callable() above.
            typed_info: Callable[[], Awaitable[object]] = cast(
                Callable[[], Awaitable[object]], info_callable
            )
            raw_info = await typed_info()  # pylint: disable=not-callable
            if isinstance(raw_info, Mapping):
                normalized: JSONObject = {}
                for key, value in cast(Mapping[object, object], raw_info).items():
                    normalized[str(key)] = _coerce_json_value(value)
                return normalized
            return {"raw": str(raw_info)}
        except Exception as e:
            logger.exception("Failed to fetch cache info")
            raise CoreServiceError(
                message="Failed to fetch cache info",
                code="CACHE_INFO_FAILED",
                service="CacheService",
                details={"error": str(e)},
            ) from e

    async def flushdb(self) -> bool:
        """Clear all data from the current database.

        WARNING: This will delete all data!

        Returns:
            True if successful, False otherwise
        """
        await self.ensure_connected()
        try:
            client = self._require_client()
            result = await client.flushdb()
            return bool(result)
        except Exception:
            logger.exception("Failed to flush database")
            return False

    # Health check

    async def health_check(self) -> bool:
        """Check cache service connectivity.

        Returns:
            True if healthy, False otherwise
        """
        try:
            await self.ensure_connected()
            client = self._require_client()
            return bool(await client.ping())
        except Exception:
            logger.exception("Cache health check failed")
            return False

    # Convenience methods with TTL presets

    async def set_short(self, key: str, value: JSONValue) -> bool:
        """Set a value with short TTL (5 minutes by default).

        Args:
            key: Cache key
            value: Value to store

        Returns:
            True if successful
        """
        return await self.set_json(key, value, ttl=300)  # Short TTL (5 minutes)

    async def set_medium(self, key: str, value: JSONValue) -> bool:
        """Set a value with medium TTL (1 hour by default).

        Args:
            key: Cache key
            value: Value to store

        Returns:
            True if successful
        """
        return await self.set_json(key, value, ttl=3600)  # Medium TTL (1 hour)

    async def set_long(self, key: str, value: JSONValue) -> bool:
        """Set a value with long TTL (24 hours by default).

        Args:
            key: Cache key
            value: Value to store

        Returns:
            True if successful
        """
        return await self.set_json(key, value, ttl=86400)  # Long TTL (24 hours)


async def get_cache_service(
    settings: Settings | None = None, *, ensure_connected: bool = True
) -> CacheService:
    """Create a ``CacheService`` instance, optionally establishing a connection.

    Args:
        settings: Optional ``Settings`` to configure the service. When ``None``,
            loads defaults via ``get_settings()`` inside ``CacheService``.
        ensure_connected: When ``True`` (default), establishes the connection by
            awaiting ``connect()`` before returning.

    Returns:
        A ``CacheService`` instance (connected when ``ensure_connected`` is True).
    """
    service = CacheService(settings)
    if ensure_connected:
        await service.connect()
    return service


@asynccontextmanager
async def cache_service(settings: Settings | None = None):
    """Async context manager yielding a connected ``CacheService``.

    Ensures fast, explicit lifecycle management: connects on enter and always
    disconnects on exit. Prefer this in short-lived tasks, tests, and scripts.

    Example:
        async with cache_service() as cache:
            await cache.set("k", "v")

    Args:
        settings: Optional ``Settings`` to configure the service.

    Yields:
        A connected ``CacheService`` instance.
    """
    service = CacheService(settings)
    try:
        await service.connect()
        yield service
    finally:
        await service.disconnect()
