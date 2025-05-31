"""
Service for destination-related operations in the TripSage API.

This service acts as a thin wrapper around the core destination service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import List, Optional

from fastapi import Depends

from tripsage.api.models.common.destinations import (
    Destination,
)
from tripsage.api.models.requests.destinations import (
    DestinationSearchRequest,
    PointOfInterestSearchRequest,
)
from tripsage.api.models.responses.destinations import (
    DestinationDetailsResponse as DestinationDetails,
)
from tripsage.api.models.responses.destinations import (
    DestinationSearchResponse,
    PointOfInterestSearchResponse,
)
from tripsage.api.models.responses.destinations import (
    DestinationSuggestionResponse as DestinationRecommendation,
)
from tripsage.api.models.responses.destinations import (
    SavedDestinationResponse as SavedDestination,
)
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as ResourceNotFoundError,
)
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.destination_service import (
    DestinationService as CoreDestinationService,
)
from tripsage_core.services.business.destination_service import (
    get_destination_service as get_core_destination_service,
)

logger = logging.getLogger(__name__)


class DestinationService:
    """
    API destination service that delegates to core business services.

    This service acts as a façade, handling:
    - Model adaptation between API and core models
    - API-specific error handling
    - FastAPI dependency integration
    """

    def __init__(
        self, core_destination_service: Optional[CoreDestinationService] = None
    ):
        """
        Initialize the API destination service.

        Args:
            core_destination_service: Core destination service
        """
        self.core_destination_service = core_destination_service

    async def _get_core_destination_service(self) -> CoreDestinationService:
        """Get or create core destination service instance."""
        if self.core_destination_service is None:
            self.core_destination_service = await get_core_destination_service()
        return self.core_destination_service

    async def search_destinations(
        self, request: DestinationSearchRequest
    ) -> DestinationSearchResponse:
        """Search for destinations based on provided criteria.

        Args:
            request: Destination search request

        Returns:
            Destination search results

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If search fails
        """
        try:
            logger.info(f"Searching for destinations with query: {request.query}")

            # Adapt API request to core model
            core_request = self._adapt_destination_search_request(request)

            # Search via core service
            core_service = await self._get_core_destination_service()
            core_response = await core_service.search_destinations(core_request)

            # Adapt core response to API model
            return self._adapt_destination_search_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Destination search failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in destination search: {str(e)}")
            raise ServiceError("Destination search failed") from e

    async def get_destination_details(self, destination_id: str) -> DestinationDetails:
        """Get detailed information about a specific destination.

        Args:
            destination_id: Destination ID

        Returns:
            Destination details

        Raises:
            ResourceNotFoundError: If destination not found
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting details for destination ID: {destination_id}")

            # Get details via core service
            core_service = await self._get_core_destination_service()
            core_response = await core_service.get_destination_details(destination_id)

            # Adapt core response to API model
            return self._adapt_destination_details(core_response)

        except ResourceNotFoundError as e:
            logger.error(f"Destination {destination_id} not found: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to get destination details: {str(e)}")
            raise ServiceError("Failed to get destination details") from e

    async def save_destination(
        self, user_id: str, destination_id: str, notes: Optional[str] = None
    ) -> SavedDestination:
        """Save a destination for a user.

        Args:
            user_id: User ID
            destination_id: Destination ID
            notes: Optional notes

        Returns:
            Saved destination

        Raises:
            ResourceNotFoundError: If destination not found
            ValidationError: If request data is invalid
            ServiceError: If save fails
        """
        try:
            logger.info(f"Saving destination {destination_id} for user {user_id}")

            # Save via core service
            core_service = await self._get_core_destination_service()
            core_response = await core_service.save_destination(
                user_id, destination_id, notes
            )

            # Adapt core response to API model
            return self._adapt_saved_destination(core_response)

        except (ResourceNotFoundError, ValidationError, ServiceError) as e:
            logger.error(f"Failed to save destination: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving destination: {str(e)}")
            raise ServiceError("Failed to save destination") from e

    async def get_saved_destinations(self, user_id: str) -> List[SavedDestination]:
        """Get all destinations saved by a user.

        Args:
            user_id: User ID

        Returns:
            List of saved destinations

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting saved destinations for user {user_id}")

            # Get saved destinations via core service
            core_service = await self._get_core_destination_service()
            core_destinations = await core_service.get_saved_destinations(user_id)

            # Adapt core response to API model
            return [
                self._adapt_saved_destination(destination)
                for destination in core_destinations
            ]

        except Exception as e:
            logger.error(f"Failed to get saved destinations: {str(e)}")
            raise ServiceError("Failed to get saved destinations") from e

    async def delete_saved_destination(self, user_id: str, destination_id: str) -> None:
        """Delete a saved destination for a user.

        Args:
            user_id: User ID
            destination_id: Destination ID

        Raises:
            ResourceNotFoundError: If saved destination not found
            ServiceError: If deletion fails
        """
        try:
            logger.info(
                f"Deleting saved destination {destination_id} for user {user_id}"
            )

            # Delete via core service
            core_service = await self._get_core_destination_service()
            await core_service.delete_saved_destination(user_id, destination_id)

        except ResourceNotFoundError as e:
            logger.error(f"Saved destination not found: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to delete saved destination: {str(e)}")
            raise ServiceError("Failed to delete saved destination") from e

    async def search_points_of_interest(
        self, request: PointOfInterestSearchRequest
    ) -> PointOfInterestSearchResponse:
        """Search for points of interest in a destination.

        Args:
            request: Point of interest search request

        Returns:
            Point of interest search results

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If search fails
        """
        try:
            logger.info(
                f"Searching for points of interest in {request.destination_id} "
                f"with category: {request.category}"
            )

            # Adapt API request to core model
            core_request = self._adapt_poi_search_request(request)

            # Search via core service
            core_service = await self._get_core_destination_service()
            core_response = await core_service.search_points_of_interest(core_request)

            # Adapt core response to API model
            return self._adapt_poi_search_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"POI search failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in POI search: {str(e)}")
            raise ServiceError("POI search failed") from e

    async def get_destination_recommendations(
        self, user_id: str
    ) -> List[DestinationRecommendation]:
        """Get personalized destination recommendations for a user.

        Args:
            user_id: User ID

        Returns:
            List of destination recommendations

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting destination recommendations for user {user_id}")

            # Get recommendations via core service
            core_service = await self._get_core_destination_service()
            core_recommendations = await core_service.get_destination_recommendations(
                user_id
            )

            # Adapt core response to API model
            return [
                self._adapt_destination_recommendation(recommendation)
                for recommendation in core_recommendations
            ]

        except Exception as e:
            logger.error(f"Failed to get destination recommendations: {str(e)}")
            raise ServiceError("Failed to get destination recommendations") from e

    def _adapt_destination_search_request(
        self, request: DestinationSearchRequest
    ) -> dict:
        """Adapt API destination search request to core model."""
        return {
            "query": request.query,
            "category": getattr(request, "category", None),
            "country": getattr(request, "country", None),
            "limit": getattr(request, "limit", 10),
            "offset": getattr(request, "offset", 0),
        }

    def _adapt_poi_search_request(self, request: PointOfInterestSearchRequest) -> dict:
        """Adapt API POI search request to core model."""
        return {
            "destination_id": request.destination_id,
            "category": request.category,
            "query": getattr(request, "query", None),
            "limit": getattr(request, "limit", 10),
            "offset": getattr(request, "offset", 0),
        }

    def _adapt_destination_search_response(
        self, core_response
    ) -> DestinationSearchResponse:
        """Adapt core destination search response to API model."""
        destinations = []
        for core_destination in core_response.get("destinations", []):
            destination = self._adapt_destination(core_destination)
            if destination:
                destinations.append(destination)

        return DestinationSearchResponse(
            results=destinations,
            total_count=core_response.get("total_count", len(destinations)),
            page=core_response.get("page", 1),
            page_size=core_response.get("page_size", 10),
        )

    def _adapt_poi_search_response(
        self, core_response
    ) -> PointOfInterestSearchResponse:
        """Adapt core POI search response to API model."""
        pois = core_response.get("pois", [])

        return PointOfInterestSearchResponse(
            results=pois,
            total_count=core_response.get("total_count", len(pois)),
            page=core_response.get("page", 1),
            page_size=core_response.get("page_size", 10),
        )

    def _adapt_destination(self, core_destination) -> Optional[Destination]:
        """Adapt core destination to API model."""
        if not core_destination:
            return None

        return Destination(
            id=core_destination.get("id", ""),
            name=core_destination.get("name", ""),
            country=core_destination.get("country", ""),
            description=core_destination.get("description", ""),
            image_url=core_destination.get("image_url", ""),
            rating=core_destination.get("rating", 0.0),
            category=core_destination.get("category", ""),
        )

    def _adapt_destination_details(self, core_details) -> DestinationDetails:
        """Adapt core destination details to API model."""
        return DestinationDetails(
            id=core_details.get("id", ""),
            name=core_details.get("name", ""),
            country=core_details.get("country", ""),
            description=core_details.get("description", ""),
            long_description=core_details.get("long_description", ""),
            image_url=core_details.get("image_url", ""),
            gallery_urls=core_details.get("gallery_urls", []),
            rating=core_details.get("rating", 0.0),
            category=core_details.get("category", ""),
            best_times_to_visit=core_details.get("best_times_to_visit", []),
            coordinates=core_details.get("coordinates", {}),
            currency=core_details.get("currency", ""),
            languages=core_details.get("languages", []),
            timezone=core_details.get("timezone", ""),
            weather_summary=core_details.get("weather_summary", ""),
            top_attractions=core_details.get("top_attractions", []),
            local_tips=core_details.get("local_tips", []),
        )

    def _adapt_saved_destination(self, core_saved_destination) -> SavedDestination:
        """Adapt core saved destination to API model."""
        return SavedDestination(
            id=core_saved_destination.get("id", ""),
            user_id=core_saved_destination.get("user_id", ""),
            destination_id=core_saved_destination.get("destination_id", ""),
            destination_name=core_saved_destination.get("destination_name", ""),
            destination_country=core_saved_destination.get("destination_country", ""),
            date_saved=core_saved_destination.get("date_saved", ""),
            notes=core_saved_destination.get("notes"),
        )

    def _adapt_destination_recommendation(
        self, core_recommendation
    ) -> DestinationRecommendation:
        """Adapt core destination recommendation to API model."""
        return DestinationRecommendation(
            destination=self._adapt_destination(core_recommendation.get("destination")),
            reasons=core_recommendation.get("reasons", []),
            match_score=core_recommendation.get("match_score", 0.0),
        )


# Module-level dependency annotation
_core_destination_service_dep = Depends(get_core_destination_service)


# Dependency function for FastAPI
async def get_destination_service(
    core_destination_service: CoreDestinationService = _core_destination_service_dep,
) -> DestinationService:
    """
    Get destination service instance for dependency injection.

    Args:
        core_destination_service: Core destination service

    Returns:
        DestinationService instance
    """
    return DestinationService(core_destination_service=core_destination_service)
