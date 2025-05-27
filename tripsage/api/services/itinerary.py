"""
Service for itinerary-related operations in the TripSage API.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List

from tripsage.api.core.exceptions import ResourceNotFoundError
from tripsage.api.models.itineraries import (
    Itinerary,
    ItineraryConflictCheckResponse,
    ItineraryCreateRequest,
    ItineraryDay,
    ItineraryItem,
    ItineraryItemCreateRequest,
    ItineraryItemType,
    ItineraryItemUpdateRequest,
    ItineraryOptimizeRequest,
    ItineraryOptimizeResponse,
    ItinerarySearchRequest,
    ItinerarySearchResponse,
    ItineraryStatus,
    ItineraryUpdateRequest,
    TimeSlot,
)

logger = logging.getLogger(__name__)


class ItineraryService:
    """Service for itinerary-related operations."""

    _instance = None

    def __new__(cls):
        """Create a singleton instance of the service."""
        if cls._instance is None:
            cls._instance = super(ItineraryService, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        """Initialize the service."""
        # In-memory storage for itineraries (would be a database in production)
        self._itineraries = {}
        # In-memory storage for itinerary items
        self._items = {}
        logger.info("ItineraryService initialized")

    async def create_itinerary(
        self, user_id: str, request: ItineraryCreateRequest
    ) -> Itinerary:
        """Create a new itinerary for a user."""
        logger.info(f"Creating new itinerary for user {user_id}: {request.title}")

        # Generate a unique ID for the itinerary
        itinerary_id = str(uuid.uuid4())

        # Create empty days for the entire date range
        days = []
        current_date = request.start_date
        while current_date <= request.end_date:
            days.append(
                ItineraryDay(
                    date=current_date,
                    items=[],
                )
            )
            current_date += timedelta(days=1)

        now = datetime.now(datetime.UTC).isoformat()

        # Create the itinerary object
        itinerary = Itinerary(
            id=itinerary_id,
            user_id=user_id,
            title=request.title,
            description=request.description,
            status=ItineraryStatus.DRAFT,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            destinations=request.destinations,
            total_budget=request.total_budget,
            currency=request.currency,
            tags=request.tags,
            created_at=now,
            updated_at=now,
        )

        # Store the itinerary
        if user_id not in self._itineraries:
            self._itineraries[user_id] = {}
        self._itineraries[user_id][itinerary_id] = itinerary

        return itinerary

    async def get_itinerary(self, user_id: str, itinerary_id: str) -> Itinerary:
        """Get an itinerary by ID."""
        logger.info(f"Getting itinerary {itinerary_id} for user {user_id}")

        if (
            user_id not in self._itineraries
            or itinerary_id not in self._itineraries[user_id]
        ):
            msg = f"Itinerary {itinerary_id} not found for user {user_id}"
            logger.warning(msg)
            raise ResourceNotFoundError(msg)

        return self._itineraries[user_id][itinerary_id]

    async def update_itinerary(
        self, user_id: str, itinerary_id: str, request: ItineraryUpdateRequest
    ) -> Itinerary:
        """Update an existing itinerary."""
        logger.info(f"Updating itinerary {itinerary_id} for user {user_id}")

        # Get the existing itinerary
        itinerary = await self.get_itinerary(user_id, itinerary_id)

        # Update fields if provided in the request
        if request.title is not None:
            itinerary.title = request.title
        if request.description is not None:
            itinerary.description = request.description
        if request.status is not None:
            itinerary.status = request.status
        if request.start_date is not None:
            itinerary.start_date = request.start_date
        if request.end_date is not None:
            itinerary.end_date = request.end_date
        if request.destinations is not None:
            itinerary.destinations = request.destinations
        if request.total_budget is not None:
            itinerary.total_budget = request.total_budget
        if request.currency is not None:
            itinerary.currency = request.currency
        if request.tags is not None:
            itinerary.tags = request.tags
        if request.share_settings is not None:
            itinerary.share_settings = request.share_settings

        # Update the 'updated_at' timestamp
        itinerary.updated_at = datetime.now(datetime.UTC).isoformat()

        # If dates have changed, we need to update the days array
        if request.start_date is not None or request.end_date is not None:
            # Create a dict of existing days by date for easy lookup
            existing_days = {day.date.isoformat(): day for day in itinerary.days}

            # Create new days array
            days = []
            current_date = itinerary.start_date
            while current_date <= itinerary.end_date:
                date_str = current_date.isoformat()
                if date_str in existing_days:
                    # Use existing day
                    days.append(existing_days[date_str])
                else:
                    # Create new empty day
                    days.append(ItineraryDay(date=current_date, items=[]))
                current_date += timedelta(days=1)

            # Update the days array
            itinerary.days = days

        # Store the updated itinerary
        self._itineraries[user_id][itinerary_id] = itinerary

        return itinerary

    async def delete_itinerary(self, user_id: str, itinerary_id: str) -> None:
        """Delete an itinerary."""
        logger.info(f"Deleting itinerary {itinerary_id} for user {user_id}")

        # Check if the itinerary exists
        await self.get_itinerary(user_id, itinerary_id)

        # Delete the itinerary
        del self._itineraries[user_id][itinerary_id]

    async def list_itineraries(self, user_id: str) -> List[Itinerary]:
        """List all itineraries for a user."""
        logger.info(f"Listing itineraries for user {user_id}")

        if user_id not in self._itineraries:
            return []

        return list(self._itineraries[user_id].values())

    async def search_itineraries(
        self, user_id: str, request: ItinerarySearchRequest
    ) -> ItinerarySearchResponse:
        """Search for itineraries based on criteria."""
        log_msg = f"Searching itineraries for user {user_id} with criteria"
        logger.info(log_msg)

        if user_id not in self._itineraries:
            return ItinerarySearchResponse(
                results=[],
                total=0,
                page=request.page,
                page_size=request.page_size,
                pages=0,
            )

        # Get all itineraries for the user
        all_itineraries = list(self._itineraries[user_id].values())

        # Apply filters
        filtered_itineraries = []
        for itinerary in all_itineraries:
            # Filter by query (title or description)
            if request.query:
                query_lower = request.query.lower()
                title_match = itinerary.title and query_lower in itinerary.title.lower()
                desc_match = (
                    itinerary.description
                    and query_lower in itinerary.description.lower()
                )
                if not (title_match or desc_match):
                    continue

            # Filter by dates
            if (
                request.start_date_from
                and itinerary.start_date < request.start_date_from
            ):
                continue
            if request.start_date_to and itinerary.start_date > request.start_date_to:
                continue
            if request.end_date_from and itinerary.end_date < request.end_date_from:
                continue
            if request.end_date_to and itinerary.end_date > request.end_date_to:
                continue

            # Filter by destinations
            if request.destinations:
                if not any(
                    dest in itinerary.destinations for dest in request.destinations
                ):
                    continue

            # Filter by status
            if request.status and itinerary.status != request.status:
                continue

            # Filter by tags
            if request.tags:
                if not any(tag in itinerary.tags for tag in request.tags):
                    continue

            # All filters passed, add to results
            filtered_itineraries.append(itinerary)

        # Sort results by updated_at (most recent first)
        sorted_itineraries = sorted(
            filtered_itineraries, key=lambda x: x.updated_at, reverse=True
        )

        # Apply pagination
        total = len(sorted_itineraries)
        pages = (total + request.page_size - 1) // request.page_size
        start_idx = (request.page - 1) * request.page_size
        end_idx = start_idx + request.page_size
        paginated_results = sorted_itineraries[start_idx:end_idx]

        return ItinerarySearchResponse(
            results=paginated_results,
            total=total,
            page=request.page,
            page_size=request.page_size,
            pages=pages,
        )

    async def add_item_to_itinerary(
        self,
        user_id: str,
        itinerary_id: str,
        request: ItineraryItemCreateRequest,
    ) -> ItineraryItem:
        """Add an item to an itinerary."""
        logger.info(
            f"Adding {request.type} item to itinerary {itinerary_id} for user {user_id}"
        )

        # Get the itinerary
        itinerary = await self.get_itinerary(user_id, itinerary_id)

        # Check if the date is within the itinerary date range
        if request.date < itinerary.start_date or request.date > itinerary.end_date:
            msg = (
                f"Item date {request.date} is outside the itinerary date range "
                f"({itinerary.start_date} to {itinerary.end_date})"
            )
            logger.warning(msg)
            raise ValueError(msg)

        # Generate a unique ID for the item
        item_id = str(uuid.uuid4())

        # Create the base item with common properties
        item_dict = {
            "id": item_id,
            "type": request.type,
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
        }

        # Add type-specific details if provided
        if request.type == ItineraryItemType.FLIGHT and request.flight_details:
            item_dict.update(request.flight_details)
        elif (
            request.type == ItineraryItemType.ACCOMMODATION
            and request.accommodation_details
        ):
            item_dict.update(request.accommodation_details)
        elif request.type == ItineraryItemType.ACTIVITY and request.activity_details:
            item_dict.update(request.activity_details)
        elif (
            request.type == ItineraryItemType.TRANSPORTATION
            and request.transportation_details
        ):
            item_dict.update(request.transportation_details)

        # Create the appropriate item type
        if request.type == ItineraryItemType.FLIGHT:
            # For production, we would create specific item types
            # For now, we'll just use a generic ItineraryItem
            item = ItineraryItem(**item_dict)
        else:
            item = ItineraryItem(**item_dict)

        # Find the correct day to add the item to
        for day in itinerary.days:
            if day.date == request.date:
                day.items.append(item)
                break
        else:
            # This should not happen if we validated the date range correctly
            msg = f"No matching day found for date {request.date}"
            logger.error(msg)
            raise ValueError(msg)

        # Update the itinerary's updated_at timestamp
        itinerary.updated_at = datetime.now(datetime.UTC).isoformat()

        # Store the updated itinerary
        self._itineraries[user_id][itinerary_id] = itinerary

        # Store the item separately for direct access
        if itinerary_id not in self._items:
            self._items[itinerary_id] = {}
        self._items[itinerary_id][item_id] = item

        # If the item has a cost, update the budget_spent in the itinerary
        if request.cost:
            if itinerary.budget_spent is None:
                itinerary.budget_spent = 0
            itinerary.budget_spent += request.cost

        return item

    async def update_item(
        self,
        user_id: str,
        itinerary_id: str,
        item_id: str,
        request: ItineraryItemUpdateRequest,
    ) -> ItineraryItem:
        """Update an item in an itinerary."""
        logger.info(
            f"Updating item {item_id} in itinerary {itinerary_id} for user {user_id}"
        )

        # Get the itinerary
        itinerary = await self.get_itinerary(user_id, itinerary_id)

        # Find the item in the itinerary
        found_item = None
        found_day = None

        for day in itinerary.days:
            for _i, item in enumerate(day.items):
                if item.id == item_id:
                    found_item = item
                    found_day = day
                    break
            if found_item:
                break

        if not found_item:
            msg = f"Item {item_id} not found in itinerary {itinerary_id}"
            logger.warning(msg)
            raise ResourceNotFoundError(msg)

        # Check if we're changing the date
        if request.date and request.date != found_item.date:
            # Check if the new date is within the itinerary date range
            if request.date < itinerary.start_date or request.date > itinerary.end_date:
                msg = (
                    f"New item date {request.date} is outside the itinerary date range "
                    f"({itinerary.start_date} to {itinerary.end_date})"
                )
                logger.warning(msg)
                raise ValueError(msg)

            # Remove the item from the current day
            found_day.items = [item for item in found_day.items if item.id != item_id]

            # Find the new day to add the item to
            new_day = None
            for day in itinerary.days:
                if day.date == request.date:
                    new_day = day
                    break

            if not new_day:
                # This should not happen if we validated the date range correctly
                msg = f"No matching day found for date {request.date}"
                logger.error(msg)
                raise ValueError(msg)

            # Update the item date
            found_item.date = request.date

            # Add the item to the new day
            new_day.items.append(found_item)

        # Update other fields if provided
        if request.title is not None:
            found_item.title = request.title
        if request.description is not None:
            found_item.description = request.description
        if request.time_slot is not None:
            found_item.time_slot = request.time_slot
        if request.location is not None:
            found_item.location = request.location

        # Handle cost updates
        if request.cost is not None and request.cost != found_item.cost:
            # If the item already had a cost, subtract it from the budget_spent
            if found_item.cost is not None and itinerary.budget_spent is not None:
                itinerary.budget_spent -= found_item.cost

            # Add the new cost to the budget_spent
            if itinerary.budget_spent is None:
                itinerary.budget_spent = 0
            itinerary.budget_spent += request.cost

            # Update the item cost
            found_item.cost = request.cost

        if request.currency is not None:
            found_item.currency = request.currency
        if request.booking_reference is not None:
            found_item.booking_reference = request.booking_reference
        if request.notes is not None:
            found_item.notes = request.notes
        if request.is_flexible is not None:
            found_item.is_flexible = request.is_flexible

        # Update type-specific details if provided
        item_type = found_item.type
        if item_type == ItineraryItemType.FLIGHT and request.flight_details:
            for key, value in request.flight_details.items():
                setattr(found_item, key, value)
        elif (
            item_type == ItineraryItemType.ACCOMMODATION
            and request.accommodation_details
        ):
            for key, value in request.accommodation_details.items():
                setattr(found_item, key, value)
        elif item_type == ItineraryItemType.ACTIVITY and request.activity_details:
            for key, value in request.activity_details.items():
                setattr(found_item, key, value)
        elif (
            item_type == ItineraryItemType.TRANSPORTATION
            and request.transportation_details
        ):
            for key, value in request.transportation_details.items():
                setattr(found_item, key, value)

        # Update the itinerary's updated_at timestamp
        itinerary.updated_at = datetime.now(datetime.UTC).isoformat()

        # Store the updated itinerary
        self._itineraries[user_id][itinerary_id] = itinerary

        # Update the item in separate storage
        if itinerary_id in self._items and item_id in self._items[itinerary_id]:
            self._items[itinerary_id][item_id] = found_item

        return found_item

    async def delete_item(self, user_id: str, itinerary_id: str, item_id: str) -> None:
        """Delete an item from an itinerary."""
        logger.info(
            f"Deleting item {item_id} from itinerary {itinerary_id} for user {user_id}"
        )

        # Get the itinerary
        itinerary = await self.get_itinerary(user_id, itinerary_id)

        # Find the item in the itinerary
        found_item = None
        found_day = None

        for day in itinerary.days:
            for item in day.items:
                if item.id == item_id:
                    found_item = item
                    found_day = day
                    break
            if found_item:
                break

        if not found_item:
            msg = f"Item {item_id} not found in itinerary {itinerary_id}"
            logger.warning(msg)
            raise ResourceNotFoundError(msg)

        # If the item has a cost, update the budget_spent in the itinerary
        if found_item.cost is not None and itinerary.budget_spent is not None:
            itinerary.budget_spent -= found_item.cost

        # Remove the item from the day
        found_day.items = [item for item in found_day.items if item.id != item_id]

        # Update the itinerary's updated_at timestamp
        itinerary.updated_at = datetime.now(datetime.UTC).isoformat()

        # Store the updated itinerary
        self._itineraries[user_id][itinerary_id] = itinerary

        # Remove the item from separate storage
        if itinerary_id in self._items and item_id in self._items[itinerary_id]:
            del self._items[itinerary_id][item_id]

    async def get_item(
        self, user_id: str, itinerary_id: str, item_id: str
    ) -> ItineraryItem:
        """Get an item from an itinerary by ID."""
        logger.info(
            f"Getting item {item_id} from itinerary {itinerary_id} for user {user_id}"
        )

        # First check if we have direct access to the item
        if itinerary_id in self._items and item_id in self._items[itinerary_id]:
            return self._items[itinerary_id][item_id]

        # Otherwise, search through the itinerary
        itinerary = await self.get_itinerary(user_id, itinerary_id)

        for day in itinerary.days:
            for item in day.items:
                if item.id == item_id:
                    return item

        # If we get here, the item wasn't found
        msg = f"Item {item_id} not found in itinerary {itinerary_id}"
        logger.warning(msg)
        raise ResourceNotFoundError(msg)

    async def check_conflicts(
        self, user_id: str, itinerary_id: str
    ) -> ItineraryConflictCheckResponse:
        """Check for conflicts in an itinerary schedule."""
        log_msg = f"Checking conflicts in itinerary {itinerary_id} for user {user_id}"
        logger.info(log_msg)

        # Get the itinerary
        itinerary = await self.get_itinerary(user_id, itinerary_id)

        conflicts = []

        # Check for conflicts in each day
        for day in itinerary.days:
            # Only check items with time slots
            items_with_time = [item for item in day.items if item.time_slot]

            # Sort the items by start time
            items_with_time.sort(
                key=lambda x: x.time_slot.start_time  # type: ignore
            )

            # Check for overlapping time slots
            for i in range(len(items_with_time) - 1):
                current_item = items_with_time[i]
                next_item = items_with_time[i + 1]

                current_end = current_item.time_slot.end_time  # type: ignore
                next_start = next_item.time_slot.start_time  # type: ignore

                # Convert to minutes for comparison
                current_end_hour, current_end_minute = map(
                    int,
                    current_end.split(":"),  # type: ignore
                )
                next_start_hour, next_start_minute = map(
                    int,
                    next_start.split(":"),  # type: ignore
                )

                current_end_minutes = current_end_hour * 60 + current_end_minute
                next_start_minutes = next_start_hour * 60 + next_start_minute

                # Handle overnight slots (e.g., end time is after midnight)
                if current_end_minutes > 24 * 60:
                    current_end_minutes -= 24 * 60

                if next_start_minutes < current_end_minutes:
                    # We have a conflict
                    conflicts.append(
                        {
                            "day": day.date.isoformat(),
                            "first_item_id": current_item.id,
                            "first_item_title": current_item.title,
                            "first_item_end": current_end,
                            "second_item_id": next_item.id,
                            "second_item_title": next_item.title,
                            "second_item_start": next_start,
                            "overlap_minutes": current_end_minutes - next_start_minutes,
                        }
                    )

        # Check for multi-day accommodation overlaps
        accommodations = []
        for day in itinerary.days:
            for item in day.items:
                if item.type == ItineraryItemType.ACCOMMODATION:
                    accommodations.append(item)

        # Sort accommodations by date
        accommodations.sort(key=lambda x: x.date)

        # Check for overlapping accommodations
        for i in range(len(accommodations) - 1):
            current_item = accommodations[i]
            next_item = accommodations[i + 1]

            # If type-specific attributes are available
            current_checkout = getattr(current_item, "check_out_date", None)
            next_checkin = getattr(next_item, "check_in_date", None)

            if current_checkout and next_checkin and current_checkout > next_checkin:
                conflicts.append(
                    {
                        "type": "accommodation_overlap",
                        "first_item_id": current_item.id,
                        "first_item_title": current_item.title,
                        "first_item_checkout": current_checkout.isoformat(),
                        "second_item_id": next_item.id,
                        "second_item_title": next_item.title,
                        "second_item_checkin": next_checkin.isoformat(),
                        "overlap_days": (current_checkout - next_checkin).days,
                    }
                )

        # Return the conflicts found
        return ItineraryConflictCheckResponse(
            has_conflicts=len(conflicts) > 0,
            conflicts=conflicts,
        )

    async def optimize_itinerary(
        self, user_id: str, request: ItineraryOptimizeRequest
    ) -> ItineraryOptimizeResponse:
        """
        Optimize an itinerary based on provided settings.

        This is a placeholder implementation that would typically involve
        complex optimization algorithms. For now, it just returns a simple
        rearrangement of the itinerary.
        """
        logger.info(f"Optimizing itinerary {request.itinerary_id} for user {user_id}")

        # Get the itinerary
        itinerary = await self.get_itinerary(user_id, request.itinerary_id)

        # Create a copy of the original itinerary for the response
        original_itinerary = itinerary

        # Create a deep copy of the itinerary for optimization
        optimized_itinerary = Itinerary.model_validate(itinerary.model_dump())

        # Track changes made during optimization
        changes = []

        # Simple optimization logic (placeholder)
        for day in optimized_itinerary.days:
            # Only optimize items with time slots
            items_with_time = [item for item in day.items if item.time_slot]
            items_without_time = [item for item in day.items if not item.time_slot]

            if items_with_time:
                # Sort items by start time
                items_with_time.sort(
                    key=lambda x: x.time_slot.start_time  # type: ignore
                )

                # Distribute items evenly throughout the day
                if request.settings.start_day_time and request.settings.end_day_time:
                    # Convert time strings to minutes
                    start_hour, start_minute = map(
                        int, request.settings.start_day_time.split(":")
                    )
                    end_hour, end_minute = map(
                        int, request.settings.end_day_time.split(":")
                    )

                    start_minutes = start_hour * 60 + start_minute
                    end_minutes = end_hour * 60 + end_minute

                    # Handle overnight (end time is after midnight)
                    if end_minutes < start_minutes:
                        end_minutes += 24 * 60

                    available_minutes = end_minutes - start_minutes

                    # Calculate total item duration
                    total_item_duration = sum(
                        item.time_slot.duration_minutes
                        for item in items_with_time  # type: ignore
                    )

                    # Calculate break duration if specified
                    break_duration = request.settings.break_duration_minutes or 30
                    total_break_duration = break_duration * (len(items_with_time) - 1)

                    # Check if everything fits
                    total_planned_time = total_item_duration + total_break_duration
                    if total_planned_time <= available_minutes:
                        # Distribute items
                        current_minutes = start_minutes

                        for i, item in enumerate(items_with_time):
                            # Set new start time
                            current_hour = current_minutes // 60
                            current_minute = current_minutes % 60

                            new_start_time = f"{current_hour:02d}:{current_minute:02d}"

                            # Calculate new end time
                            duration = item.time_slot.duration_minutes  # type: ignore
                            end_minutes = current_minutes + duration
                            end_hour = end_minutes // 60
                            end_minute = end_minutes % 60

                            new_end_time = f"{end_hour:02d}:{end_minute:02d}"

                            # Record the change
                            changes.append(
                                {
                                    "item_id": item.id,
                                    "type": "time_adjustment",
                                    "old_start": item.time_slot.start_time,  # type: ignore
                                    "old_end": item.time_slot.end_time,  # type: ignore
                                    "new_start": new_start_time,
                                    "new_end": new_end_time,
                                }
                            )

                            # Update the item's time slot
                            item.time_slot = TimeSlot(  # type: ignore
                                start_time=new_start_time,
                                end_time=new_end_time,
                                duration_minutes=duration,
                            )

                            # Move to the next item's start time (add break)
                            if i < len(items_with_time) - 1:
                                current_minutes = end_minutes + break_duration

            # Update the day's items
            day.items = items_with_time + items_without_time

        # Update the itinerary's updated_at timestamp
        optimized_itinerary.updated_at = datetime.now(datetime.UTC).isoformat()

        # Calculate an optimization score (placeholder)
        optimization_score = 0.75  # In a real implementation, this would be calculated

        # Return the optimized itinerary and details
        return ItineraryOptimizeResponse(
            original_itinerary=original_itinerary,
            optimized_itinerary=optimized_itinerary,
            changes=changes,
            optimization_score=optimization_score,
        )


def get_itinerary_service() -> ItineraryService:
    """Get the singleton instance of the itinerary service."""
    return ItineraryService()
