"""
Google Calendar MCP Client implementation for TripSage.

This module provides a client for interacting with the Model Context Protocol's
Google Calendar MCP Server, which offers Google Calendar integration capabilities.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from agents import function_tool

from ...cache.redis_cache import redis_cache
from ...utils.config import get_config
from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from ..fastmcp import FastMCPClient
from .models import (
    CalendarListResponse,
    CreateEventParams,
    CreateItineraryEventsParams,
    CreateItineraryEventsResponse,
    DeleteEventParams,
    Event,
    EventListResponse,
    EventSearchResponse,
    ListCalendarsParams,
    ListEventsParams,
    SearchEventsParams,
    UpdateEventParams,
)

logger = get_module_logger(__name__)
config = get_config()


class CalendarMCPClient(FastMCPClient):
    """Client for the Google Calendar MCP Server."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        use_cache: bool = True,
        cache_ttl: int = 300,  # 5 minute default cache TTL for calendar data
    ):
        """Initialize the Google Calendar MCP Client.

        Args:
            endpoint: MCP server endpoint URL (defaults to config value)
            api_key: API key for authentication (defaults to config value)
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
            cache_ttl: Cache TTL in seconds
        """
        if endpoint is None:
            endpoint = (
                config.calendar_mcp.endpoint
                if hasattr(config, "calendar_mcp")
                else "http://localhost:3003"
            )

        api_key = api_key or (
            config.calendar_mcp.api_key.get_secret_value()
            if hasattr(config.calendar_mcp, "api_key") and config.calendar_mcp.api_key
            else None
        )

        super().__init__(
            server_name="Google Calendar",
            endpoint=endpoint,
            api_key=api_key,
            timeout=timeout,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
        )

    @function_tool
    @redis_cache.cached("calendar_list", 600)  # Cache for 10 minutes
    async def get_calendars(
        self, max_results: Optional[int] = None, skip_cache: bool = False
    ) -> CalendarListResponse:
        """Get a list of available calendars.

        Args:
            max_results: Maximum number of calendars to return
            skip_cache: Whether to skip the cache

        Returns:
            Response containing list of calendars

        Raises:
            MCPError: If the request fails
        """
        try:
            # Validate parameters
            params = ListCalendarsParams(max_results=max_results)

            # Call the MCP tool
            response = await self.call_tool(
                "list-calendars",
                params.model_dump(exclude_none=True),
                skip_cache=skip_cache,
            )

            # Parse the response
            if isinstance(response, str):
                response = json.loads(response)

            # Validate with Pydantic model
            return CalendarListResponse.model_validate(response)
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for list-calendars: {str(e)}",
                server=self.server_name,
                tool="list-calendars",
                params={"max_results": max_results},
            ) from e
        except Exception as e:
            logger.error(f"Error getting calendars: {str(e)}")
            raise MCPError(
                message=f"Failed to get calendars: {str(e)}",
                server=self.server_name,
                tool="list-calendars",
                params={"max_results": max_results},
            ) from e

    @function_tool
    @redis_cache.cached("calendar_events", 300)  # Cache for 5 minutes
    async def get_events(
        self,
        calendar_id: str,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: Optional[int] = None,
        single_events: bool = True,
        order_by: str = "startTime",
        skip_cache: bool = False,
    ) -> EventListResponse:
        """Get events from a calendar within a specified time range.

        Args:
            calendar_id: ID of the calendar to get events from
            time_min: Start time in ISO 8601 format (defaults to now)
            time_max: End time in ISO 8601 format (defaults to 1 week from now)
            max_results: Maximum number of events to return
            single_events: Whether to expand recurring events
            order_by: Order of events (startTime, updated)
            skip_cache: Whether to skip the cache

        Returns:
            Response containing list of events

        Raises:
            MCPError: If the request fails
        """
        try:
            # Set default time range if not provided
            if not time_min:
                time_min = datetime.utcnow().isoformat() + "Z"
            if not time_max:
                time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"

            # Validate parameters
            params = ListEventsParams(
                calendar_id=calendar_id,
                time_min=time_min,
                time_max=time_max,
                max_results=max_results,
                single_events=single_events,
                order_by=order_by,
            )

            # Call the MCP tool
            response = await self.call_tool(
                "list-events",
                params.model_dump(exclude_none=True),
                skip_cache=skip_cache,
            )

            # Parse the response
            if isinstance(response, str):
                response = json.loads(response)

            # Validate with Pydantic model
            return EventListResponse.model_validate(response)
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for list-events: {str(e)}",
                server=self.server_name,
                tool="list-events",
                params={
                    "calendar_id": calendar_id,
                    "time_min": time_min,
                    "time_max": time_max,
                    "max_results": max_results,
                    "single_events": single_events,
                    "order_by": order_by,
                },
            ) from e
        except Exception as e:
            logger.error(f"Error getting events: {str(e)}")
            raise MCPError(
                message=f"Failed to get events: {str(e)}",
                server=self.server_name,
                tool="list-events",
                params={
                    "calendar_id": calendar_id,
                    "time_min": time_min,
                    "time_max": time_max,
                    "max_results": max_results,
                    "single_events": single_events,
                    "order_by": order_by,
                },
            ) from e

    @function_tool
    @redis_cache.cached("calendar_search", 300)  # Cache for 5 minutes
    async def search_events(
        self,
        calendar_id: str,
        query: str,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: Optional[int] = None,
        skip_cache: bool = False,
    ) -> EventSearchResponse:
        """Search for events in a calendar that match a query.

        Args:
            calendar_id: ID of the calendar to search
            query: Search query string
            time_min: Start time in ISO 8601 format (defaults to now)
            time_max: End time in ISO 8601 format (defaults to 1 month from now)
            max_results: Maximum number of events to return
            skip_cache: Whether to skip the cache

        Returns:
            Response containing matching events

        Raises:
            MCPError: If the request fails
        """
        try:
            # Set default time range if not provided
            if not time_min:
                time_min = datetime.utcnow().isoformat() + "Z"
            if not time_max:
                time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"

            # Validate parameters
            params = SearchEventsParams(
                calendar_id=calendar_id,
                query=query,
                time_min=time_min,
                time_max=time_max,
                max_results=max_results,
            )

            # Call the MCP tool
            response = await self.call_tool(
                "search-events",
                params.model_dump(exclude_none=True),
                skip_cache=skip_cache,
            )

            # Parse the response
            if isinstance(response, str):
                response = json.loads(response)

            # Validate with Pydantic model
            return EventSearchResponse.model_validate(response)
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for search-events: {str(e)}",
                server=self.server_name,
                tool="search-events",
                params={
                    "calendar_id": calendar_id,
                    "query": query,
                    "time_min": time_min,
                    "time_max": time_max,
                    "max_results": max_results,
                },
            ) from e
        except Exception as e:
            logger.error(f"Error searching events: {str(e)}")
            raise MCPError(
                message=f"Failed to search events: {str(e)}",
                server=self.server_name,
                tool="search-events",
                params={
                    "calendar_id": calendar_id,
                    "query": query,
                    "time_min": time_min,
                    "time_max": time_max,
                    "max_results": max_results,
                },
            ) from e

    @function_tool
    async def create_event(
        self,
        calendar_id: str,
        summary: str,
        start: Dict[str, Any],
        end: Dict[str, Any],
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[Dict[str, Any]]] = None,
        reminders: Optional[Dict[str, Any]] = None,
        recurrence: Optional[List[str]] = None,
        visibility: Optional[str] = None,
    ) -> Event:
        """Create a new event in a calendar.

        Args:
            calendar_id: ID of the calendar to create the event in
            summary: Title of the event
            start: Start time information (date_time or date + time_zone)
            end: End time information (date_time or date + time_zone)
            description: Description of the event
            location: Location of the event
            attendees: List of attendees (each with email, optional display_name)
            reminders: Reminder configuration
            recurrence: Recurrence rules
            visibility: Visibility of the event (default, public, private, confidential)

        Returns:
            Created event information

        Raises:
            MCPError: If the request fails
        """
        try:
            # Validate parameters
            params = CreateEventParams(
                calendar_id=calendar_id,
                summary=summary,
                description=description,
                location=location,
                start=start,
                end=end,
                attendees=attendees,
                reminders=reminders,
                recurrence=recurrence,
                visibility=visibility,
            )

            # Call the MCP tool
            response = await self.call_tool(
                "create-event", params.model_dump(exclude_none=True)
            )

            # Parse the response
            if isinstance(response, str):
                response = json.loads(response)

            # Clear cache for this calendar
            cache_key = f"calendar_events:{calendar_id}"
            await redis_cache.delete(cache_key)

            # Validate with Pydantic model
            return Event.model_validate(response)
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for create-event: {str(e)}",
                server=self.server_name,
                tool="create-event",
                params={
                    "calendar_id": calendar_id,
                    "summary": summary,
                    "start": start,
                    "end": end,
                    "description": description,
                    "location": location,
                },
            ) from e
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            raise MCPError(
                message=f"Failed to create event: {str(e)}",
                server=self.server_name,
                tool="create-event",
                params={
                    "calendar_id": calendar_id,
                    "summary": summary,
                    "start": start,
                    "end": end,
                    "description": description,
                    "location": location,
                },
            ) from e

    @function_tool
    async def update_event(
        self,
        calendar_id: str,
        event_id: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        start: Optional[Dict[str, Any]] = None,
        end: Optional[Dict[str, Any]] = None,
        attendees: Optional[List[Dict[str, Any]]] = None,
        reminders: Optional[Dict[str, Any]] = None,
        recurrence: Optional[List[str]] = None,
        visibility: Optional[str] = None,
    ) -> Event:
        """Update an existing event in a calendar.

        Args:
            calendar_id: ID of the calendar containing the event
            event_id: ID of the event to update
            summary: New title of the event
            description: New description of the event
            location: New location of the event
            start: New start time information
            end: New end time information
            attendees: New list of attendees
            reminders: New reminder configuration
            recurrence: New recurrence rules
            visibility: New visibility of the event

        Returns:
            Updated event information

        Raises:
            MCPError: If the request fails
        """
        try:
            # Validate parameters
            params = UpdateEventParams(
                calendar_id=calendar_id,
                event_id=event_id,
                summary=summary,
                description=description,
                location=location,
                start=start,
                end=end,
                attendees=attendees,
                reminders=reminders,
                recurrence=recurrence,
                visibility=visibility,
            )

            # Call the MCP tool
            response = await self.call_tool(
                "update-event", params.model_dump(exclude_none=True)
            )

            # Parse the response
            if isinstance(response, str):
                response = json.loads(response)

            # Clear cache for this calendar
            cache_key = f"calendar_events:{calendar_id}"
            await redis_cache.delete(cache_key)

            # Validate with Pydantic model
            return Event.model_validate(response)
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for update-event: {str(e)}",
                server=self.server_name,
                tool="update-event",
                params={
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "summary": summary,
                    "start": start,
                    "end": end,
                },
            ) from e
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}")
            raise MCPError(
                message=f"Failed to update event: {str(e)}",
                server=self.server_name,
                tool="update-event",
                params={
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "summary": summary,
                    "start": start,
                    "end": end,
                },
            ) from e

    @function_tool
    async def delete_event(self, calendar_id: str, event_id: str) -> Dict[str, bool]:
        """Delete an event from a calendar.

        Args:
            calendar_id: ID of the calendar containing the event
            event_id: ID of the event to delete

        Returns:
            Dictionary indicating success of the deletion

        Raises:
            MCPError: If the request fails
        """
        try:
            # Validate parameters
            params = DeleteEventParams(calendar_id=calendar_id, event_id=event_id)

            # Call the MCP tool
            response = await self.call_tool(
                "delete-event", params.model_dump(exclude_none=True)
            )

            # Parse the response
            if isinstance(response, str):
                response = json.loads(response)

            # Clear cache for this calendar
            cache_key = f"calendar_events:{calendar_id}"
            await redis_cache.delete(cache_key)

            return {"success": True, "deleted": True}
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}")
            raise MCPError(
                message=f"Failed to delete event: {str(e)}",
                server=self.server_name,
                tool="delete-event",
                params={"calendar_id": calendar_id, "event_id": event_id},
            ) from e


