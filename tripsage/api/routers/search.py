"""
Router for unified search endpoints in the TripSage API.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from tripsage.api.core.dependencies import get_principal_id, require_principal_dep
from tripsage.api.middlewares.authentication import Principal
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

    This endpoint provides intelligent search suggestions including popular destinations,
    activity types, and common search patterns to help users discover travel options.
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
        20, ge=1, le=50, description="Maximum number of recent searches"
    ),
    principal: Principal = require_principal_dep,
    search_service=Depends(get_unified_search_service),
):
    """
    Get recent searches for the authenticated user.

    Args:
        limit: Maximum number of recent searches to return
        principal: Current authenticated principal
        search_service: Injected unified search service

    Returns:
        List of recent searches with metadata
    """
    user_id = get_principal_id(principal)
    logger.info(f"Get recent searches request for user {user_id}, limit: {limit}")

    try:
        # Get recent searches using service
        recent_searches = await search_service.get_recent_searches(
            user_id=user_id,
            limit=limit,
        )

        logger.info(
            f"Retrieved {len(recent_searches)} recent searches for user {user_id}"
        )
        return recent_searches

    except UnifiedSearchServiceError as e:
        logger.error(f"Failed to get recent searches for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get recent searches: {str(e)}",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error getting recent searches for user {user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/save", response_model=Dict[str, Any])
async def save_search(
    request: UnifiedSearchRequest,
    principal: Principal = require_principal_dep,
    search_service=Depends(get_unified_search_service),
):
    """
    Save a search query for the authenticated user.

    Args:
        request: Unified search request to save
        principal: Current authenticated principal
        search_service: Injected unified search service

    Returns:
        Saved search data with ID and metadata
    """
    user_id = get_principal_id(principal)
    logger.info(f"Save search request: '{request.query}' for user {user_id}")

    try:
        # Save search using service
        saved_search = await search_service.save_search(
            user_id=user_id,
            search_request=request,
        )

        logger.info(f"Search '{request.query}' saved successfully for user {user_id}")
        return saved_search

    except UnifiedSearchServiceError as e:
        logger.error(f"Failed to save search for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to save search: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error saving search for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/saved/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: str,
    principal: Principal = require_principal_dep,
    search_service=Depends(get_unified_search_service),
):
    """
    Delete a saved search for the authenticated user.

    Args:
        search_id: Search ID to delete
        principal: Current authenticated principal
        search_service: Injected unified search service

    Returns:
        204 No Content on successful deletion
    """
    user_id = get_principal_id(principal)
    logger.info(f"Delete saved search request: {search_id} for user {user_id}")

    try:
        # Delete saved search using service
        success = await search_service.delete_saved_search(
            user_id=user_id,
            search_id=search_id,
        )

        if not success:
            logger.warning(f"Search {search_id} not found for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Saved search {search_id} not found",
            )

        logger.info(f"Search {search_id} deleted successfully for user {user_id}")
        # Return 204 No Content (FastAPI handles this automatically with the status_code)

    except UnifiedSearchServiceError as e:
        logger.error(f"Failed to delete search {search_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete saved search: {str(e)}",
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error deleting search {search_id} for user {user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
