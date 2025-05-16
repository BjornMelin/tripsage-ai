"""
Time MCP Wrapper implementation.

This wrapper provides a standardized interface for the Time MCP client,
mapping user-friendly method names to actual Time MCP client methods.
"""

from typing import Dict, List

from tripsage.mcp.time.client import TimeMCPClient
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper


class TimeMCPWrapper(BaseMCPWrapper):
    """Wrapper for the Time MCP client."""

    def __init__(self, client: TimeMCPClient = None, mcp_name: str = "time"):
        """
        Initialize the Time MCP wrapper.

        Args:
            client: Optional pre-initialized client, will create one if None
            mcp_name: Name identifier for this MCP service
        """
        if client is None:
            # Create client from configuration
            from tripsage.mcp.time.factory import get_client

            client = get_client()
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to actual client methods.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        return {
            # Time operations
            "get_current_time": "get_current_time",
            "get_time": "get_current_time",
            "current_time": "get_current_time",
            "now": "get_current_time",
            # Timezone conversion
            "convert_time": "convert_time",
            "convert_timezone": "convert_time",
            "timezone_convert": "convert_time",
            # Flight arrival time calculations
            "calculate_arrival_time": "calculate_flight_arrival_time",
            "flight_arrival_time": "calculate_flight_arrival_time",
            # Meeting time optimization
            "find_meeting_time": "find_optimal_meeting_time",
            "optimize_meeting_time": "find_optimal_meeting_time",
            "suggest_meeting_time": "find_optimal_meeting_time",
            # Itinerary timezone processing
            "process_itinerary": "process_itinerary_timezones",
            "itinerary_timezones": "process_itinerary_timezones",
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names.

        Returns:
            List of available method names
        """
        return list(self._method_map.keys())
