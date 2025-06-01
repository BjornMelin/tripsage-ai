"""
Service for itinerary-related operations in the TripSage API.

This service acts as a thin wrapper around the core itinerary service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from datetime import date as DateType
from typing import List

from fastapi import Depends

# Create simple models for missing classes
from pydantic import BaseModel, Field

from tripsage.api.models.requests.itineraries import (
    ItineraryCreateRequest,
    ItineraryItemCreateRequest,
    ItineraryItemUpdateRequest,
    ItineraryOptimizeRequest,
    ItinerarySearchRequest,
    ItineraryUpdateRequest,
)
from tripsage.api.models.responses.itineraries import (
    Itinerary,
    ItineraryConflictCheckResponse,
    ItineraryOptimizeResponse,
    ItinerarySearchResponse,
)
from tripsage_core.exceptions import CoreResourceNotFoundError as ResourceNotFoundError
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.models.db.itinerary_item import ItineraryItem
from tripsage_core.models.schemas_common.enums import TripStatus as ItineraryStatus
from tripsage_core.services.business.itinerary_service import (
    ItineraryService as CoreItineraryService,
)
from tripsage_core.services.business.itinerary_service import (
    get_itinerary_service as get_core_itinerary_service,
)


class ItineraryDay(BaseModel):
    date: DateType = Field(..., description="Date of the itinerary day")
    items: List[ItineraryItem] = Field(default=[], description="Items for this day")


logger = logging.getLogger(__name__)


class ItineraryService:
    """
    API itinerary service that delegates to core business services.

    This service acts as a façade, handling:
    - Model adaptation between API and core models
    - API-specific error handling
    - FastAPI dependency integration
    """

    def __init__(self, core_itinerary_service: CoreItineraryService = None):
        """
        Initialize the API itinerary service.

        Args:
            core_itinerary_service: Core itinerary service
        """
        self.core_itinerary_service = core_itinerary_service

    async def _get_core_itinerary_service(self) -> CoreItineraryService:
        """Get or create core itinerary service instance."""
        if self.core_itinerary_service is None:
            self.core_itinerary_service = await get_core_itinerary_service()
        return self.core_itinerary_service

    async def create_itinerary(
        self,
        user_id: str,
        request: ItineraryCreateRequest,
    ) -> Itinerary:
        """Create a new itinerary for a user.

        Args:
            user_id: User ID
            request: Itinerary creation request

        Returns:
            Created itinerary

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If creation fails
        """
        try:
            logger.info(f"Creating new itinerary for user {user_id}: {request.title}")

            # Adapt API request to core model
            core_request = self._adapt_itinerary_create_request(request)

            # Create via core service
            core_service = await self._get_core_itinerary_service()
            core_response = await core_service.create_itinerary(user_id, core_request)

            # Adapt core response to API model
            return self._adapt_itinerary(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Itinerary creation failed: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating itinerary: {e!s}")
            raise ServiceError("Failed to create itinerary") from e

    async def get_itinerary(self, user_id: str, itinerary_id: str) -> Itinerary:
        """Get an itinerary by ID.

        Args:
            user_id: User ID
            itinerary_id: Itinerary ID

        Returns:
            Itinerary

        Raises:
            ResourceNotFoundError: If itinerary not found
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting itinerary {itinerary_id} for user {user_id}")

            # Get via core service
            core_service = await self._get_core_itinerary_service()
            core_response = await core_service.get_itinerary(user_id, itinerary_id)

            # Adapt core response to API model
            return self._adapt_itinerary(core_response)

        except ResourceNotFoundError as e:
            logger.error(f"Itinerary not found: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Failed to get itinerary: {e!s}")
            raise ServiceError("Failed to get itinerary") from e

    async def update_itinerary(
        self,
        user_id: str,
        itinerary_id: str,
        request: ItineraryUpdateRequest,
    ) -> Itinerary:
        """Update an existing itinerary.

        Args:
            user_id: User ID
            itinerary_id: Itinerary ID
            request: Update request

        Returns:
            Updated itinerary

        Raises:
            ResourceNotFoundError: If itinerary not found
            ValidationError: If request data is invalid
            ServiceError: If update fails
        """
        try:
            logger.info(f"Updating itinerary {itinerary_id} for user {user_id}")

            # Adapt API request to core model
            core_request = self._adapt_itinerary_update_request(request)

            # Update via core service
            core_service = await self._get_core_itinerary_service()
            core_response = await core_service.update_itinerary(
                user_id,
                itinerary_id,
                core_request,
            )

            # Adapt core response to API model
            return self._adapt_itinerary(core_response)

        except (ResourceNotFoundError, ValidationError, ServiceError) as e:
            logger.error(f"Itinerary update failed: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating itinerary: {e!s}")
            raise ServiceError("Failed to update itinerary") from e

    async def delete_itinerary(self, user_id: str, itinerary_id: str) -> None:
        """Delete an itinerary.

        Args:
            user_id: User ID
            itinerary_id: Itinerary ID

        Raises:
            ResourceNotFoundError: If itinerary not found
            ServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting itinerary {itinerary_id} for user {user_id}")

            # Delete via core service
            core_service = await self._get_core_itinerary_service()
            await core_service.delete_itinerary(user_id, itinerary_id)

        except ResourceNotFoundError as e:
            logger.error(f"Itinerary not found: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Failed to delete itinerary: {e!s}")
            raise ServiceError("Failed to delete itinerary") from e

    async def list_itineraries(self, user_id: str) -> list[Itinerary]:
        """List all itineraries for a user.

        Args:
            user_id: User ID

        Returns:
            List of itineraries

        Raises:
            ServiceError: If listing fails
        """
        try:
            logger.info(f"Listing itineraries for user {user_id}")

            # List via core service
            core_service = await self._get_core_itinerary_service()
            core_itineraries = await core_service.list_itineraries(user_id)

            # Adapt core response to API model
            return [self._adapt_itinerary(itinerary) for itinerary in core_itineraries]

        except Exception as e:
            logger.error(f"Failed to list itineraries: {e!s}")
            raise ServiceError("Failed to list itineraries") from e

    async def search_itineraries(
        self,
        user_id: str,
        request: ItinerarySearchRequest,
    ) -> ItinerarySearchResponse:
        """Search for itineraries based on criteria.

        Args:
            user_id: User ID
            request: Search request

        Returns:
            Search results

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If search fails
        """
        try:
            logger.info(f"Searching itineraries for user {user_id} with criteria")

            # Adapt API request to core model
            core_request = self._adapt_itinerary_search_request(request)

            # Search via core service
            core_service = await self._get_core_itinerary_service()
            core_response = await core_service.search_itineraries(user_id, core_request)

            # Adapt core response to API model
            return self._adapt_itinerary_search_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Itinerary search failed: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching itineraries: {e!s}")
            raise ServiceError("Failed to search itineraries") from e

    async def add_item_to_itinerary(
        self,
        user_id: str,
        itinerary_id: str,
        request: ItineraryItemCreateRequest,
    ) -> ItineraryItem:
        """Add an item to an itinerary.

        Args:
            user_id: User ID
            itinerary_id: Itinerary ID
            request: Item creation request

        Returns:
            Created item

        Raises:
            ResourceNotFoundError: If itinerary not found
            ValidationError: If request data is invalid
            ServiceError: If creation fails
        """
        try:
            logger.info(
                f"Adding {request.item_type} item to itinerary {itinerary_id} "
                f"for user {user_id}",
            )

            # Adapt API request to core model
            core_request = self._adapt_itinerary_item_create_request(request)

            # Add item via core service
            core_service = await self._get_core_itinerary_service()
            core_response = await core_service.add_item_to_itinerary(
                user_id,
                itinerary_id,
                core_request,
            )

            # Adapt core response to API model
            return self._adapt_itinerary_item(core_response)

        except (ResourceNotFoundError, ValidationError, ServiceError) as e:
            logger.error(f"Failed to add item to itinerary: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error adding item to itinerary: {e!s}")
            raise ServiceError("Failed to add item to itinerary") from e

    async def update_item(
        self,
        user_id: str,
        itinerary_id: str,
        item_id: str,
        request: ItineraryItemUpdateRequest,
    ) -> ItineraryItem:
        """Update an item in an itinerary.

        Args:
            user_id: User ID
            itinerary_id: Itinerary ID
            item_id: Item ID
            request: Update request

        Returns:
            Updated item

        Raises:
            ResourceNotFoundError: If itinerary or item not found
            ValidationError: If request data is invalid
            ServiceError: If update fails
        """
        try:
            logger.info(
                f"Updating item {item_id} in itinerary {itinerary_id} "
                f"for user {user_id}",
            )

            # Adapt API request to core model
            core_request = self._adapt_itinerary_item_update_request(request)

            # Update item via core service
            core_service = await self._get_core_itinerary_service()
            core_response = await core_service.update_item(
                user_id,
                itinerary_id,
                item_id,
                core_request,
            )

            # Adapt core response to API model
            return self._adapt_itinerary_item(core_response)

        except (ResourceNotFoundError, ValidationError, ServiceError) as e:
            logger.error(f"Failed to update item: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating item: {e!s}")
            raise ServiceError("Failed to update item") from e

    async def delete_item(self, user_id: str, itinerary_id: str, item_id: str) -> None:
        """Delete an item from an itinerary.

        Args:
            user_id: User ID
            itinerary_id: Itinerary ID
            item_id: Item ID

        Raises:
            ResourceNotFoundError: If itinerary or item not found
            ServiceError: If deletion fails
        """
        try:
            logger.info(
                f"Deleting item {item_id} from itinerary {itinerary_id} "
                f"for user {user_id}",
            )

            # Delete item via core service
            core_service = await self._get_core_itinerary_service()
            await core_service.delete_item(user_id, itinerary_id, item_id)

        except ResourceNotFoundError as e:
            logger.error(f"Item not found: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Failed to delete item: {e!s}")
            raise ServiceError("Failed to delete item") from e

    async def get_item(
        self,
        user_id: str,
        itinerary_id: str,
        item_id: str,
    ) -> ItineraryItem:
        """Get an item from an itinerary by ID.

        Args:
            user_id: User ID
            itinerary_id: Itinerary ID
            item_id: Item ID

        Returns:
            Itinerary item

        Raises:
            ResourceNotFoundError: If itinerary or item not found
            ServiceError: If retrieval fails
        """
        try:
            logger.info(
                f"Getting item {item_id} from itinerary {itinerary_id} "
                f"for user {user_id}",
            )

            # Get item via core service
            core_service = await self._get_core_itinerary_service()
            core_response = await core_service.get_item(user_id, itinerary_id, item_id)

            # Adapt core response to API model
            return self._adapt_itinerary_item(core_response)

        except ResourceNotFoundError as e:
            logger.error(f"Item not found: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Failed to get item: {e!s}")
            raise ServiceError("Failed to get item") from e

    async def check_conflicts(
        self,
        user_id: str,
        itinerary_id: str,
    ) -> ItineraryConflictCheckResponse:
        """Check for conflicts in an itinerary schedule.

        Args:
            user_id: User ID
            itinerary_id: Itinerary ID

        Returns:
            Conflict check response

        Raises:
            ResourceNotFoundError: If itinerary not found
            ServiceError: If check fails
        """
        try:
            logger.info(
                f"Checking conflicts in itinerary {itinerary_id} for user {user_id}",
            )

            # Check conflicts via core service
            core_service = await self._get_core_itinerary_service()
            core_response = await core_service.check_conflicts(user_id, itinerary_id)

            # Adapt core response to API model
            return self._adapt_conflict_check_response(core_response)

        except ResourceNotFoundError as e:
            logger.error(f"Itinerary not found: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Failed to check conflicts: {e!s}")
            raise ServiceError("Failed to check conflicts") from e

    async def optimize_itinerary(
        self,
        user_id: str,
        request: ItineraryOptimizeRequest,
    ) -> ItineraryOptimizeResponse:
        """Optimize an itinerary based on provided settings.

        Args:
            user_id: User ID
            request: Optimization request

        Returns:
            Optimization response

        Raises:
            ResourceNotFoundError: If itinerary not found
            ValidationError: If request data is invalid
            ServiceError: If optimization fails
        """
        try:
            logger.info(
                f"Optimizing itinerary {request.itinerary_id} for user {user_id}",
            )

            # Adapt API request to core model
            core_request = self._adapt_itinerary_optimize_request(request)

            # Optimize via core service
            core_service = await self._get_core_itinerary_service()
            core_response = await core_service.optimize_itinerary(user_id, core_request)

            # Adapt core response to API model
            return self._adapt_optimize_response(core_response)

        except (ResourceNotFoundError, ValidationError, ServiceError) as e:
            logger.error(f"Itinerary optimization failed: {e!s}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error optimizing itinerary: {e!s}")
            raise ServiceError("Failed to optimize itinerary") from e

    def _adapt_itinerary_create_request(self, request: ItineraryCreateRequest) -> dict:
        """Adapt API itinerary create request to core model."""
        return {
            "title": request.title,
            "description": request.description,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "destinations": request.destinations,
            "total_budget": request.total_budget,
            "currency": request.currency,
            "tags": request.tags,
        }

    def _adapt_itinerary_update_request(self, request: ItineraryUpdateRequest) -> dict:
        """Adapt API itinerary update request to core model."""
        return {
            "title": request.title,
            "description": request.description,
            "status": request.status,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "destinations": request.destinations,
            "total_budget": request.total_budget,
            "currency": request.currency,
            "tags": request.tags,
            "share_settings": request.share_settings,
        }

    def _adapt_itinerary_search_request(self, request: ItinerarySearchRequest) -> dict:
        """Adapt API itinerary search request to core model."""
        return {
            "query": request.query,
            "start_date_from": request.start_date_from,
            "start_date_to": request.start_date_to,
            "end_date_from": request.end_date_from,
            "end_date_to": request.end_date_to,
            "destinations": request.destinations,
            "status": request.status,
            "tags": request.tags,
            "page": request.page,
            "page_size": request.page_size,
        }

    def _adapt_itinerary_item_create_request(
        self,
        request: ItineraryItemCreateRequest,
    ) -> dict:
        """Adapt API itinerary item create request to core model."""
        return {
            "type": request.item_type,
            "title": request.title,
            "description": request.description,
            "date": request.item_date,
            "time_slot": request.time_slot,
            "location": request.location,
            "cost": request.cost,
            "currency": request.currency,
            "booking_reference": request.booking_reference,
            "notes": request.notes,
            "is_flexible": request.is_flexible,
            "flight_details": request.flight_details,
            "accommodation_details": request.accommodation_details,
            "activity_details": request.activity_details,
            "transportation_details": request.transportation_details,
        }

    def _adapt_itinerary_item_update_request(
        self,
        request: ItineraryItemUpdateRequest,
    ) -> dict:
        """Adapt API itinerary item update request to core model."""
        return {
            "title": request.title,
            "description": request.description,
            "date": request.date,
            "time_slot": request.time_slot,
            "location": request.location,
            "cost": request.cost,
            "currency": request.currency,
            "booking_reference": request.booking_reference,
            "notes": request.notes,
            "is_flexible": request.is_flexible,
            "flight_details": request.flight_details,
            "accommodation_details": request.accommodation_details,
            "activity_details": request.activity_details,
            "transportation_details": request.transportation_details,
        }

    def _adapt_itinerary_optimize_request(
        self,
        request: ItineraryOptimizeRequest,
    ) -> dict:
        """Adapt API itinerary optimize request to core model."""
        return {
            "itinerary_id": request.itinerary_id,
            "settings": request.settings,
        }

    def _adapt_itinerary(self, core_itinerary) -> Itinerary:
        """Adapt core itinerary to API model."""
        # This is a simplified adaptation - real implementation needs detailed mapping
        # ItineraryStatus already imported at module level

        return Itinerary(
            id=core_itinerary.get("id", ""),
            user_id=core_itinerary.get("user_id", ""),
            title=core_itinerary.get("title", ""),
            description=core_itinerary.get("description", ""),
            status=ItineraryStatus(core_itinerary.get("status", "draft")),
            start_date=core_itinerary.get("start_date"),
            end_date=core_itinerary.get("end_date"),
            days=[
                self._adapt_itinerary_day(day) for day in core_itinerary.get("days", [])
            ],
            destinations=core_itinerary.get("destinations", []),
            total_budget=core_itinerary.get("total_budget"),
            budget_spent=core_itinerary.get("budget_spent"),
            currency=core_itinerary.get("currency", "USD"),
            tags=core_itinerary.get("tags", []),
            created_at=core_itinerary.get("created_at", ""),
            updated_at=core_itinerary.get("updated_at", ""),
            share_settings=core_itinerary.get("share_settings"),
        )

    def _adapt_itinerary_day(self, core_day):
        """Adapt core itinerary day to API model."""
        # ItineraryDay already imported at module level

        return ItineraryDay(
            day_date=core_day.get("date"),
            items=[
                self._adapt_itinerary_item(item) for item in core_day.get("items", [])
            ],
        )

    def _adapt_itinerary_item(self, core_item) -> ItineraryItem:
        """Adapt core itinerary item to API model."""
        # This is a simplified adaptation - real implementation needs detailed mapping
        return ItineraryItem(
            id=core_item.get("id", ""),
            item_type=core_item.get("type", ""),
            title=core_item.get("title", ""),
            description=core_item.get("description", ""),
            item_date=core_item.get("date"),
            time_slot=core_item.get("time_slot"),
            location=core_item.get("location", ""),
            cost=core_item.get("cost"),
            currency=core_item.get("currency", "USD"),
            booking_reference=core_item.get("booking_reference", ""),
            notes=core_item.get("notes", ""),
            is_flexible=core_item.get("is_flexible", False),
        )

    def _adapt_itinerary_search_response(
        self,
        core_response,
    ) -> ItinerarySearchResponse:
        """Adapt core itinerary search response to API model."""
        return ItinerarySearchResponse(
            results=[
                self._adapt_itinerary(itinerary)
                for itinerary in core_response.get("results", [])
            ],
            total=core_response.get("total", 0),
            page=core_response.get("page", 1),
            page_size=core_response.get("page_size", 10),
            pages=core_response.get("pages", 0),
        )

    def _adapt_conflict_check_response(
        self,
        core_response,
    ) -> ItineraryConflictCheckResponse:
        """Adapt core conflict check response to API model."""
        return ItineraryConflictCheckResponse(
            has_conflicts=core_response.get("has_conflicts", False),
            conflicts=core_response.get("conflicts", []),
        )

    def _adapt_optimize_response(self, core_response) -> ItineraryOptimizeResponse:
        """Adapt core optimize response to API model."""
        return ItineraryOptimizeResponse(
            original_itinerary=self._adapt_itinerary(
                core_response.get("original_itinerary"),
            ),
            optimized_itinerary=self._adapt_itinerary(
                core_response.get("optimized_itinerary"),
            ),
            changes=core_response.get("changes", []),
            optimization_score=core_response.get("optimization_score", 0.0),
        )


# Module-level dependency annotation
_core_itinerary_service_dep = Depends(get_core_itinerary_service)


# Dependency function for FastAPI
async def get_itinerary_service(
    core_itinerary_service: CoreItineraryService = _core_itinerary_service_dep,
) -> ItineraryService:
    """
    Get itinerary service instance for dependency injection.

    Args:
        core_itinerary_service: Core itinerary service

    Returns:
        ItineraryService instance
    """
    return ItineraryService(core_itinerary_service=core_itinerary_service)
