"""
Calendar-related function tools for TripSage.

This module provides OpenAI Agents SDK function tools for calendar operations
using the Google Calendar MCP, allowing agents to list, create, update, and
delete calendar events, as well as convert itineraries to calendar events.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import function_tool

from tripsage.mcp_abstraction.exceptions import TripSageMCPError
from tripsage.mcp_abstraction.manager import mcp_manager
from tripsage.tools.schemas.calendar import (
    EventTime,
)
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


@function_tool
@with_error_handling
async def list_calendars_tool(max_results: Optional[int] = None) -> Dict[str, Any]:
    """List all available Google Calendars.

    Args:
        max_results: Maximum number of calendars to return

    Returns:
        Dictionary with list of calendars including name and ID
    """
    try:
        logger.info("Listing available calendars")

        params = {}
        if max_results:
            params["max_results"] = max_results

        result = await mcp_manager.invoke(
            mcp_name="google_calendar", method_name="get_calendars", params=params
        )

        calendars_info = []
        for calendar in result.calendars:
            primary_indicator = " (Primary)" if calendar.primary else ""
            calendars_info.append(
                {
                    "id": calendar.id,
                    "name": calendar.summary,
                    "is_primary": calendar.primary,
                    "time_zone": calendar.time_zone,
                    "formatted": (
                        f"{calendar.summary}{primary_indicator} (ID: {calendar.id})"
                    ),
                }
            )

        return {
            "calendars": calendars_info,
            "count": len(calendars_info),
            "formatted": "\n".join([cal["formatted"] for cal in calendars_info]),
        }
    except TripSageMCPError as e:
        logger.error(f"MCP error in list_calendars_tool: {str(e)}")
        return {
            "error": f"Failed to list calendars: {str(e)}",
            "calendars": [],
            "count": 0,
        }
    except Exception as e:
        logger.error(f"Error in list_calendars_tool: {str(e)}")
        return {
            "error": f"Failed to list calendars: {str(e)}",
            "calendars": [],
            "count": 0,
        }


@function_tool
@with_error_handling
async def list_events_tool(
    calendar_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_events: Optional[int] = None,
) -> Dict[str, Any]:
    """List events from a Google Calendar.

    Args:
        calendar_id: ID of the calendar to get events from
        start_date: Start date in YYYY-MM-DD format (defaults to today)
        end_date: End date in YYYY-MM-DD format (defaults to 7 days from start)
        max_events: Maximum number of events to return

    Returns:
        Dictionary with list of events
    """
    try:
        logger.info(f"Listing events for calendar: {calendar_id}")

        # Convert dates to ISO format
        time_min = None
        time_max = None

        if start_date:
            if "T" not in start_date:
                # Convert YYYY-MM-DD to ISO format
                start_date = f"{start_date}T00:00:00Z"
            time_min = start_date

        if end_date:
            if "T" not in end_date:
                # Convert YYYY-MM-DD to ISO format with end of day
                end_date = f"{end_date}T23:59:59Z"
            time_max = end_date

        params = {
            "calendar_id": calendar_id,
            "single_events": True,
            "order_by": "startTime",
        }

        if time_min:
            params["time_min"] = time_min
        if time_max:
            params["time_max"] = time_max
        if max_events:
            params["max_results"] = max_events

        result = await mcp_manager.invoke(
            mcp_name="google_calendar", method_name="get_events", params=params
        )

        events_info = []
        for event in result.events:
            # Get start and end time/date
            start_info = _format_event_time(event.start)
            end_info = _format_event_time(event.end)

            events_info.append(
                {
                    "id": event.id,
                    "title": event.summary,
                    "description": event.description,
                    "location": event.location,
                    "start": start_info,
                    "end": end_info,
                    "status": event.status,
                    "formatted": f"{event.summary} - {start_info} to {end_info}"
                    + (f" at {event.location}" if event.location else ""),
                }
            )

        return {
            "events": events_info,
            "count": len(events_info),
            "calendar_id": calendar_id,
            "formatted": "\n".join([event["formatted"] for event in events_info])
            if events_info
            else "No events found in the specified time range.",
        }
    except TripSageMCPError as e:
        logger.error(f"MCP error in list_events_tool: {str(e)}")
        return {
            "error": f"Failed to list events: {str(e)}",
            "events": [],
            "count": 0,
            "calendar_id": calendar_id,
        }
    except Exception as e:
        logger.error(f"Error in list_events_tool: {str(e)}")
        return {
            "error": f"Failed to list events: {str(e)}",
            "events": [],
            "count": 0,
            "calendar_id": calendar_id,
        }


@function_tool
@with_error_handling
async def search_events_tool(
    query: str, calendar_id: str, max_results: Optional[int] = None
) -> Dict[str, Any]:
    """Search for events in a Google Calendar that match a query.

    Args:
        query: Search query string
        calendar_id: ID of the calendar to search
        max_results: Maximum number of events to return

    Returns:
        Dictionary with matching events
    """
    try:
        logger.info(
            f"Searching for events matching '{query}' in calendar: {calendar_id}"
        )

        params = {
            "calendar_id": calendar_id,
            "query": query,
        }

        if max_results:
            params["max_results"] = max_results

        result = await mcp_manager.invoke(
            mcp_name="google_calendar", method_name="search_events", params=params
        )

        events_info = []
        for event in result.events:
            # Get start and end time/date
            start_info = _format_event_time(event.start)
            end_info = _format_event_time(event.end)

            events_info.append(
                {
                    "id": event.id,
                    "title": event.summary,
                    "description": event.description,
                    "location": event.location,
                    "start": start_info,
                    "end": end_info,
                    "status": event.status,
                    "formatted": f"{event.summary} - {start_info} to {end_info}"
                    + (f" at {event.location}" if event.location else ""),
                }
            )

        return {
            "events": events_info,
            "count": len(events_info),
            "query": query,
            "calendar_id": calendar_id,
            "formatted": "\n".join([event["formatted"] for event in events_info])
            if events_info
            else f"No events found matching query: {query}",
        }
    except TripSageMCPError as e:
        logger.error(f"MCP error in search_events_tool: {str(e)}")
        return {
            "error": f"Failed to search events: {str(e)}",
            "events": [],
            "count": 0,
            "query": query,
            "calendar_id": calendar_id,
        }
    except Exception as e:
        logger.error(f"Error in search_events_tool: {str(e)}")
        return {
            "error": f"Failed to search events: {str(e)}",
            "events": [],
            "count": 0,
            "query": query,
            "calendar_id": calendar_id,
        }


@function_tool
@with_error_handling
async def create_event_tool(
    calendar_id: str,
    summary: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    time_zone: Optional[str] = None,
    attendees: Optional[List[Dict[str, str]]] = None,
    is_all_day: bool = False,
) -> Dict[str, Any]:
    """Create a new event in a Google Calendar.

    Args:
        calendar_id: ID of the calendar to create the event in
        summary: Title of the event
        start_time: Start time (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS format)
        end_time: End time (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS format)
        description: Description of the event
        location: Location of the event
        time_zone: Time zone (IANA format, e.g., 'America/New_York')
        attendees: List of attendees (each with 'email' and optional 'name')
        is_all_day: Whether this is an all-day event

    Returns:
        Dictionary with created event information
    """
    try:
        logger.info(f"Creating event '{summary}' in calendar: {calendar_id}")

        # Format start and end time
        start = {}
        end = {}
        if is_all_day:
            # All-day event format
            start = {"date": start_time}
            end = {"date": end_time}
        else:
            # Regular event format
            if "T" not in start_time:
                start_time = f"{start_time}T00:00:00"
            if "T" not in end_time:
                end_time = f"{end_time}T00:00:00"

            start = {"date_time": start_time}
            end = {"date_time": end_time}

            # Add time zone if provided
            if time_zone:
                start["time_zone"] = time_zone
                end["time_zone"] = time_zone

        # Format attendees
        formatted_attendees = None
        if attendees:
            formatted_attendees = [
                {"email": attendee["email"], "display_name": attendee.get("name", "")}
                for attendee in attendees
            ]

        # Create event parameters
        params = {
            "calendar_id": calendar_id,
            "summary": summary,
            "start": start,
            "end": end,
        }

        if description:
            params["description"] = description
        if location:
            params["location"] = location
        if formatted_attendees:
            params["attendees"] = formatted_attendees

        # Call the MCP
        result = await mcp_manager.invoke(
            mcp_name="google_calendar", method_name="create_event", params=params
        )

        # Format response
        start_info = _format_event_time(result.start)
        end_info = _format_event_time(result.end)

        return {
            "id": result.id,
            "title": result.summary,
            "description": result.description,
            "location": result.location,
            "start": start_info,
            "end": end_info,
            "html_link": str(result.html_link) if result.html_link else None,
            "calendar_id": calendar_id,
            "formatted": f"Event created: {result.summary} - {start_info} to {end_info}"
            + (f" at {result.location}" if result.location else ""),
        }
    except TripSageMCPError as e:
        logger.error(f"MCP error in create_event_tool: {str(e)}")
        return {
            "error": f"Failed to create event: {str(e)}",
            "calendar_id": calendar_id,
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"Error in create_event_tool: {str(e)}")
        return {
            "error": f"Failed to create event: {str(e)}",
            "calendar_id": calendar_id,
            "summary": summary,
        }


@function_tool
@with_error_handling
async def update_event_tool(
    calendar_id: str,
    event_id: str,
    summary: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    time_zone: Optional[str] = None,
    is_all_day: Optional[bool] = None,
) -> Dict[str, Any]:
    """Update an existing event in a Google Calendar.

    Args:
        calendar_id: ID of the calendar containing the event
        event_id: ID of the event to update
        summary: New title of the event (if changing)
        start_time: New start time (if changing)
        end_time: New end time (if changing)
        description: New description of the event (if changing)
        location: New location of the event (if changing)
        time_zone: New time zone (if changing)
        is_all_day: Whether to convert to all-day event

    Returns:
        Dictionary with updated event information
    """
    try:
        logger.info(f"Updating event {event_id} in calendar: {calendar_id}")

        # Prepare update parameters
        params = {"calendar_id": calendar_id, "event_id": event_id}

        if summary:
            params["summary"] = summary

        if description:
            params["description"] = description

        if location:
            params["location"] = location

        # Handle start and end time updates
        if start_time or end_time or is_all_day is not None:
            # First, get the current event
            current_event_params = {
                "calendar_id": calendar_id,
                "time_min": None,
                "time_max": None,
                "max_results": 1,
            }

            events_response = await mcp_manager.invoke(
                mcp_name="google_calendar",
                method_name="get_events",
                params=current_event_params,
            )

            current_event = None
            for event in events_response.events:
                if event.id == event_id:
                    current_event = event
                    break

            if not current_event:
                raise ValueError(
                    f"Event {event_id} not found in calendar {calendar_id}"
                )

            # Determine if the current event is an all-day event
            current_is_all_day = (
                hasattr(current_event.start, "date")
                and current_event.start.date is not None
                and not hasattr(current_event.start, "date_time")
            )

            # Use provided is_all_day or keep current format
            is_all_day = is_all_day if is_all_day is not None else current_is_all_day

            # Create start and end objects based on new format
            if start_time:
                if is_all_day:
                    # Format as date-only
                    if "T" in start_time:
                        start_time = start_time.split("T")[0]
                    params["start"] = {"date": start_time}
                else:
                    # Format as date-time
                    if "T" not in start_time:
                        start_time = f"{start_time}T00:00:00"
                    params["start"] = {"date_time": start_time}
                    if time_zone:
                        params["start"]["time_zone"] = time_zone

            if end_time:
                if is_all_day:
                    # Format as date-only
                    if "T" in end_time:
                        end_time = end_time.split("T")[0]
                    params["end"] = {"date": end_time}
                else:
                    # Format as date-time
                    if "T" not in end_time:
                        end_time = f"{end_time}T00:00:00"
                    params["end"] = {"date_time": end_time}
                    if time_zone:
                        params["end"]["time_zone"] = time_zone

            # Handle conversion between all-day and time-specific events
            if is_all_day != current_is_all_day:
                if is_all_day:
                    # Convert to all-day: get date from datetime
                    if not start_time and hasattr(current_event.start, "date_time"):
                        start_date = current_event.start.date_time.split("T")[0]
                        params["start"] = {"date": start_date}

                    if not end_time and hasattr(current_event.end, "date_time"):
                        end_date = current_event.end.date_time.split("T")[0]
                        params["end"] = {"date": end_date}
                else:
                    # Convert to time-specific: add time to date
                    if not start_time and hasattr(current_event.start, "date"):
                        params["start"] = {
                            "date_time": f"{current_event.start.date}T00:00:00"
                        }
                        if time_zone:
                            params["start"]["time_zone"] = time_zone

                    if not end_time and hasattr(current_event.end, "date"):
                        params["end"] = {
                            "date_time": f"{current_event.end.date}T00:00:00"
                        }
                        if time_zone:
                            params["end"]["time_zone"] = time_zone

        # Update the event
        result = await mcp_manager.invoke(
            mcp_name="google_calendar", method_name="update_event", params=params
        )

        # Format response
        start_info = _format_event_time(result.start)
        end_info = _format_event_time(result.end)

        return {
            "id": result.id,
            "title": result.summary,
            "description": result.description,
            "location": result.location,
            "start": start_info,
            "end": end_info,
            "html_link": str(result.html_link) if result.html_link else None,
            "calendar_id": calendar_id,
            "formatted": f"Event updated: {result.summary} - {start_info} to {end_info}"
            + (f" at {result.location}" if result.location else ""),
        }
    except TripSageMCPError as e:
        logger.error(f"MCP error in update_event_tool: {str(e)}")
        return {
            "error": f"Failed to update event: {str(e)}",
            "calendar_id": calendar_id,
            "event_id": event_id,
        }
    except Exception as e:
        logger.error(f"Error in update_event_tool: {str(e)}")
        return {
            "error": f"Failed to update event: {str(e)}",
            "calendar_id": calendar_id,
            "event_id": event_id,
        }


@function_tool
@with_error_handling
async def delete_event_tool(calendar_id: str, event_id: str) -> Dict[str, Any]:
    """Delete an event from a Google Calendar.

    Args:
        calendar_id: ID of the calendar containing the event
        event_id: ID of the event to delete

    Returns:
        Dictionary indicating success of the deletion
    """
    try:
        logger.info(f"Deleting event {event_id} from calendar: {calendar_id}")

        params = {
            "calendar_id": calendar_id,
            "event_id": event_id,
        }

        result = await mcp_manager.invoke(
            mcp_name="google_calendar", method_name="delete_event", params=params
        )

        return {
            "success": result.get("success", False),
            "deleted": result.get("deleted", False),
            "calendar_id": calendar_id,
            "event_id": event_id,
            "formatted": f"Event {event_id} successfully deleted from calendar.",
        }
    except TripSageMCPError as e:
        logger.error(f"MCP error in delete_event_tool: {str(e)}")
        return {
            "error": f"Failed to delete event: {str(e)}",
            "success": False,
            "deleted": False,
            "calendar_id": calendar_id,
            "event_id": event_id,
        }
    except Exception as e:
        logger.error(f"Error in delete_event_tool: {str(e)}")
        return {
            "error": f"Failed to delete event: {str(e)}",
            "success": False,
            "deleted": False,
            "calendar_id": calendar_id,
            "event_id": event_id,
        }


@function_tool
@with_error_handling
async def create_itinerary_events_tool(
    calendar_id: str,
    itinerary_items: List[Dict[str, Any]],
    trip_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create Google Calendar events from a trip itinerary.

    This tool converts TripSage itinerary items into calendar events. Each itinerary
    item should include type (flight, accommodation, activity, etc.), title, times,
    and location information.

    Args:
        calendar_id: ID of the calendar to create events in
        itinerary_items: List of itinerary items to convert to events
        trip_name: Name of the trip for event grouping

    Returns:
        Dictionary with created events and any failures
    """
    try:
        logger.info(
            f"Creating calendar events for {len(itinerary_items)} itinerary items"
        )

        params = {
            "calendar_id": calendar_id,
            "itinerary_items": itinerary_items,
        }

        if trip_name:
            params["trip_name"] = trip_name

        result = await mcp_manager.invoke(
            mcp_name="google_calendar",
            method_name="create_itinerary_events",
            params=params,
        )

        # Format successful events
        created_events_info = []
        for event in result.created_events:
            start_info = _format_event_time(event.start)
            end_info = _format_event_time(event.end)

            created_events_info.append(
                {
                    "id": event.id,
                    "title": event.summary,
                    "start": start_info,
                    "end": end_info,
                    "location": event.location,
                    "formatted": f"{event.summary} - {start_info} to {end_info}"
                    + (f" at {event.location}" if event.location else ""),
                }
            )

        # Format failures
        failed_items_info = []
        for failed in result.failed_items:
            item = failed.get("item", {})
            error = failed.get("error", "Unknown error")

            failed_items_info.append(
                {
                    "title": item.get("title", "Unknown"),
                    "type": item.get("type", "Unknown"),
                    "error": error,
                    "formatted": (
                        f"Failed to create event for {item.get('title', 'Unknown')}: "
                        f"{error}"
                    ),
                }
            )

        # Format overall summary
        summary = (
            f"Created {len(created_events_info)} events for trip: "
            f"{trip_name or 'Untitled Trip'}"
        )
        if failed_items_info:
            summary += f"\n{len(failed_items_info)} items failed to create."

        return {
            "created_events": created_events_info,
            "failed_items": failed_items_info,
            "trip_name": trip_name,
            "calendar_id": calendar_id,
            "success_count": len(created_events_info),
            "failure_count": len(failed_items_info),
            "total_items": len(itinerary_items),
            "summary": summary,
            "formatted": (
                f"{summary}\n\n"
                "Created events:\n"
                + "\n".join([e["formatted"] for e in created_events_info])
            ),
        }
    except TripSageMCPError as e:
        logger.error(f"MCP error in create_itinerary_events_tool: {str(e)}")
        return {
            "error": f"Failed to create itinerary events: {str(e)}",
            "created_events": [],
            "failed_items": [{"error": str(e), "formatted": f"Error: {str(e)}"}],
            "calendar_id": calendar_id,
            "success_count": 0,
            "failure_count": len(itinerary_items),
            "total_items": len(itinerary_items),
        }
    except Exception as e:
        logger.error(f"Error in create_itinerary_events_tool: {str(e)}")
        return {
            "error": f"Failed to create itinerary events: {str(e)}",
            "created_events": [],
            "failed_items": [{"error": str(e), "formatted": f"Error: {str(e)}"}],
            "calendar_id": calendar_id,
            "success_count": 0,
            "failure_count": len(itinerary_items),
            "total_items": len(itinerary_items),
        }


def _format_event_time(event_time: EventTime) -> str:
    """Format event time for display.

    Args:
        event_time: Event time object with date or date_time

    Returns:
        Formatted time string
    """
    if event_time.date:
        return f"All day {event_time.date}"

    if event_time.date_time:
        # Format datetime to a more readable form
        dt_str = event_time.date_time

        # Handle ISO format with 'Z' or timezone offset
        if "Z" in dt_str:
            dt_str = dt_str.replace("Z", "+00:00")

        try:
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            # Fallback if parsing fails
            return dt_str

    return "Unknown time"
