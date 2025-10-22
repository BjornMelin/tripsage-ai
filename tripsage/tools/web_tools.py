"""Web search tools with caching for TripSage agents."""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any, Literal

from agents import WebSearchTool as _BaseWebSearchTool
from tripsage_core.utils.cache_utils import (
    CacheStats,
    generate_cache_key,
    get_cache,
    get_cache_stats,
    invalidate_pattern,
    set_cache,
)
from tripsage_core.utils.content_utils import ContentType
from tripsage_core.utils.decorator_utils import with_error_handling
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)
WEB_CACHE_NAMESPACE = "web-search"


def _infer_content_type(query: str) -> ContentType:
    """Best-effort heuristics for cache TTL selection."""
    normalized = query.lower()
    if any(
        keyword in normalized for keyword in ("now", "today", "right now", "weather")
    ):
        return ContentType.REALTIME
    if any(keyword in normalized for keyword in ("breaking", "news", "update")):
        return ContentType.TIME_SENSITIVE
    if any(keyword in normalized for keyword in ("price", "fare", "flight", "deal")):
        return ContentType.DAILY
    if any(keyword in normalized for keyword in ("menu", "hours", "schedule")):
        return ContentType.SEMI_STATIC
    return ContentType.STATIC


class CachedWebSearchTool(_BaseWebSearchTool):
    """Web search tool with Redis/Dragonfly-backed caching."""

    def __init__(
        self,
        namespace: str = WEB_CACHE_NAMESPACE,
        user_location: Any | None = None,
        search_context_size: Literal["low", "medium", "high"] = "medium",
    ) -> None:
        """Initialize the cached tool with namespace and user context defaults."""
        super().__init__(
            user_location=user_location, search_context_size=search_context_size
        )
        self.namespace = namespace

    async def _run(  # type: ignore[override]
        self,
        query: str,
        *,
        skip_cache: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        cache_key = generate_cache_key(
            "websearch",
            query.strip(),
            self.user_location or "",
            search_context_size=self.search_context_size,
            **kwargs,
        )

        if not skip_cache:
            cached_result = await get_cache(cache_key, namespace=self.namespace)
            if cached_result is not None:
                logger.debug("Web search cache hit for %s", query)
                return cached_result

        logger.debug("Web search cache miss for %s", query)
        result = await super()._run(  # type: ignore[attr-defined]  # pylint: disable=no-member
            query, **kwargs
        )

        content_type = _infer_content_type(query)
        await set_cache(
            cache_key,
            result,
            content_type=content_type,
            namespace=self.namespace,
        )
        return result


async def get_web_cache_stats() -> CacheStats:
    """Return aggregate cache statistics (namespace-agnostic)."""
    return await get_cache_stats()


async def invalidate_web_cache_for_query(query: str) -> int:
    """Invalidate cached entries that match the hashed query key."""
    normalized = query.lower().strip()
    digest = hashlib.md5(normalized.encode(), usedforsecurity=False).hexdigest()
    pattern = f"*{digest}*"
    return await invalidate_pattern(pattern, namespace=WEB_CACHE_NAMESPACE)


@with_error_handling()
async def batch_web_search(
    queries: list[str],
    skip_cache: bool = False,
) -> list[dict[str, Any]]:
    """Run multiple web searches concurrently with caching."""
    if not queries:
        return []

    tool = CachedWebSearchTool(namespace=WEB_CACHE_NAMESPACE)
    tasks = [
        asyncio.create_task(tool._run(query, skip_cache=skip_cache))
        for query in queries
    ]
    try:
        return await asyncio.gather(*tasks)
    except Exception as exc:
        logger.exception("batch_web_search failed")
        return [
            {"status": "error", "error": {"message": str(exc)}, "search_results": []}
            for _ in queries
        ]


def web_cached(content_type: ContentType, ttl: int | None = None):
    """Decorator that applies caching using the shared cache facade."""

    def _decorator(func):
        @with_error_handling()
        async def _wrapper(*args: Any, **kwargs: Any):
            cache_key = generate_cache_key(
                func.__name__,
                args,
                kwargs,
                content_type=content_type.value,
            )
            cached_value = await get_cache(cache_key, namespace=WEB_CACHE_NAMESPACE)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)
            await set_cache(
                cache_key,
                result,
                content_type=content_type,
                ttl=ttl,
                namespace=WEB_CACHE_NAMESPACE,
            )
            return result

        return _wrapper

    return _decorator


__all__ = [
    "CachedWebSearchTool",
    "batch_web_search",
    "get_web_cache_stats",
    "invalidate_web_cache_for_query",
    "web_cached",
]
