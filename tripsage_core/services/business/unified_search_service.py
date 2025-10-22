"""Unified search service for TripSage.

This service orchestrates searches across multiple resource types (destinations,
flights, accommodations, activities) and provides a unified interface for
cross-resource search operations. It leverages existing business services
to avoid code duplication while providing enhanced search capabilities.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

from tripsage.api.schemas.requests.search import UnifiedSearchRequest
from tripsage.api.schemas.responses.search import (
    SearchFacet,
    SearchResultItem,
    UnifiedSearchResponse,
)
from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.infrastructure.search_cache_mixin import SearchCacheMixin
from tripsage_core.utils.decorator_utils import with_error_handling
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)

# Resource type mapping for search
RESOURCE_TYPES = {
    "destination": "destinations",
    "flight": "flights",
    "accommodation": "accommodations",
    "activity": "activities",
}

# Default search types if none specified
DEFAULT_SEARCH_TYPES = ["destination", "activity", "accommodation"]


class UnifiedSearchServiceError(CoreServiceError):
    """Exception raised for unified search service errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        """Construct the error with optional original exception."""
        details = {
            "additional_context": {
                "original_error": str(original_error) if original_error else None
            }
        }
        super().__init__(
            message=message,
            code="UNIFIED_SEARCH_ERROR",
            service="UnifiedSearchService",
            details=details,
        )
        self.original_error = original_error


