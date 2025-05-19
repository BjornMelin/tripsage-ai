"""
Weather MCP Wrapper implementation.

This wrapper provides a standardized interface for the Weather MCP client,
mapping user-friendly method names to actual Weather MCP client methods.
"""

from typing import Dict, List

from tripsage.clients.weather.weather_mcp_client import WeatherMCPClient
from tripsage.config.mcp_settings import mcp_settings
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper


class WeatherMCPWrapper(BaseMCPWrapper):
    """Wrapper for the Weather MCP client."""

    def __init__(self, client: WeatherMCPClient = None, mcp_name: str = "weather"):
        """
        Initialize the Weather MCP wrapper.

        Args:
            client: Optional pre-initialized client, will create one if None
            mcp_name: Name identifier for this MCP service
        """
        if client is None:
            # Create client from configuration
            config = mcp_settings.weather
            # WeatherMCPClient expects endpoint and API key from initialization
            client = WeatherMCPClient(
                endpoint=str(config.url),
                api_key=config.api_key.get_secret_value() if config.api_key else None,
            )
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to actual client methods.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        return {
            # Current weather - based on what I saw in the client
            "get_current_weather": "get_current_weather",
            # Forecast - based on what I saw in the client
            "get_forecast": "get_forecast",
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names.

        Returns:
            List of available method names
        """
        return list(self._method_map.keys())
