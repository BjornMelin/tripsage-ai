"""Shared utilities for external API service implementations."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar


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

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager."""
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


@dataclass(frozen=True)
class ConcurrencyLimits:
    """Common concurrency limits for async services."""

    max_concurrent: int = 3