class CalendarService:
    """High-level service for calendar operations in TripSage."""

    def __init__(self, client: Optional[CalendarMCPClient] = None):
        """Initialize the Calendar Service.

        Args:
            client: CalendarMCPClient instance. If not provided, uses the default
                client.
        """
        self.client = client or calendar_client
        logger.info("Initialized Calendar Service")

    async def create_itinerary_events(
        self,
        calendar_id: str,
        itinerary_items: List[Dict[str, Any]],
        trip_name: Optional[str] = None,
    ) -> CreateItineraryEventsResponse:
        """Create calendar events from a trip itinerary.

        Args:
            calendar_id: ID of the calendar to create events in
            itinerary_items: List of itinerary items
            trip_name: Name of the trip for event grouping

        Returns:
            Response containing created events and failures
        """
        # Validate parameters
        params = CreateItineraryEventsParams(
            calendar_id=calendar_id,
            itinerary_items=itinerary_items,
            trip_name=trip_name,
        )

        created_events = []
        failed_items = []

        # Process each itinerary item
        for item in params.itinerary_items:
            try:
                # Prepare event data based on item type
                event_data = self._map_itinerary_item_to_event(item, trip_name)

                # Create the event
                event = await self.client.create_event(
                    calendar_id=calendar_id,
                    summary=event_data["summary"],
                    description=event_data.get("description"),
                    location=event_data.get("location"),
                    start=event_data["start"],
                    end=event_data["end"],
                    reminders=event_data.get("reminders"),
                )

                created_events.append(event)
            except Exception as e:
                logger.error(f"Error creating event for itinerary item: {str(e)}")
                failed_items.append({"item": item.model_dump(), "error": str(e)})

        return CreateItineraryEventsResponse(
            created_events=created_events,
            failed_items=failed_items,
            trip_name=trip_name,
        )

    def _map_itinerary_item_to_event(
        self, item: Dict[str, Any], trip_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Map a TripSage itinerary item to a Google Calendar event.

        Args:
            item: Itinerary item
            trip_name: Name of the trip for event context

        Returns:
            Event data for Google Calendar API
        """
        # Get item details
        item_title = item.title
        item_desc = item.description or ""
        item_location = item.location
        item_type = item.type
        start_time = item.start_time
        end_time = item.end_time
        time_zone = item.time_zone

        # If time_zone not specified, use UTC
        if not time_zone:
            time_zone = "UTC"

        # If end_time not provided, calculate from duration
        if not end_time and item.duration_minutes:
            # Parse the start time
            if "T" in start_time:  # ISO format with time
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                end_dt = start_dt + timedelta(minutes=item.duration_minutes)
                end_time = end_dt.isoformat()
            else:  # All-day event
                # For all-day events, we'll keep it as a date string
                # but need to handle duration differently
                # For multi-day events, we need to add days and not just minutes
                days = item.duration_minutes // (24 * 60)
                start_date = datetime.strptime(start_time, "%Y-%m-%d")
                end_date = start_date + timedelta(days=max(1, days))
                end_time = end_date.strftime("%Y-%m-%d")

        # Create the base event data
        event_data = {
            "summary": item_title,
            "description": item_desc,
            "location": item_location,
        }

        # Add trip context to the description if provided
        if trip_name:
            event_data["description"] = (
                f"Trip: {trip_name}\n\n{event_data['description']}"
                if event_data["description"]
                else f"Trip: {trip_name}"
            )

        # Add any confirmation numbers to the description
        if item.confirmation_number:
            event_data["description"] += (
                f"\n\nConfirmation/Booking #: {item.confirmation_number}"
            )

        # Set start and end time format based on whether it's a date-only
        # (all-day) event or a datetime event
        if "T" in start_time:  # ISO format with time
            event_data["start"] = {"date_time": start_time, "time_zone": time_zone}
            event_data["end"] = {"date_time": end_time, "time_zone": time_zone}
        else:  # All-day event
            event_data["start"] = {"date": start_time}
            event_data["end"] = {"date": end_time}

        # Add reminders based on event type
        if item_type == "flight":
            # For flights, remind 3 hours before
            event_data["reminders"] = {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 180}],
            }
        elif item_type == "accommodation":
            # For accommodations (check-in/check-out), remind 1 day before
            event_data["reminders"] = {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 1440}],
            }
        else:
            # For other activities, use default reminders
            event_data["reminders"] = {"useDefault": True}

        # Customize by item type
        if item_type == "flight":
            # Add flight details like flight number to title if available
            if item.details and "flight_number" in item.details:
                event_data["summary"] = (
                    f"Flight {item.details['flight_number']}: {item_title}"
                )

            # Add detailed flight information if available
            if item.details:
                flight_info = []
                if "airline" in item.details:
                    flight_info.append(f"Airline: {item.details['airline']}")
                if "departure_airport" in item.details:
                    flight_info.append(f"From: {item.details['departure_airport']}")
                if "arrival_airport" in item.details:
                    flight_info.append(f"To: {item.details['arrival_airport']}")
                if flight_info:
                    event_data["description"] += "\n\n" + "\n".join(flight_info)

        elif item_type == "accommodation":
            # Add accommodation-specific information
            if item.details:
                accomm_info = []
                if "property_name" in item.details:
                    accomm_info.append(f"Property: {item.details['property_name']}")
                if "check_in_time" in item.details:
                    accomm_info.append(
                        f"Check-in time: {item.details['check_in_time']}"
                    )
                if "check_out_time" in item.details:
                    accomm_info.append(
                        f"Check-out time: {item.details['check_out_time']}"
                    )
                if accomm_info:
                    event_data["description"] += "\n\n" + "\n".join(accomm_info)

        # Add a note that this event was created by TripSage
        event_data["description"] += "\n\nCreated by TripSage"

        return event_data


# Initialize global client instance
calendar_client = CalendarMCPClient()


def get_client() -> CalendarMCPClient:
    """Get a Calendar MCP Client instance.

    Returns:
        CalendarMCPClient instance
    """
    return calendar_client


def get_service() -> CalendarService:
    """Get a Calendar Service instance.

    Returns:
        CalendarService instance
    """
    return CalendarService(calendar_client)
