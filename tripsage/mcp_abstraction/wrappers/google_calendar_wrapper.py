"""
Google Calendar MCP Wrapper implementation.

This wrapper provides a standardized interface for the Google Calendar MCP client,
mapping user-friendly method names to actual Google Calendar MCP client methods.
"""

from typing import Dict, List

from tripsage.mcp.calendar.client import CalendarMCPClient
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper


class GoogleCalendarMCPWrapper(BaseMCPWrapper):
    """Wrapper for the Google Calendar MCP client."""

    def __init__(
        self, client: CalendarMCPClient = None, mcp_name: str = "google_calendar"
    ):
        """
        Initialize the Google Calendar MCP wrapper.

        Args:
            client: Optional pre-initialized client, will create one if None
            mcp_name: Name identifier for this MCP service
        """
        if client is None:
            # Create client from configuration
            client = CalendarMCPClient()
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to actual client methods.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        return {
            # Calendar listing
            "list_calendars": "list_calendars",
            "get_calendars": "list_calendars",
            # Event operations
            "create_event": "create_event",
            "add_event": "create_event",
            "new_event": "create_event",
            "list_events": "list_events",
            "get_events": "list_events",
            "search_events": "search_events",
            "find_events": "search_events",
            "query_events": "search_events",
            "update_event": "update_event",
            "edit_event": "update_event",
            "modify_event": "update_event",
            "delete_event": "delete_event",
            "remove_event": "delete_event",
            # Itinerary specific operations
            "create_itinerary_events": "create_itinerary_events",
            "add_itinerary": "create_itinerary_events",
            "schedule_itinerary": "create_itinerary_events",
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names.

        Returns:
            List of available method names
        """
        return list(self._method_map.keys())
