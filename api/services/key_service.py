"""
Service for managing user-provided API keys (BYOK functionality).

This service handles validation, storage, and retrieval of user API keys
for external services.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from supabase import Client, create_client

from api.core.config import settings
from tripsage.mcp_abstraction import mcp_manager
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as KeyValidationError,
)

logger = logging.getLogger(__name__)


class KeyService:
    """Service for managing API keys."""

    def __init__(self):
        """Initialize the key service."""
        self.supabase: Optional[Client] = None
        self.mcp_manager = mcp_manager

    async def _get_supabase_client(self) -> Client:
        """Get or create Supabase client."""
        if self.supabase is None:
            self.supabase = create_client(
                settings.supabase_url, settings.supabase_anon_key
            )
        return self.supabase

    async def save_key(self, user_id: str, service: str, api_key: str) -> bool:
        """Save an API key for a user.

        Args:
            user_id: User ID
            service: Service name
            api_key: API key value

        Returns:
            True if successful, False otherwise
        """
        try:
            # Save the key in the database
            key_data = {
                "user_id": user_id,
                "service": service,
                "api_key": api_key,  # In a real implementation, encrypt this value
                "created_at": datetime.now(datetime.UTC).isoformat(),
                "last_validated": datetime.now(datetime.UTC).isoformat(),
                "is_valid": True,
            }

            # Use the storage service to save the key
            await self._get_supabase_client()
            result = await self.supabase.table("api_keys").insert(key_data).execute()

            return result is not None

        except Exception as e:
            logger.error(
                f"Error saving API key for user {user_id}, service {service}: {str(e)}"
            )
            return False

    async def get_key(self, user_id: str, service: str) -> Optional[Dict[str, Any]]:
        """Get API key information for a user.

        Args:
            user_id: User ID
            service: Service name

        Returns:
            Key information or None if not found
        """
        try:
            # Retrieve the key from the database
            await self._get_supabase_client()
            key_data = (
                await self.supabase.table("api_keys")
                .select("*")
                .eq("user_id", user_id)
                .eq("service", service)
                .execute()
            )

            if not key_data["data"]:
                return None

            # Return key information (without the actual key)
            return {
                "service": service,
                "has_key": True,
                "is_valid": key_data["data"][0]["is_valid"],
                "last_validated": key_data["data"][0]["last_validated"],
                "last_used": key_data["data"][0]["last_used"],
            }

        except Exception as e:
            logger.error(
                f"Error retrieving API key for user {user_id}, "
                f"service {service}: {str(e)}"
            )
            return None

    async def get_all_keys(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary of service names to key information
        """
        try:
            # Retrieve all keys from the database
            await self._get_supabase_client()
            keys = (
                await self.supabase.table("api_keys")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )

            result = {}
            for key in keys["data"]:
                service = key["service"]
                result[service] = {
                    "service": service,
                    "has_key": True,
                    "is_valid": key["is_valid"],
                    "last_validated": key["last_validated"],
                    "last_used": key["last_used"],
                }

            return result

        except Exception as e:
            logger.error(f"Error retrieving API keys for user {user_id}: {str(e)}")
            return {}

    async def delete_key(self, user_id: str, service: str) -> bool:
        """Delete an API key for a user.

        Args:
            user_id: User ID
            service: Service name

        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete the key from the database
            await self._get_supabase_client()
            result = (
                await self.supabase.table("api_keys")
                .delete()
                .eq("user_id", user_id)
                .eq("service", service)
                .execute()
            )

            return result is not None

        except Exception as e:
            logger.error(
                f"Error deleting API key for user {user_id}, "
                f"service {service}: {str(e)}"
            )
            return False

    async def validate_key(self, service: str, api_key: str) -> Dict[str, Any]:
        """Validate an API key.

        Args:
            service: Service name
            api_key: API key value

        Returns:
            Validation result containing:
            - is_valid: Whether the key is valid
            - message: Status message
            - details: Additional validation details (optional)

        Raises:
            KeyValidationError: If validation fails
        """
        try:
            validation_result = {
                "is_valid": False,
                "message": "Key validation not implemented for this service.",
            }

            # Validate the key based on the service
            if service == "openai":
                validation_result = await self._validate_openai_key(api_key)
            elif service == "weather":
                validation_result = await self._validate_weather_key(api_key)
            elif service == "flights":
                validation_result = await self._validate_flights_key(api_key)
            elif service == "googleMaps":
                validation_result = await self._validate_googlemaps_key(api_key)
            elif service == "accommodation":
                validation_result = await self._validate_accommodation_key(api_key)
            elif service == "webCrawl":
                validation_result = await self._validate_webcrawl_key(api_key)
            else:
                # For services without specific validation
                validation_result = {
                    "is_valid": True,
                    "message": "Key accepted without validation.",
                }

            return validation_result

        except Exception as e:
            logger.error(f"Error validating API key for service {service}: {str(e)}")
            raise KeyValidationError(
                message=f"Error validating API key: {str(e)}",
                details={"service": service},
            ) from e

    async def _validate_openai_key(self, api_key: str) -> Dict[str, Any]:
        """Validate an OpenAI API key.

        Args:
            api_key: OpenAI API key

        Returns:
            Validation result
        """
        try:
            # Simple OpenAI key validation logic
            if not api_key.startswith("sk-"):
                return {
                    "is_valid": False,
                    "message": "Invalid OpenAI API key format.",
                }

            # In a real implementation, make a test API call to OpenAI
            # to verify the key is valid and active

            return {
                "is_valid": True,
                "message": "OpenAI API key is valid.",
            }
        except Exception as e:
            return {
                "is_valid": False,
                "message": f"Error validating OpenAI API key: {str(e)}",
            }

    async def _validate_weather_key(self, api_key: str) -> Dict[str, Any]:
        """Validate a weather API key.

        Args:
            api_key: Weather API key

        Returns:
            Validation result
        """
        try:
            # Initialize the weather MCP
            # weather_mcp = await self.mcp_manager.initialize_mcp("weather")

            # Call a simple validation method
            # In a real implementation, this would call the weather API with the key

            return {
                "is_valid": True,
                "message": "Weather API key accepted.",
            }
        except Exception as e:
            return {
                "is_valid": False,
                "message": f"Error validating weather API key: {str(e)}",
            }

    async def _validate_flights_key(self, api_key: str) -> Dict[str, Any]:
        """Validate a flights API key.

        Args:
            api_key: Flights API key

        Returns:
            Validation result
        """
        # Implement validation logic for flights API key
        return {
            "is_valid": True,
            "message": "Flights API key accepted.",
        }

    async def _validate_googlemaps_key(self, api_key: str) -> Dict[str, Any]:
        """Validate a Google Maps API key.

        Args:
            api_key: Google Maps API key

        Returns:
            Validation result
        """
        # Implement validation logic for Google Maps API key
        return {
            "is_valid": True,
            "message": "Google Maps API key accepted.",
        }

    async def _validate_accommodation_key(self, api_key: str) -> Dict[str, Any]:
        """Validate an accommodation API key.

        Args:
            api_key: Accommodation API key

        Returns:
            Validation result
        """
        # Implement validation logic for accommodation API key
        return {
            "is_valid": True,
            "message": "Accommodation API key accepted.",
        }

    async def _validate_webcrawl_key(self, api_key: str) -> Dict[str, Any]:
        """Validate a web crawl API key.

        Args:
            api_key: Web crawl API key

        Returns:
            Validation result
        """
        # Implement validation logic for web crawl API key
        return {
            "is_valid": True,
            "message": "Web crawl API key accepted.",
        }
