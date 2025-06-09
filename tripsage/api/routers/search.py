"""
Router for unified search endpoints in the TripSage API.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from tripsage.api.schemas.requests.search import UnifiedSearchRequest
from tripsage.api.schemas.responses.search import (
    SearchMetadata,
    UnifiedSearchResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/unified", response_model=UnifiedSearchResponse)
async def unified_search(request: UnifiedSearchRequest):
    """
    Perform a unified search across multiple resource types.
    
    Note: This endpoint is currently returning mock data as the unified search service
    is not yet implemented. This router exists to prevent import errors.
    """
    logger.info(f"Unified search request: {request.query}")
    
    # Return empty results for now - this prevents import errors
    # TODO: Implement actual unified search service
    return UnifiedSearchResponse(
        results=[],
        facets=[],
        metadata=SearchMetadata(
            total_results=0,
            returned_results=0,
            search_time_ms=0,
            search_id="mock-search-id"
        )
    )


@router.post("/suggest")
async def search_suggestions(query: str):
    """
    Get search suggestions based on partial query.
    
    Note: This endpoint is not yet implemented.
    """
    logger.info(f"Search suggestions request: {query}")
    
    # Return 501 Not Implemented for now
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Search suggestions endpoint not yet implemented"
    )


@router.get("/recent")
async def get_recent_searches():
    """
    Get recent searches for the authenticated user.
    
    Note: This endpoint is not yet implemented.
    """
    logger.info("Get recent searches request")
    
    # Return empty list for now
    return []


@router.post("/save")
async def save_search(request: UnifiedSearchRequest):
    """
    Save a search query for the authenticated user.
    
    Note: This endpoint is not yet implemented.
    """
    logger.info(f"Save search request: {request.query}")
    
    # Return 501 Not Implemented for now
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Save search endpoint not yet implemented"
    )


@router.delete("/saved/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(search_id: str):
    """
    Delete a saved search for the authenticated user.
    
    Note: This endpoint is not yet implemented.
    """
    logger.info(f"Delete saved search request: {search_id}")
    
    # Return 501 Not Implemented for now
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Delete saved search endpoint not yet implemented"
    )