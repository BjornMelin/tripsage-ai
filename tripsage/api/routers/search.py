"""Router for unified search endpoints in the TripSage API."""

import logging
from datetime import UTC
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query, Request, status

from tripsage.api.core.dependencies import (
    CacheDep,
    CurrentPrincipalDep,
    DatabaseDep,
    RequiredPrincipalDep,
    SearchFacadeDep,
    get_principal_id,
)
from tripsage.api.schemas.search import (
    SearchAnalyticsResponse,
    UnifiedSearchAggregateResponse as UnifiedSearchResponse,
    UnifiedSearchRequest,
)
from tripsage_core.services.business.search_history_service import SearchHistoryService
from tripsage_core.services.business.unified_search_service import (
    UnifiedSearchServiceError,
)
from tripsage_core.services.infrastructure.cache_service import CacheService


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/unified", response_model=UnifiedSearchResponse)
async def unified_search(
    _: Request,
    request: UnifiedSearchRequest,
    search_service: SearchFacadeDep,
    cache_service: CacheDep,
    principal: CurrentPrincipalDep,
    use_cache: bool = Query(True, description="Whether to use cached results"),
):
    """Perform a unified search across multiple resource types with caching.

    This endpoint searches across destinations, activities, accommodations,
    and flights (when applicable) to provide travel search results.
    Results are aggregated, filtered, sorted, and cached for performance.
    """
    user_id = principal.id if principal else None
    logger.info("Unified search request: %s (user: %s)", request.query, user_id)

    try:
        # DI-managed services provided via dependencies

        # Generate cache key based on request parameters
        cache_key = f"search:unified:{hash(str(request.model_dump()))}"

        # Try to get from cache first
        cached_result = None
        if use_cache:
            try:
                cached_result = await cache_service.get_json(cache_key)
                if cached_result:
                    logger.info("Cache hit for search query: %s", request.query)
                    # Track cache hit analytics
                    await _track_search_analytics(
                        user_id, request.query, "cache_hit", cache_service
                    )
                    return UnifiedSearchResponse.model_validate(cached_result)
            except (OSError, RuntimeError, ValueError, TypeError) as e:
                logger.warning("Cache retrieval failed: %s", e)

        # Perform actual search
        result = await search_service.unified_search(request)

        # Cache the result for 5 minutes
        if use_cache:
            try:
                await cache_service.set_json(cache_key, result.model_dump(), ttl=300)
            except (OSError, RuntimeError, ValueError, TypeError) as e:
                logger.warning("Cache storage failed: %s", e)

        # Track search analytics
        await _track_search_analytics(
            user_id,
            request.query,
            "cache_miss" if use_cache else "no_cache",
            cache_service,
        )

        logger.info(
            "Unified search completed: %s results in %sms",
            result.metadata.returned_results,
            result.metadata.search_time_ms,
        )
        return result

    except UnifiedSearchServiceError as e:
        logger.exception("Unified search service error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {e.message}",
        ) from e
    except Exception as e:
        logger.exception("Unexpected error in unified search")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while performing the search",
        ) from e