class UnifiedSearchService(
    SearchCacheMixin[UnifiedSearchRequest, UnifiedSearchResponse]
):
    """Service for unified search across multiple resource types."""

    def __init__(
        self,
        *,
        cache_service,
        destination_service=None,
        activity_service=None,
        flight_service=None,
        accommodation_service=None,
    ):
        """Initialize unified search service.

        Args:
            cache_service: Cache service instance
            destination_service: Destination service
            activity_service: Activity service
            flight_service: Flight service
            accommodation_service: Accommodation service instance
        """
        self._cache_service = cache_service
        self._cache_ttl = 300  # 5 minutes for search results
        self._cache_prefix = "unified_search"

        # Collaborators are injected; no lazy globals
        self._destination_service = destination_service
        self._flight_service = flight_service
        self._accommodation_service = accommodation_service
        self._activity_service = activity_service

    def get_cache_fields(self, request: UnifiedSearchRequest) -> dict[str, Any]:
        """Extract fields for cache key generation."""
        cache_fields = {
            "query": request.query,
            "types": sorted(request.types or DEFAULT_SEARCH_TYPES),
            "destination": request.destination,
            "start_date": request.start_date.isoformat()
            if request.start_date
            else None,
            "end_date": request.end_date.isoformat() if request.end_date else None,
            "origin": request.origin,
            "adults": request.adults,
            "children": request.children,
            "infants": request.infants,
            "sort_by": request.sort_by,
            "sort_order": request.sort_order,
        }

        # Include filters if present
        if request.filters:
            cache_fields.update(
                {
                    "price_min": request.filters.price_min,
                    "price_max": request.filters.price_max,
                    "rating_min": request.filters.rating_min,
                    "latitude": request.filters.latitude,
                    "longitude": request.filters.longitude,
                    "radius_km": request.filters.radius_km,
                }
            )

        return cache_fields

    def _get_response_class(self) -> type[UnifiedSearchResponse]:
        """Get the response class for deserialization."""
        return UnifiedSearchResponse

    @with_error_handling()
    async def unified_search(
        self, request: UnifiedSearchRequest
    ) -> UnifiedSearchResponse:
        """Perform unified search across multiple resource types.

        Args:
            request: Unified search request

        Returns:
            Unified search response with results from all requested types

        Raises:
            UnifiedSearchServiceError: If search fails
        """
        # Dependencies are injected; no lazy ensures

        try:
            logger.info(
                "Unified search request: '%s' across types: %s",
                request.query,
                request.types,
            )

            start_time = datetime.now()

            # Check cache first
            cached_result = await self.get_cached_search(request)
            if cached_result:
                logger.info(
                    "Returning cached unified search results for: %s", request.query
                )
                return cached_result

            # Determine which types to search
            search_types = request.types or DEFAULT_SEARCH_TYPES

            # Prepare search tasks for parallel execution
            search_tasks = {}
            provider_errors = {}

            # Destination search
            if "destination" in search_types:
                search_tasks["destination"] = self._search_destinations(request)

            # Activity search
            if "activity" in search_types:
                search_tasks["activity"] = self._search_activities(request)

            # Flight search (if origin is provided)
            if "flight" in search_types and request.origin and request.destination:
                search_tasks["flight"] = self._search_flights(request)

            # Accommodation search
            if "accommodation" in search_types and request.destination:
                search_tasks["accommodation"] = self._search_accommodations(request)

            # Execute searches in parallel
            if search_tasks:
                search_results = await asyncio.gather(
                    *search_tasks.values(), return_exceptions=True
                )

                # Process results
                all_results = []
                results_by_type = {}

                for search_type, result in zip(
                    list(search_tasks.keys()), list(search_results), strict=False
                ):
                    if isinstance(result, Exception):
                        logger.warning("Search failed for %s: %s", search_type, result)
                        provider_errors[search_type] = str(result)
                        results_by_type[search_type] = []
                    else:
                        type_results = list(result) if isinstance(result, list) else []
                        all_results.extend(type_results)
                        results_by_type[search_type] = type_results
                        logger.debug(
                            "Found %s %s results", len(type_results), search_type
                        )
            else:
                all_results = []
                results_by_type = {}
                logger.warning(
                    "No valid search types provided or insufficient parameters"
                )

            # Apply cross-type sorting and filtering
            filtered_results = self._apply_unified_filters(all_results, request)
            sorted_results = self._sort_unified_results(filtered_results, request)

            # Generate facets for filtering UI
            facets = self._generate_facets(all_results)

            # Calculate search time
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Create response
            search_id = str(uuid.uuid4())
            response = UnifiedSearchResponse.model_validate(
                {
                    "results": sorted_results,
                    "facets": facets,
                    "metadata": {
                        "total_results": len(all_results),
                        "returned_results": len(sorted_results),
                        "search_time_ms": search_time_ms,
                        "cached_results": 0,
                        "search_id": search_id,
                        "user_id": None,
                        "personalized": None,
                        "providers_queried": list(search_tasks.keys()),
                        "provider_errors": provider_errors or None,
                    },
                    "results_by_type": results_by_type,
                    "errors": provider_errors or None,
                }
            )

            # Cache the results
            await self.cache_search_results(request, response)

            logger.info(
                "Unified search completed: %s total results", len(sorted_results)
            )
            return response

        except Exception as e:
            logger.exception("Unified search failed")
            raise UnifiedSearchServiceError(f"Unified search failed: {e}", e) from e

    async def _search_destinations(
        self, request: UnifiedSearchRequest
    ) -> list[SearchResultItem]:
        """Search destinations and convert to unified results."""
        try:
            # Use the destination service to search
            # For now, we'll create basic destination results based on the query
            results = []

            if request.destination or "destination" in request.query.lower():
                # Create a destination result based on the query
                destination_query = request.destination or request.query

                result = SearchResultItem.model_validate(
                    {
                        "id": f"dest_{uuid.uuid4().hex[:8]}",
                        "type": "destination",
                        "title": destination_query.title(),
                        "description": (
                            f"Explore {destination_query} - discover attractions, "
                            f"activities, and local experiences"
                        ),
                        "location": destination_query,
                        "relevance_score": 0.9,
                        "match_reasons": ["Query matches destination name"],
                        "quick_actions": [
                            {"action": "explore", "label": "Explore Destination"},
                            {"action": "activities", "label": "Find Activities"},
                            {"action": "hotels", "label": "Find Hotels"},
                        ],
                        "metadata": {
                            "country": "Unknown",
                            "category": "city",
                            "popularity_score": 0.8,
                        },
                    }
                )
                results.append(result)

            return results
        except (ValueError, KeyError, CoreServiceError) as e:
            logger.warning("Destination search failed: %s", e)
            return []

    async def _search_activities(
        self, request: UnifiedSearchRequest
    ) -> list[SearchResultItem]:
        """Search activities and convert to unified results."""
        try:
            if not request.destination:
                return []

            # Create activity search request
            from tripsage.api.schemas.requests.activities import ActivitySearchRequest

            activity_request = ActivitySearchRequest.model_validate(
                {
                    "destination": request.destination,
                    "start_date": request.start_date or datetime.now().date(),
                    "adults": request.adults or 1,
                    "children": request.children or 0,
                    "infants": request.infants or 0,
                    "rating": request.filters.rating_min if request.filters else None,
                }
            )

            # Search using activity service
            assert self._activity_service is not None
            activity_response = await self._activity_service.search_activities(
                activity_request
            )

            # Convert to unified results
            results = []
            for activity in activity_response.activities:
                result = SearchResultItem.model_validate(
                    {
                        "id": activity.id,
                        "type": "activity",
                        "title": activity.name,
                        "description": activity.description,
                        "image_url": None,
                        "price": activity.price,
                        "currency": "USD",
                        "location": activity.location,
                        "rating": activity.rating,
                        "review_count": None,
                        "relevance_score": (
                            min(activity.rating / 5.0, 1.0) if activity.rating else 0.0
                        ),
                        "match_reasons": ["Activity in requested destination"],
                        "quick_actions": [
                            {"action": "view", "label": "View Details"},
                            {"action": "book", "label": "Book Now"},
                            {"action": "save", "label": "Save to Trip"},
                        ],
                        "metadata": {
                            "activity_type": activity.type,
                            "duration": activity.duration,
                            "provider": activity.provider,
                            "coordinates": (
                                activity.coordinates.model_dump()
                                if activity.coordinates
                                else None
                            ),
                        },
                    }
                )
                results.append(result)

            return results
        except (ValueError, KeyError, CoreServiceError) as e:
            logger.warning("Activity search failed: %s", e)
            return []

    async def _search_flights(
        self, request: UnifiedSearchRequest
    ) -> list[SearchResultItem]:
        """Search flights and convert to unified results."""
        try:
            # For now, return empty as flight service integration needs more work
            # TODO: Implement flight search integration when flight service is available
            logger.debug("Flight search not yet implemented in unified search")
            return []
        except (ValueError, KeyError, CoreServiceError) as e:
            logger.warning("Flight search failed: %s", e)
            return []

    async def _search_accommodations(
        self, request: UnifiedSearchRequest
    ) -> list[SearchResultItem]:
        """Search accommodations and convert to unified results."""
        try:
            # For now, return empty as accommodation service integration needs more work
            # TODO: Implement accommodation search integration when service is available
            logger.debug("Accommodation search not yet implemented in unified search")
            return []
        except (ValueError, KeyError, CoreServiceError) as e:
            logger.warning("Accommodation search failed: %s", e)
            return []

    def _apply_unified_filters(
        self, results: list[SearchResultItem], request: UnifiedSearchRequest
    ) -> list[SearchResultItem]:
        """Apply filters across all result types."""
        if not request.filters:
            return results

        filtered = results

        # Price range filter
        if request.filters.price_min is not None:
            filtered = [
                r
                for r in filtered
                if r.price is None or r.price >= request.filters.price_min
            ]

        if request.filters.price_max is not None:
            filtered = [
                r
                for r in filtered
                if r.price is None or r.price <= request.filters.price_max
            ]

        # Rating filter
        if request.filters.rating_min is not None:
            filtered = [
                r
                for r in filtered
                if r.rating is None or r.rating >= request.filters.rating_min
            ]

        return filtered

    def _sort_unified_results(
        self, results: list[SearchResultItem], request: UnifiedSearchRequest
    ) -> list[SearchResultItem]:
        """Sort results across all types."""
        sort_by = request.sort_by or "relevance"
        reverse = request.sort_order == "desc"

        if sort_by == "price":
            # Sort by price, putting items without prices at the end
            results.sort(
                key=lambda x: (x.price is None, x.price if x.price else 0),
                reverse=reverse,
            )
        elif sort_by == "rating":
            # Sort by rating, putting items without ratings at the end
            results.sort(
                key=lambda x: (x.rating is None, x.rating if x.rating else 0),
                reverse=reverse,
            )
        elif sort_by == "relevance":
            # Sort by relevance score
            results.sort(
                key=lambda x: x.relevance_score or 0,
                reverse=True,  # Always desc for relevance
            )

        return results

    def _generate_facets(self, results: list[SearchResultItem]) -> list[SearchFacet]:
        """Generate facets for filtering UI."""
        facets = []

        # Type facet
        type_counts = {}
        for result in results:
            type_counts[result.type] = type_counts.get(result.type, 0) + 1

        if type_counts:
            type_facet = SearchFacet(
                field="type",
                label="Type",
                type="terms",
                values=[
                    {"value": k, "label": k.title(), "count": v}
                    for k, v in sorted(type_counts.items())
                ],
            )
            facets.append(type_facet)

        # Price range facet
        prices = [r.price for r in results if r.price is not None]
        if prices:
            price_facet = SearchFacet(
                field="price",
                label="Price Range",
                type="range",
                values=[{"min": min(prices), "max": max(prices), "count": len(prices)}],
            )
            facets.append(price_facet)

        # Rating facet
        ratings = [r.rating for r in results if r.rating is not None]
        if ratings:
            rating_facet = SearchFacet(
                field="rating",
                label="Rating",
                type="range",
                values=[
                    {"min": min(ratings), "max": max(ratings), "count": len(ratings)}
                ],
            )
            facets.append(rating_facet)

        return facets

    @with_error_handling()
    async def get_search_suggestions(self, query: str, limit: int = 10) -> list[str]:
        """Get search suggestions based on partial query.

        Args:
            query: Partial search query
            limit: Maximum number of suggestions

        Returns:
            List of search suggestions

        Raises:
            UnifiedSearchServiceError: If suggestion generation fails
        """
        try:
            suggestions = []
            query_lower = query.lower()

            # Basic destination suggestions
            common_destinations = [
                "Paris, France",
                "Tokyo, Japan",
                "New York, USA",
                "London, UK",
                "Rome, Italy",
                "Barcelona, Spain",
                "Amsterdam, Netherlands",
                "Sydney, Australia",
                "Bangkok, Thailand",
                "Dubai, UAE",
            ]

            destination_suggestions = [
                dest for dest in common_destinations if query_lower in dest.lower()
            ]
            suggestions.extend(destination_suggestions[: limit // 2])

            # Activity type suggestions
            activity_types = [
                "museums",
                "restaurants",
                "tours",
                "outdoor activities",
                "nightlife",
                "shopping",
                "cultural experiences",
                "adventure sports",
            ]

            activity_suggestions = [
                f"{atype} in {query}" for atype in activity_types if len(query) > 2
            ]
            suggestions.extend(activity_suggestions[: limit // 2])

            return suggestions[:limit]

        except Exception as e:
            logger.exception("Failed to get search suggestions")
            raise UnifiedSearchServiceError(f"Failed to get suggestions: {e}", e) from e


# FINAL-ONLY: Removed module-level singleton and factory. Inject this service
# via application DI with required collaborators.
