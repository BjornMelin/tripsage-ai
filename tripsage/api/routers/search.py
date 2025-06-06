"""Unified search endpoints for the TripSage API.

This module provides endpoints for searching across multiple resource types
(flights, accommodations, activities, destinations) in a unified way.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from tripsage.api.schemas.requests.search import (
    UnifiedSearchRequest,
    SearchFilters,
)
from tripsage.api.schemas.responses.search import (
    SearchResultItem,
    UnifiedSearchResponse,
    SearchMetadata,
    SearchFacet,
)
from tripsage_core.services.business.auth_service import (
    AuthenticationService,
    get_auth_service,
)
from tripsage_core.services.business.destination_service import (
    DestinationService,
    get_destination_service,
)
from tripsage_core.services.business.flight_service import (
    FlightService,
    get_flight_service,
)
from tripsage_core.services.business.accommodation_service import (
    AccommodationService,
    get_accommodation_service,
)

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


@router.post(
    "/unified",
    response_model=UnifiedSearchResponse,
    summary="Unified search across all resources",
    description="Search for flights, accommodations, activities, and destinations in one request",
)
async def unified_search(
    search_request: UnifiedSearchRequest,
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max number of results per type"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service),
    destination_service: DestinationService = Depends(get_destination_service),
    flight_service: FlightService = Depends(get_flight_service),
    accommodation_service: AccommodationService = Depends(get_accommodation_service),
):
    """Perform unified search across multiple resource types.

    Args:
        search_request: Unified search parameters
        skip: Pagination offset
        limit: Pagination limit per resource type
        credentials: Optional authorization credentials
        auth_service: Injected authentication service
        destination_service: Injected destination service
        flight_service: Injected flight service
        accommodation_service: Injected accommodation service

    Returns:
        Unified search results with items from all requested types

    Raises:
        HTTPException: If search fails
    """
    try:
        # Get current user if authenticated
        current_user = None
        if credentials:
            try:
                current_user = await auth_service.get_current_user(credentials.credentials)
            except Exception:
                # Continue as anonymous if auth fails
                pass
        
        results: List[SearchResultItem] = []
        facets: List[SearchFacet] = []
        errors: Dict[str, str] = {}
        
        # Determine which types to search
        search_types = search_request.types or ["destination", "flight", "accommodation", "activity"]
        
        # Create parallel search tasks
        tasks = []
        
        if "destination" in search_types:
            tasks.append(_search_destinations(
                search_request, destination_service, skip, limit
            ))
        
        if "flight" in search_types and search_request.origin:
            tasks.append(_search_flights(
                search_request, flight_service, skip, limit
            ))
        
        if "accommodation" in search_types:
            tasks.append(_search_accommodations(
                search_request, accommodation_service, skip, limit
            ))
        
        if "activity" in search_types:
            tasks.append(_search_activities(
                search_request, skip, limit
            ))
        
        # Execute searches in parallel
        if tasks:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in search_results:
                if isinstance(result, Exception):
                    logger.error(f"Search task failed: {str(result)}")
                    errors[result.__class__.__name__] = str(result)
                elif isinstance(result, tuple) and len(result) == 2:
                    items, type_facets = result
                    results.extend(items)
                    facets.extend(type_facets)
        
        # Sort results by relevance score if available
        results.sort(key=lambda x: x.relevance_score or 0, reverse=True)
        
        # Apply overall pagination
        total_results = len(results)
        results = results[skip : skip + limit]
        
        # Create search metadata
        metadata = SearchMetadata(
            total_results=total_results,
            returned_results=len(results),
            search_time_ms=100,  # TODO: Implement actual timing
            cached_results=0,  # TODO: Implement caching
            user_id=current_user.id if current_user else None,
        )
        
        return UnifiedSearchResponse(
            results=results,
            facets=facets,
            metadata=metadata,
            errors=errors if errors else None,
        )
        
    except Exception as e:
        logger.error(f"Unified search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        )


@router.get(
    "/suggestions",
    response_model=List[str],
    summary="Get search suggestions",
    description="Get search suggestions based on partial query",
)
async def get_search_suggestions(
    query: str = Query(..., min_length=2, description="Partial search query"),
    types: Optional[List[str]] = Query(
        None,
        description="Types to get suggestions for",
    ),
    limit: int = Query(10, ge=1, le=50, description="Max suggestions to return"),
):
    """Get search suggestions for autocomplete.

    Args:
        query: Partial search query
        types: Optional list of types to filter suggestions
        limit: Maximum number of suggestions

    Returns:
        List of search suggestions
    """
    try:
        # TODO: Implement actual suggestion logic
        # For now, return mock suggestions
        
        suggestions = []
        
        # Mock destination suggestions
        destinations = [
            "Paris, France",
            "Tokyo, Japan",
            "New York, USA",
            "London, UK",
            "Barcelona, Spain",
            "Rome, Italy",
            "Sydney, Australia",
            "Dubai, UAE",
            "Singapore",
            "Bangkok, Thailand",
        ]
        
        # Filter suggestions based on query
        for dest in destinations:
            if query.lower() in dest.lower():
                suggestions.append(dest)
        
        # Limit results
        suggestions = suggestions[:limit]
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Failed to get suggestions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get suggestions",
        )


@router.get(
    "/recent",
    response_model=List[Dict],
    summary="Get recent searches",
    description="Get user's recent search history",
)
async def get_recent_searches(
    limit: int = Query(10, ge=1, le=50, description="Max searches to return"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Get user's recent search history.

    Args:
        limit: Maximum number of searches to return
        credentials: Authorization credentials
        auth_service: Injected authentication service

    Returns:
        List of recent searches
    """
    try:
        # Get current user
        token = credentials.credentials
        current_user = await auth_service.get_current_user(token)
        
        # TODO: Implement actual search history retrieval
        # For now, return mock data
        
        recent_searches = [
            {
                "id": "search-1",
                "query": "Hotels in Paris",
                "type": "accommodation",
                "timestamp": "2025-06-05T10:00:00Z",
                "results_count": 45,
            },
            {
                "id": "search-2",
                "query": "Flights NYC to London",
                "type": "flight",
                "timestamp": "2025-06-04T15:30:00Z",
                "results_count": 23,
            },
            {
                "id": "search-3",
                "query": "Activities in Tokyo",
                "type": "activity",
                "timestamp": "2025-06-03T09:15:00Z",
                "results_count": 67,
            },
        ]
        
        return recent_searches[:limit]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recent searches: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recent searches",
        )


