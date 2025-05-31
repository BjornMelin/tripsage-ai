"""Accommodation service for TripSage API.

This service acts as a thin wrapper around the core accommodation service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import Depends

from tripsage.api.models.common.accommodations import AccommodationListing
from tripsage.api.models.requests.accommodations import (
    AccommodationDetailsRequest,
    AccommodationSearchRequest,
    SavedAccommodationRequest,
)
from tripsage.api.models.responses.accommodations import (
    AccommodationDetailsResponse,
    AccommodationSearchResponse,
    SavedAccommodationResponse,
)
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.accommodation_service import (
    AccommodationService as CoreAccommodationService,
)
from tripsage_core.services.business.accommodation_service import (
    get_accommodation_service as get_core_accommodation_service,
)

logger = logging.getLogger(__name__)


class AccommodationService:
    """
    API accommodation service that delegates to core business services.

    This service acts as a façade, handling:
    - Model adaptation between API and core models
    - API-specific error handling
    - FastAPI dependency integration
    """

    def __init__(
        self, core_accommodation_service: Optional[CoreAccommodationService] = None
    ):
        """
        Initialize the API accommodation service.

        Args:
            core_accommodation_service: Core accommodation service
        """
        self.core_accommodation_service = core_accommodation_service

    async def _get_core_accommodation_service(self) -> CoreAccommodationService:
        """Get or create core accommodation service instance."""
        if self.core_accommodation_service is None:
            self.core_accommodation_service = await get_core_accommodation_service()
        return self.core_accommodation_service

    async def search_accommodations(
        self, request: AccommodationSearchRequest
    ) -> AccommodationSearchResponse:
        """Search for accommodations based on the provided criteria.

        Args:
            request: Accommodation search request parameters

        Returns:
            Accommodation search results

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If search fails
        """
        try:
            logger.info(
                f"Searching for accommodations in {request.location} "
                f"from {request.check_in} to {request.check_out}"
            )

            # Adapt API request to core model
            core_request = self._adapt_accommodation_search_request(request)

            # Search via core service
            core_service = await self._get_core_accommodation_service()
            core_response = await core_service.search_accommodations(core_request)

            # Adapt core response to API model
            return self._adapt_accommodation_search_response(core_response, request)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Accommodation search failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in accommodation search: {str(e)}")
            raise ServiceError("Accommodation search failed") from e

    async def get_accommodation_details(
        self, request: AccommodationDetailsRequest
    ) -> Optional[AccommodationDetailsResponse]:
        """Get details of a specific accommodation listing.

        Args:
            request: Accommodation details request parameters

        Returns:
            Accommodation details response if found, None otherwise

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(
                f"Getting accommodation details for listing ID: {request.listing_id}"
            )

            # Adapt API request to core model
            core_request = self._adapt_accommodation_details_request(request)

            # Get details via core service
            core_service = await self._get_core_accommodation_service()
            core_response = await core_service.get_accommodation_details(core_request)

            if core_response is None:
                return None

            # Adapt core response to API model
            return self._adapt_accommodation_details_response(core_response)

        except Exception as e:
            logger.error(f"Failed to get accommodation details: {str(e)}")
            raise ServiceError("Failed to get accommodation details") from e

    async def save_accommodation(
        self, user_id: str, request: SavedAccommodationRequest
    ) -> Optional[SavedAccommodationResponse]:
        """Save an accommodation listing for a trip.

        Args:
            user_id: User ID
            request: Save accommodation request

        Returns:
            Saved accommodation response if successful, None otherwise

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If save fails
        """
        try:
            logger.info(
                f"Saving accommodation {request.listing_id} for user {user_id} "
                f"and trip {request.trip_id}"
            )

            # Adapt API request to core model
            core_request = self._adapt_save_accommodation_request(request)

            # Save via core service
            core_service = await self._get_core_accommodation_service()
            core_response = await core_service.save_accommodation(user_id, core_request)

            if core_response is None:
                return None

            # Adapt core response to API model
            return self._adapt_saved_accommodation_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Failed to save accommodation: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving accommodation: {str(e)}")
            raise ServiceError("Failed to save accommodation") from e

    async def delete_saved_accommodation(
        self, user_id: str, saved_accommodation_id: UUID
    ) -> bool:
        """Delete a saved accommodation.

        Args:
            user_id: User ID
            saved_accommodation_id: Saved accommodation ID

        Returns:
            True if deleted, False otherwise

        Raises:
            ServiceError: If deletion fails
        """
        try:
            logger.info(
                f"Deleting saved accommodation {saved_accommodation_id} "
                f"for user {user_id}"
            )

            # Delete via core service
            core_service = await self._get_core_accommodation_service()
            return await core_service.delete_saved_accommodation(
                user_id, str(saved_accommodation_id)
            )

        except Exception as e:
            logger.error(f"Failed to delete saved accommodation: {str(e)}")
            raise ServiceError("Failed to delete saved accommodation") from e

    async def list_saved_accommodations(
        self, user_id: str, trip_id: Optional[UUID] = None
    ) -> List[SavedAccommodationResponse]:
        """List saved accommodations for a user, optionally filtered by trip.

        Args:
            user_id: User ID
            trip_id: Optional trip ID to filter by

        Returns:
            List of saved accommodations

        Raises:
            ServiceError: If listing fails
        """
        try:
            logger.info(
                f"Listing saved accommodations for user {user_id}"
                + (f" and trip {trip_id}" if trip_id else "")
            )

            # List via core service
            core_service = await self._get_core_accommodation_service()
            core_accommodations = await core_service.list_saved_accommodations(
                user_id, str(trip_id) if trip_id else None
            )

            # Adapt core response to API model
            return [
                self._adapt_saved_accommodation_response(accommodation)
                for accommodation in core_accommodations
            ]

        except Exception as e:
            logger.error(f"Failed to list saved accommodations: {str(e)}")
            raise ServiceError("Failed to list saved accommodations") from e

    async def update_saved_accommodation_status(
        self, user_id: str, saved_accommodation_id: UUID, status: str
    ) -> Optional[SavedAccommodationResponse]:
        """Update the status of a saved accommodation.

        Args:
            user_id: User ID
            saved_accommodation_id: Saved accommodation ID
            status: New status

        Returns:
            Updated saved accommodation if successful, None otherwise

        Raises:
            ValidationError: If status is invalid
            ServiceError: If update fails
        """
        try:
            logger.info(
                f"Updating saved accommodation {saved_accommodation_id} status to "
                f"{status} "
                f"for user {user_id}"
            )

            # Update via core service
            core_service = await self._get_core_accommodation_service()
            core_response = await core_service.update_saved_accommodation_status(
                user_id, str(saved_accommodation_id), status
            )

            if core_response is None:
                return None

            # Adapt core response to API model
            return self._adapt_saved_accommodation_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Failed to update accommodation status: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating accommodation status: {str(e)}")
            raise ServiceError("Failed to update accommodation status") from e

    def _adapt_accommodation_search_request(
        self, request: AccommodationSearchRequest
    ) -> dict:
        """Adapt API accommodation search request to core model."""
        return {
            "location": request.location,
            "check_in": request.check_in,
            "check_out": request.check_out,
            "guests": getattr(request, "guests", 2),
            "rooms": getattr(request, "rooms", 1),
            "property_type": getattr(request, "property_type", None),
            "min_price": getattr(request, "min_price", None),
            "max_price": getattr(request, "max_price", None),
            "amenities": getattr(request, "amenities", None),
            "rating_min": getattr(request, "rating_min", None),
            "sort_by": getattr(request, "sort_by", "price"),
            "limit": getattr(request, "limit", 20),
        }

    def _adapt_accommodation_details_request(
        self, request: AccommodationDetailsRequest
    ) -> dict:
        """Adapt API accommodation details request to core model."""
        return {
            "listing_id": request.listing_id,
            "check_in": request.check_in,
            "check_out": request.check_out,
        }

    def _adapt_save_accommodation_request(
        self, request: SavedAccommodationRequest
    ) -> dict:
        """Adapt API save accommodation request to core model."""
        return {
            "listing_id": request.listing_id,
            "trip_id": str(request.trip_id) if request.trip_id else None,
            "check_in": request.check_in,
            "check_out": request.check_out,
            "notes": request.notes,
        }

    def _adapt_accommodation_search_response(
        self, core_response, original_request
    ) -> AccommodationSearchResponse:
        """Adapt core accommodation search response to API model."""
        listings = []
        for core_listing in core_response.get("listings", []):
            listing = self._adapt_accommodation_listing(core_listing)
            if listing:
                listings.append(listing)

        return AccommodationSearchResponse(
            listings=listings,
            count=len(listings),
            currency=core_response.get("currency", "USD"),
            search_id=core_response.get("search_id", ""),
            trip_id=original_request.trip_id,
            min_price=core_response.get("min_price"),
            max_price=core_response.get("max_price"),
            avg_price=core_response.get("avg_price"),
            search_request=original_request,
        )

    def _adapt_accommodation_details_response(
        self, core_response
    ) -> AccommodationDetailsResponse:
        """Adapt core accommodation details response to API model."""
        return AccommodationDetailsResponse(
            listing=self._adapt_accommodation_listing(core_response.get("listing")),
            availability=core_response.get("availability", True),
            total_price=core_response.get("total_price"),
        )

    def _adapt_accommodation_listing(
        self, core_listing
    ) -> Optional[AccommodationListing]:
        """Adapt core accommodation listing to API model."""
        if not core_listing:
            return None

        # This is a simplified adaptation - real implementation would need
        # detailed mapping
        from tripsage.api.models.accommodations import (
            AccommodationAmenity,
            AccommodationImage,
            AccommodationLocation,
            PropertyType,
        )

        return AccommodationListing(
            id=core_listing.get("id", ""),
            name=core_listing.get("name", ""),
            description=core_listing.get("description", ""),
            property_type=PropertyType(core_listing.get("property_type", "hotel")),
            location=AccommodationLocation(
                city=core_listing.get("location", {}).get("city", ""),
                country=core_listing.get("location", {}).get("country", ""),
                latitude=core_listing.get("location", {}).get("latitude", 0.0),
                longitude=core_listing.get("location", {}).get("longitude", 0.0),
                neighborhood=core_listing.get("location", {}).get("neighborhood", ""),
                distance_to_center=core_listing.get("location", {}).get(
                    "distance_to_center", 0.0
                ),
            ),
            price_per_night=core_listing.get("price_per_night", 0.0),
            currency=core_listing.get("currency", "USD"),
            rating=core_listing.get("rating", 0.0),
            review_count=core_listing.get("review_count", 0),
            amenities=[
                AccommodationAmenity(name=amenity.get("name", ""))
                for amenity in core_listing.get("amenities", [])
            ],
            images=[
                AccommodationImage(
                    url=image.get("url", ""),
                    caption=image.get("caption", ""),
                    is_primary=image.get("is_primary", False),
                )
                for image in core_listing.get("images", [])
            ],
            max_guests=core_listing.get("max_guests", 2),
            bedrooms=core_listing.get("bedrooms", 1),
            beds=core_listing.get("beds", 1),
            bathrooms=core_listing.get("bathrooms", 1.0),
            check_in_time=core_listing.get("check_in_time", "15:00"),
            check_out_time=core_listing.get("check_out_time", "11:00"),
            url=core_listing.get("url", ""),
            source=core_listing.get("source", ""),
            total_price=core_listing.get("total_price"),
        )

    def _adapt_saved_accommodation_response(
        self, core_response
    ) -> SavedAccommodationResponse:
        """Adapt core saved accommodation response to API model."""
        from tripsage.api.models.accommodations import BookingStatus

        return SavedAccommodationResponse(
            id=core_response.get("id"),
            user_id=core_response.get("user_id", ""),
            trip_id=core_response.get("trip_id"),
            listing=self._adapt_accommodation_listing(core_response.get("listing")),
            check_in=core_response.get("check_in"),
            check_out=core_response.get("check_out"),
            saved_at=core_response.get("saved_at"),
            notes=core_response.get("notes"),
            status=BookingStatus(core_response.get("status", "saved")),
        )


# Module-level dependency annotation
_core_accommodation_service_dep = Depends(get_core_accommodation_service)


# Dependency function for FastAPI
async def get_accommodation_service(
    core_accommodation_service: CoreAccommodationService = (
        _core_accommodation_service_dep
    ),
) -> AccommodationService:
    """
    Get accommodation service instance for dependency injection.

    Args:
        core_accommodation_service: Core accommodation service

    Returns:
        AccommodationService instance
    """
    return AccommodationService(core_accommodation_service=core_accommodation_service)
