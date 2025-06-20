"""
Router for unified search endpoints in the TripSage API.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from tripsage.api.core.dependencies import (
    get_current_principal,
    get_principal_id,
    require_principal,
)
from tripsage.api.schemas.requests.search import UnifiedSearchRequest
from tripsage.api.schemas.responses.search import UnifiedSearchResponse
from tripsage_core.services.business.search_history_service import (
    get_search_history_service,
)
from tripsage_core.services.business.unified_search_service import (
    UnifiedSearchServiceError,
    get_unified_search_service,
)
from tripsage_core.services.infrastructure.cache_service import get_cache_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/unified", response_model=UnifiedSearchResponse)
async def unified_search(
    request: UnifiedSearchRequest,
    use_cache: bool = Query(True, description="Whether to use cached results"),
    principal=Depends(get_current_principal),
):
    """
    Perform a unified search across multiple resource types with caching.

    This endpoint searches across destinations, activities, accommodations,
    and flights (when applicable) to provide comprehensive travel search results.
    Results are aggregated, filtered, sorted, and cached for performance.
    """
    user_id = principal.id if principal else None
    logger.info(f"Unified search request: {request.query} (user: {user_id})")

    try:
        search_service = await get_unified_search_service()
        cache_service = await get_cache_service()

        # Generate cache key based on request parameters
        cache_key = f"search:unified:{hash(str(request.model_dump()))}"

        # Try to get from cache first
        cached_result = None
        if use_cache:
            try:
                cached_result = await cache_service.get(cache_key)
                if cached_result:
                    logger.info(f"Cache hit for search query: {request.query}")
                    # Track cache hit analytics
                    await _track_search_analytics(
                        user_id, request.query, "cache_hit", cache_service
                    )
                    return cached_result
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")

        # Perform actual search
        result = await search_service.unified_search(request)

        # Cache the result for 5 minutes
        if use_cache:
            try:
                await cache_service.set(cache_key, result, ttl=300)
            except Exception as e:
                logger.warning(f"Cache storage failed: {e}")

        # Track search analytics
        await _track_search_analytics(
            user_id,
            request.query,
            "cache_miss" if use_cache else "no_cache",
            cache_service,
        )

        logger.info(
            f"Unified search completed: {result.metadata.returned_results} results "
            f"in {result.metadata.search_time_ms}ms"
        )
        return result

    except UnifiedSearchServiceError as e:
        logger.error(f"Unified search service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {e.message}",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error in unified search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while performing the search",
        ) from e


async def _track_search_analytics(
    user_id: Optional[str], query: str, cache_status: str, cache_service
):
    """Track search analytics for monitoring and optimization."""
    try:
        from datetime import datetime

        analytics_data = {
            "user_id": user_id,
            "query": query,
            "cache_status": cache_status,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Store analytics in cache with daily key
        date_key = datetime.utcnow().strftime("%Y-%m-%d")
        analytics_key = f"analytics:search:{date_key}"

        # Get existing analytics or create new
        existing_analytics = await cache_service.get(analytics_key) or []
        existing_analytics.append(analytics_data)

        # Store back with 24-hour TTL
        await cache_service.set(analytics_key, existing_analytics, ttl=86400)

    except Exception as e:
        logger.warning(f"Failed to track search analytics: {e}")


@router.get("/suggest", response_model=List[str])
async def search_suggestions(
    query: str = Query(
        ..., min_length=1, max_length=100, description="Partial search query"
    ),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of suggestions"),
):
    """
    Get search suggestions based on partial query.

    This endpoint provides intelligent search suggestions including popular
    destinations, activity types, and common search patterns to help users
    discover travel options.
    """
    logger.info(f"Search suggestions request: '{query}' (limit: {limit})")

    try:
        search_service = await get_unified_search_service()
        suggestions = await search_service.get_search_suggestions(query, limit)

        logger.info(f"Generated {len(suggestions)} suggestions for query: '{query}'")
        return suggestions

    except UnifiedSearchServiceError as e:
        logger.error(f"Search suggestions service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {e.message}",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error getting search suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating suggestions",
        ) from e


@router.get("/recent", response_model=List[Dict[str, Any]])
async def get_recent_searches(
    limit: int = Query(
        10, ge=1, le=50, description="Maximum number of searches to return"
    ),
    principal=Depends(require_principal),
):
    """
    Get recent searches for the authenticated user.

    Returns the user's search history ordered by most recent first.
    """
    user_id = get_principal_id(principal)
    logger.info(f"Get recent searches request for user: {user_id} (limit: {limit})")

    try:
        search_history_service = await get_search_history_service()
        searches = await search_history_service.get_recent_searches(
            user_id, limit=limit
        )

        logger.info(f"Retrieved {len(searches)} recent searches for user: {user_id}")
        return searches

    except Exception as e:
        logger.error(f"Error retrieving search history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve search history",
        ) from e


@router.post("/save", response_model=Dict[str, str])
async def save_search(
    request: UnifiedSearchRequest,
    principal=Depends(require_principal),
):
    """
    Save a search query for the authenticated user.

    Saves the search parameters to the user's search history for
    quick access and personalization.
    """
    user_id = get_principal_id(principal)
    logger.info(f"Save search request for user {user_id}: {request.query}")

    try:
        search_history_service = await get_search_history_service()
        saved_search = await search_history_service.save_search(user_id, request)

        logger.info(f"Saved search {saved_search['id']} for user: {user_id}")
        return {
            "id": saved_search["id"],
            "message": "Search saved successfully",
        }

    except Exception as e:
        logger.error(f"Error saving search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save search",
        ) from e


@router.delete("/saved/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: str,
    principal=Depends(require_principal),
):
    """
    Delete a saved search for the authenticated user.

    Removes the specified search from the user's search history.
    """
    user_id = get_principal_id(principal)
    logger.info(f"Delete saved search request from user {user_id}: {search_id}")

    try:
        search_history_service = await get_search_history_service()
        deleted = await search_history_service.delete_saved_search(user_id, search_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved search not found",
            )

        logger.info(f"Deleted saved search {search_id} for user: {user_id}")
        # Return 204 No Content (no response body)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting saved search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete saved search",
        ) from e


@router.post("/bulk", response_model=List[UnifiedSearchResponse])
async def bulk_search(
    requests: List[UnifiedSearchRequest],
    use_cache: bool = Query(True, description="Whether to use cached results"),
    principal=Depends(get_current_principal),
):
    """
    Perform multiple searches in a single request for efficiency.

    Useful for comparing multiple destinations or search variations.
    Results are processed in parallel for optimal performance.
    """
    user_id = principal.id if principal else None
    logger.info(f"Bulk search request: {len(requests)} queries (user: {user_id})")

    if len(requests) > 10:  # Limit bulk searches
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 searches allowed per bulk request",
        )

    try:
        import asyncio

        search_service = await get_unified_search_service()
        cache_service = await get_cache_service()

        async def process_single_search(request: UnifiedSearchRequest):
            """Process a single search with caching."""
            cache_key = f"search:unified:{hash(str(request.model_dump()))}"

            # Try cache first
            if use_cache:
                try:
                    cached_result = await cache_service.get(cache_key)
                    if cached_result:
                        await _track_search_analytics(
                            user_id, request.query, "cache_hit", cache_service
                        )
                        return cached_result
                except Exception:
                    pass

            # Perform search
            result = await search_service.unified_search(request)

            # Cache result
            if use_cache:
                try:
                    await cache_service.set(cache_key, result, ttl=300)
                except Exception:
                    pass

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
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Search {i} failed: {result}")
                # Add placeholder for failed search
                successful_results.append(None)
            else:
                successful_results.append(result)

        # Remove None values
        valid_results = [r for r in successful_results if r is not None]

        logger.info(
            f"Bulk search completed: {len(valid_results)}/{len(requests)} successful"
        )
        return valid_results

    except Exception as e:
        logger.error(f"Bulk search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk search operation failed",
        ) from e


@router.get("/analytics")
async def get_search_analytics(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    principal=Depends(require_principal),
):
    """
    Get search analytics for a specific date.

    Only available to authenticated users for their own analytics.
    """
    user_id = get_principal_id(principal)
    logger.info(f"Search analytics request for {date} by user: {user_id}")

    try:
        cache_service = await get_cache_service()
        analytics_key = f"analytics:search:{date}"

        analytics_data = await cache_service.get(analytics_key) or []

        # Filter to user's own analytics
        user_analytics = [
            data for data in analytics_data if data.get("user_id") == user_id
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
        query_counts = {}
        for data in user_analytics:
            query = data.get("query", "")
            query_counts[query] = query_counts.get(query, 0) + 1

        popular_queries = sorted(
            query_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        return {
            "date": date,
            "total_searches": total_searches,
            "cache_hit_rate": cache_hits / max(total_searches, 1),
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "popular_queries": [{"query": q, "count": c} for q, c in popular_queries],
        }

    except Exception as e:
        logger.error(f"Failed to get search analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve search analytics",
        ) from e