async def _track_search_analytics(
    user_id: str | None, query: str, cache_status: str, cache_service: CacheService
) -> None:
    """Track search analytics for monitoring and optimization."""
    try:
        from datetime import datetime

        analytics_data = {
            "user_id": user_id,
            "query": query,
            "cache_status": cache_status,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Store analytics in cache with daily key
        date_key = datetime.now(UTC).strftime("%Y-%m-%d")
        analytics_key = f"analytics:search:{date_key}"

        # Get existing analytics or create new
        raw_existing = await cache_service.get_json(analytics_key, default=[])
        existing_list = (
            (
                [
                    cast(dict[str, Any], item)
                    for item in cast(list[Any], raw_existing)
                    if isinstance(item, dict)
                ]
                + [analytics_data]
            )
            if isinstance(raw_existing, list)
            else [analytics_data]
        )

        # Store back with 24-hour TTL
        await cache_service.set_json(analytics_key, existing_list, ttl=86400)

    except (OSError, RuntimeError, ValueError, TypeError) as e:
        logger.warning("Failed to track search analytics: %s", e)


@router.get("/suggest", response_model=list[str])
async def search_suggestions(
    _: Request,
    search_service: SearchFacadeDep,
    query: str = Query(
        ..., min_length=1, max_length=100, description="Partial search query"
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of suggestions"),
):
    """Get search suggestions based on partial query.

    This endpoint provides intelligent search suggestions including popular
    destinations, activity types, and common search patterns to help users
    discover travel options.
    """
    logger.info("Search suggestions request: '%s' (limit: %s)", query, limit)

    try:
        suggestions = await search_service.get_search_suggestions(query, limit)

        logger.info("Generated %s suggestions for query: '%s'", len(suggestions), query)
        return suggestions

    except UnifiedSearchServiceError as e:
        logger.exception("Search suggestions service error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {e.message}",
        ) from e
    except Exception as e:
        logger.exception("Unexpected error getting search suggestions")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating suggestions",
        ) from e


@router.get("/recent", response_model=list[dict[str, Any]])
async def get_recent_searches(
    _: Request,
    db_service: DatabaseDep,
    principal: RequiredPrincipalDep,
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of searches to return"
    ),
):
    """Get recent searches for the authenticated user.

    Returns the user's search history ordered by most recent first.
    """
    user_id = get_principal_id(principal)
    logger.info("Get recent searches request for user: %s (limit: %s)", user_id, limit)

    try:
        search_history_service = SearchHistoryService(db_service)
        searches = await search_history_service.get_recent_searches(
            user_id, limit=limit
        )

        logger.info("Retrieved %s recent searches for user: %s", len(searches), user_id)
        return searches

    except Exception as e:
        logger.exception("Error retrieving search history")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve search history",
        ) from e


@router.post("/save", response_model=dict[str, str])
async def save_search(
    _: Request,
    db_service: DatabaseDep,
    request: UnifiedSearchRequest,
    principal: RequiredPrincipalDep,
):
    """Save a search query for the authenticated user.

    Saves the search parameters to the user's search history for
    quick access and personalization.
    """
    user_id = get_principal_id(principal)
    logger.info("Save search request for user %s: %s", user_id, request.query)

    try:
        search_history_service = SearchHistoryService(db_service)
        saved_search = await search_history_service.save_search(user_id, request)

        logger.info("Saved search %s for user: %s", saved_search["id"], user_id)
        return {
            "id": saved_search["id"],
            "message": "Search saved successfully",
        }

    except Exception as e:
        logger.exception("Error saving search")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save search",
        ) from e


@router.delete("/saved/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    request: Request,
    db_service: DatabaseDep,
    search_id: str,
    principal: RequiredPrincipalDep,
):
    """Delete a saved search for the authenticated user.

    Removes the specified search from the user's search history.
    """
    user_id = get_principal_id(principal)
    logger.info("Delete saved search request from user %s: %s", user_id, search_id)

    try:
        search_history_service = SearchHistoryService(db_service)
        deleted = await search_history_service.delete_saved_search(user_id, search_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved search not found",
            )

        logger.info("Deleted saved search %s for user: %s", search_id, user_id)
        # Return 204 No Content (no response body)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting saved search")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete saved search",
        ) from e


