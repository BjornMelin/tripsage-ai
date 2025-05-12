"""
Configuration settings for TripSage agents

This module provides the configuration settings for the TripSage agents,
now using the centralized settings system.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel

from src.utils.settings import settings


class AgentConfig(BaseModel):
    """Configuration settings for TripSage agents"""

    # OpenAI configuration
    openai_api_key: str = settings.openai_api_key.get_secret_value()
    model_name: str = settings.agent.model_name
    max_tokens: int = settings.agent.max_tokens
    temperature: float = settings.agent.temperature

    # Supabase configuration
    supabase_url: str = settings.database.supabase_url
    supabase_key: str = settings.database.supabase_anon_key.get_secret_value()

    # Travel API configuration
    flight_api_key: Optional[str] = (
        settings.flights_mcp.duffel_api_key.get_secret_value()
        if settings.flights_mcp.duffel_api_key
        else ""
    )
    hotel_api_key: Optional[str] = ""  # No specific hotel API in settings yet

    # Agent settings
    agent_timeout: int = settings.agent.agent_timeout  # seconds
    max_retries: int = settings.agent.max_retries
    agent_memory_size: int = settings.agent.agent_memory_size  # number of messages

    # Default agent parameters
    default_flight_preferences: Dict[str, Any] = (
        settings.agent.default_flight_preferences
    )

    default_accommodation_preferences: Dict[str, Any] = (
        settings.agent.default_accommodation_preferences
    )

    # Helper functions
    def validate_credentials(self) -> bool:
        """Validate that all required credentials are provided"""
        if not self.openai_api_key:
            print("Missing OpenAI API key")
            return False
        if not self.supabase_url or not self.supabase_key:
            print("Missing Supabase credentials")
            return False
        return True

    def get_flight_preferences(
        self, user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Merge default flight preferences with user preferences"""
        if user_preferences is None:
            return self.default_flight_preferences

        merged = self.default_flight_preferences.copy()
        merged.update(user_preferences)
        return merged

    def get_accommodation_preferences(
        self, user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Merge default accommodation preferences with user preferences"""
        if user_preferences is None:
            return self.default_accommodation_preferences

        merged = self.default_accommodation_preferences.copy()
        merged.update(user_preferences)
        return merged


# Create a default config instance
config = AgentConfig()

# Validate credentials
if not config.validate_credentials():
    print(
        "Warning: Some required credentials are missing. "
        "Agents may not function correctly."
    )