# Helper functions for searching different resource types

async def _search_destinations(
    search_request: UnifiedSearchRequest,
    destination_service: DestinationService,
    skip: int,
    limit: int,
) -> tuple[List[SearchResultItem], List[SearchFacet]]:
    """Search destinations."""
    results = []
    facets = []
    
    # TODO: Implement actual destination search
    # For now, return mock data
    
    mock_destinations = [
        SearchResultItem(
            id="dest-1",
            type="destination",
            title="Paris, France",
            description="The City of Light - famous for the Eiffel Tower, art, and cuisine",
            image_url="https://example.com/paris.jpg",
            price=None,
            location="France",
            rating=4.8,
            relevance_score=0.95,
            metadata={
                "country": "France",
                "region": "Île-de-France",
                "attractions": ["Eiffel Tower", "Louvre", "Notre-Dame"],
            },
        ),
    ]
    
    if "paris" in search_request.query.lower():
        results.extend(mock_destinations)
    
    return results, facets


async def _search_flights(
    search_request: UnifiedSearchRequest,
    flight_service: FlightService,
    skip: int,
    limit: int,
) -> tuple[List[SearchResultItem], List[SearchFacet]]:
    """Search flights."""
    results = []
    facets = []
    
    # TODO: Implement actual flight search integration
    # For now, return empty results
    
    return results, facets


async def _search_accommodations(
    search_request: UnifiedSearchRequest,
    accommodation_service: AccommodationService,
    skip: int,
    limit: int,
) -> tuple[List[SearchResultItem], List[SearchFacet]]:
    """Search accommodations."""
    results = []
    facets = []
    
    # TODO: Implement actual accommodation search integration
    # For now, return empty results
    
    return results, facets


async def _search_activities(
    search_request: UnifiedSearchRequest,
    skip: int,
    limit: int,
) -> tuple[List[SearchResultItem], List[SearchFacet]]:
    """Search activities."""
    results = []
    facets = []
    
    # TODO: Implement actual activity search
    # For now, return mock data based on query
    
    if "paris" in search_request.query.lower():
        results.append(
            SearchResultItem(
                id="act-1",
                type="activity",
                title="Eiffel Tower Skip-the-Line Tour",
                description="Skip the lines and enjoy guided tour with stunning views",
                image_url="https://example.com/eiffel-tour.jpg",
                price=89.99,
                location="Paris, France",
                rating=4.8,
                relevance_score=0.90,
                metadata={
                    "duration": "2 hours",
                    "category": "tour",
                    "instant_confirmation": True,
                },
            )
        )
    
    return results, facets