@router.post("/bulk", response_model=list[UnifiedSearchResponse])
async def bulk_search(
    _: Request,
    requests: list[UnifiedSearchRequest],
    search_service: SearchFacadeDep,
    cache_service: CacheDep,
    principal: CurrentPrincipalDep,
    use_cache: bool = Query(True, description="Whether to use cached results"),
):
    """Perform multiple searches in a single request for efficiency.

    Useful for comparing multiple destinations or search variations.
    Results are processed in parallel for optimal performance.
    """
    user_id = principal.id if principal else None
    logger.info("Bulk search request: %s queries (user: %s)", len(requests), user_id)

    if len(requests) > 10:  # Limit bulk searches
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 searches allowed per bulk request",
        )

    try:
        import asyncio
        # cache_service not required explicitly here; UnifiedSearchService is DI

        async def process_single_search(request: UnifiedSearchRequest):
            """Process a single search with caching."""
            cache_key = f"search:unified:{hash(str(request.model_dump()))}"

            # Try cache first
            if use_cache:
                try:
                    cached_result = await cache_service.get_json(cache_key)
                    if cached_result:
                        await _track_search_analytics(
                            user_id, request.query, "cache_hit", cache_service
                        )
                        return UnifiedSearchResponse.model_validate(cached_result)
                except (OSError, RuntimeError, ValueError, TypeError) as cache_error:
                    logger.warning(
                        "Cache lookup failed for key %s: %s",
                        cache_key,
                        cache_error,
                    )

            # Perform search
            result = await search_service.unified_search(request)

            # Cache result
            if use_cache:
                try:
                    await cache_service.set_json(
                        cache_key, result.model_dump(), ttl=300
                    )
                except (OSError, RuntimeError, ValueError, TypeError) as cache_error:
                    logger.warning(
                        "Cache write failed for key %s: %s",
                        cache_key,
                        cache_error,
                    )

            await _track_search_analytics(
                user_id,
                request.query,
                "cache_miss" if use_cache else "no_cache",
                cache_service,
            )

            return result

        # Process all searches in parallel
        results = await asyncio.gather(
            *[process_single_search(req) for req in requests], return_exceptions=True
        )

        # Filter out exceptions and return successful results
        gathered: list[UnifiedSearchResponse | Exception] = cast(
            list[UnifiedSearchResponse | Exception], results
        )

        successful_results: list[UnifiedSearchResponse | None] = []
        for i, result in enumerate(gathered):
            if isinstance(result, Exception):
                logger.exception("Search %s failed: %s", i, result)
                successful_results.append(None)
            else:
                successful_results.append(result)

        # Remove None values
        valid_results: list[UnifiedSearchResponse] = [
            r for r in successful_results if r is not None
        ]

        logger.info(
            "Bulk search completed: %s/%s successful", len(valid_results), len(requests)
        )
        return valid_results

    except Exception as e:
        logger.exception("Bulk search failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk search operation failed",
        ) from e


@router.get("/analytics", response_model=SearchAnalyticsResponse)
async def get_search_analytics(
    _: Request,
    principal: RequiredPrincipalDep,
    cache_service: CacheDep,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
):
    """Get search analytics for a specific date.

    Only available to authenticated users for their own analytics.
    """
    user_id = get_principal_id(principal)
    logger.info("Search analytics request for %s by user: %s", date, user_id)

    try:
        analytics_key = f"analytics:search:{date}"

        raw_analytics = await cache_service.get_json(analytics_key, default=[])
        analytics_data = (
            [
                cast(dict[str, Any], item)
                for item in cast(list[Any], raw_analytics)
                if isinstance(item, dict)
            ]
            if isinstance(raw_analytics, list)
            else []
        )

        # Filter to user's own analytics
        user_analytics: list[dict[str, Any]] = [
            d for d in analytics_data if d.get("user_id") == user_id
        ]

        # Aggregate statistics
        total_searches = len(user_analytics)
        cache_hits = len(
            [d for d in user_analytics if d.get("cache_status") == "cache_hit"]
        )
        cache_misses = len(
            [d for d in user_analytics if d.get("cache_status") == "cache_miss"]
        )

        # Most common queries
        query_counts: dict[str, int] = {}
        for data in user_analytics:
            query = str(data.get("query", ""))
            query_counts[query] = query_counts.get(query, 0) + 1

        popular_queries: list[tuple[str, int]] = sorted(
            query_counts.items(), key=lambda x: int(x[1]), reverse=True
        )[:10]

        return SearchAnalyticsResponse(
            date=date,
            total_searches=total_searches,
            cache_hit_rate=cache_hits / max(total_searches, 1),
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            popular_queries=[{"query": q, "count": c} for q, c in popular_queries],
        )

    except Exception as e:
        logger.exception("Failed to get search analytics")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve search analytics",
        ) from e
