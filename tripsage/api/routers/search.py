"""
Router for unified search endpoints in the TripSage API.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Query, status

from tripsage.api.schemas.requests.search import UnifiedSearchRequest
from tripsage.api.schemas.responses.search import UnifiedSearchResponse
from tripsage_core.services.business.unified_search_service import (
    UnifiedSearchServiceError,
    get_unified_search_service,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/unified", response_model=UnifiedSearchResponse)
async def unified_search(request: UnifiedSearchRequest):
    """
    Perform a unified search across multiple resource types.

    This endpoint searches across destinations, activities, accommodations,
    and flights (when applicable) to provide comprehensive travel search results.
    Results are aggregated, filtered, and sorted to provide the best matches.
    """
    logger.info(f"Unified search request: {request.query}")

    try:
        search_service = await get_unified_search_service()
        result = await search_service.unified_search(request)

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


@router.get("/recent")
async def get_recent_searches():
    """
    Get recent searches for the authenticated user.

    Note: This endpoint requires user authentication and database integration
    to store and retrieve user search history.
    """
    logger.info("Get recent searches request")

    # TODO: Implement user authentication and search history storage
    # For now, return empty list to maintain API contract
    return []


@router.post("/save")
async def save_search(request: UnifiedSearchRequest):
    """
    Save a search query for the authenticated user.

    Note: This endpoint requires user authentication and database integration
    to persist user search preferences and history.
    """
    logger.info(f"Save search request: {request.query}")

    # TODO: Implement user authentication and search history storage
    # For now, return 501 to maintain API contract
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Save search endpoint requires user authentication implementation",
    )


@router.delete("/saved/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(search_id: str):
    """
    Delete a saved search for the authenticated user.

    Note: This endpoint requires user authentication and database integration
    to manage user search history.
    """
    logger.info(f"Delete saved search request: {search_id}")

    # TODO: Implement user authentication and search history management
    # For now, return 501 to maintain API contract
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Delete saved search endpoint requires user authentication "
            "implementation"
        ),
    )
