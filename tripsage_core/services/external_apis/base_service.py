"""Shared utilities for external API service implementations.

This module provides small, focused helpers and mixins used by external API
services. It intentionally keeps surface area small and dependency-free,
favoring built-ins and widely used libraries already present in the project.

Additions in this change:
- ``sanitize_response``: A defensive JSON sanitizer/parser to normalize
  third-party responses before they reach our models or storage layers.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from types import TracebackType
from typing import Any, Final, TypeVar, cast


try:  # Prefer orjson for strict, fast parsing if available
    import orjson as _orjson  # type: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - fallback path used in minimal envs
    _orjson = None  # type: ignore[assignment]
import json as _json
import math


ServiceT = TypeVar("ServiceT")


class AsyncServiceLifecycle:
    """Mixin providing default async context management."""

    async def connect(self) -> None:  # pragma: no cover - interface only
        """Connect the service."""
        raise NotImplementedError

    async def disconnect(self) -> None:  # pragma: no cover - interface only
        """Disconnect the service."""
        raise NotImplementedError

    async def close(self) -> None:
        """Close the service by delegating to disconnect."""
        await self.disconnect()

    async def __aenter__(self) -> AsyncServiceLifecycle:
        """Enter the context manager."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager, always closing the service."""
        await self.close()


class AsyncServiceProvider[ServiceT]:
    """Lazy async service provider without module-level globals."""

    def __init__(
        self,
        factory: Callable[[], ServiceT],
        initializer: Callable[[ServiceT], Awaitable[None]] | None = None,
        finalizer: Callable[[ServiceT], Awaitable[None]] | None = None,
    ):
        """Initialize the service provider."""
        self._factory = factory
        self._initializer = initializer
        self._finalizer = finalizer
        self._instance: ServiceT | None = None
        self._lock = asyncio.Lock()

    async def get(self) -> ServiceT:
        """Return a singleton service instance, creating it on demand."""
        async with self._lock:
            if self._instance is None:
                instance = self._factory()
                if self._initializer:
                    await self._initializer(instance)
                self._instance = instance
            return self._instance

    async def close(self) -> None:
        """Dispose of the singleton instance if it exists."""
        async with self._lock:
            if self._instance is None:
                return
            if self._finalizer:
                await self._finalizer(self._instance)
            self._instance = None


# JSON type used for sanitized payloads
type JSONScalar = None | bool | int | float | str
type JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]

_DANGEROUS_KEYS: Final[set[str]] = {"__proto__", "prototype", "constructor"}


def _coerce_scalar(value: Any) -> JSONScalar:
    """Coerce a scalar to a JSON-safe scalar.

    - Rejects NaN/Infinity by converting to ``None``.
    - Leaves ints/bools/strings as-is (strings are returned unchanged; HTML
      encoding is a rendering concern handled at the template boundary).

    Args:
        value: Arbitrary scalar value.

    Returns:
        A JSON-safe scalar (``None`` replaces non-finite floats).
    """
    if value is None or isinstance(value, (bool, int, str)):
        return cast(JSONScalar, value)
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    # Fallback: string representation to avoid implicit objects leaking through
    return str(value)


def _sanitize_mapping(obj: Mapping[Any, Any]) -> dict[str, JSONValue]:
    """Sanitize a mapping into a plain ``dict[str, JSONValue]``.

    - Drops dangerous prototype-like keys.
    - Coerces non-string keys to strings.
    - Recursively sanitizes nested structures.
    """
    out: dict[str, JSONValue] = {}
    for k, v in obj.items():
        key = str(k)
        if key in _DANGEROUS_KEYS:
            continue
        out[key] = _sanitize_any(v)
    return out


def _sanitize_any(value: Any) -> JSONValue:
    """Recursively sanitize arbitrary JSON-like data."""
    if isinstance(value, Mapping):
        return _sanitize_mapping(cast(Mapping[Any, Any], value))
    if isinstance(value, (list, tuple)):
        seq = cast(list[Any] | tuple[Any, ...], value)
        return [_sanitize_any(v) for v in seq]
    return _coerce_scalar(value)


def sanitize_response(data: Any) -> JSONValue:
    """Parse and sanitize third-party API responses.

    This function serves two roles:
    1) If ``data`` is ``bytes``/``str``, attempt strict JSON parsing using
       ``orjson`` when available, otherwise ``json.loads``. Non-finite floats
       are rejected/normalized.
    2) For ``dict``/``list`` inputs (e.g., SDK-returned objects), recursively
       sanitize by removing prototype-like keys and coercing values into a
       JSON-safe shape.

    The result is validated to conform to the ``JSONValue`` alias to keep
    downstream models safe and predictable.

    Args:
        data: Raw payload from an HTTP/SDK response. May be bytes, str, list,
            tuple, dict, or other mapping.

    Returns:
        A sanitized ``JSONValue`` suitable for Pydantic validation and safe
        merging/serialization.
    """
    parsed: Any
    if isinstance(data, (bytes, bytearray)):
        if _orjson is not None:
            parsed = _orjson.loads(data)  # pylint: disable=no-member
        else:
            # Standard json parser; keep strict string handling and disallow
            # NaN/Infinity by rerouting via parse_constant to raise.
            def _reject_constants(_: str) -> None:  # pragma: no cover - edge path
                raise ValueError("Non-finite JSON number encountered")

            parsed = _json.loads(
                data.decode("utf-8"),
                parse_constant=_reject_constants,
                strict=True,
            )
    elif isinstance(data, str):
        if _orjson is not None:
            parsed = _orjson.loads(data)  # pylint: disable=no-member
        else:

            def _reject_constants(_: str) -> None:  # pragma: no cover - edge path
                raise ValueError("Non-finite JSON number encountered")

            parsed = _json.loads(data, parse_constant=_reject_constants, strict=True)
    else:
        parsed = data

    return _sanitize_any(parsed)
