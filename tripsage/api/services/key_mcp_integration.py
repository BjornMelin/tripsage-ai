"""MCP integration service for dynamic API key management.

This module provides integration between the KeyService and MCPManager,
enabling dynamic injection of user-provided API keys into MCP operations.
"""

import logging
from typing import Any, Dict, Optional

from tripsage.api.services.key import KeyService
from tripsage.mcp_abstraction import mcp_manager
from tripsage.mcp_abstraction.exceptions import MCPAuthenticationError

logger = logging.getLogger(__name__)


class KeyMCPIntegrationService:
    """Service for integrating user API keys with MCP operations.

    This service extends the MCPManager to dynamically inject user-provided
    API keys when making MCP calls, with fallback to default keys.
    """

    def __init__(self, key_service: Optional[KeyService] = None):
        """Initialize the integration service.

        Args:
            key_service: KeyService instance or None to create one
        """
        self.key_service = key_service or KeyService()
        self.mcp_manager = mcp_manager
        self._cache: Dict[str, Dict[str, str]] = {}  # Simple in-memory cache

    async def invoke_with_user_key(
        self,
        mcp_name: str,
        method_name: str,
        user_id: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Any:
        """Invoke an MCP method with user's API key if available.

        This method attempts to use the user's API key for the service,
        falling back to default configuration if no user key is available.

        Args:
            mcp_name: The name of the MCP to use
            method_name: The method to invoke
            user_id: The user ID for key lookup
            params: Method parameters as a dictionary
            **kwargs: Additional keyword arguments

        Returns:
            The result from the MCP method call

        Raises:
            MCPAuthenticationError: If authentication fails with both user
            and default keys
        """
        # Try to get user's API key for the service
        user_key = await self._get_user_key_for_service(user_id, mcp_name)

        # Prepare parameters
        call_params = params or {}
        call_params.update(kwargs)

        # If we have a user key, inject it into the call
        if user_key:
            logger.info(
                f"Using user-provided API key for {mcp_name}",
                extra={
                    "user_id": user_id,
                    "mcp_name": mcp_name,
                    "method": method_name,
                },
            )

            # Inject the user's API key into the parameters
            call_params = self._inject_api_key(call_params, mcp_name, user_key)

            try:
                # Attempt the call with user's key
                result = await self.mcp_manager.invoke(
                    mcp_name, method_name, call_params
                )

                # Cache the successful key for faster future access
                self._cache_user_key(user_id, mcp_name, user_key)

                return result

            except MCPAuthenticationError as e:
                # User's key failed, log and fallback to default
                logger.warning(
                    f"User API key failed for {mcp_name}, falling back to default",
                    extra={
                        "user_id": user_id,
                        "mcp_name": mcp_name,
                        "error": str(e),
                    },
                )
                # Remove from cache if it was cached
                self._remove_from_cache(user_id, mcp_name)

        # Use default configuration (no user key or user key failed)
        logger.info(
            f"Using default configuration for {mcp_name}",
            extra={
                "user_id": user_id,
                "mcp_name": mcp_name,
                "method": method_name,
                "has_user_key": bool(user_key),
            },
        )

        # Remove user key injection if it was added
        call_params = self._remove_api_key_injection(call_params, mcp_name)

        return await self.mcp_manager.invoke(mcp_name, method_name, call_params)

    async def _get_user_key_for_service(
        self, user_id: str, service: str
    ) -> Optional[str]:
        """Get a user's API key for a specific service.

        Args:
            user_id: The user ID
            service: The service name

        Returns:
            The decrypted API key if found, None otherwise
        """
        # Check cache first
        if user_id in self._cache and service in self._cache[user_id]:
            return self._cache[user_id][service]

        try:
            # Get the key from the key service
            key = await self.key_service.get_key_for_service(user_id, service)

            if key:
                # Cache it for future use
                self._cache_user_key(user_id, service, key)

            return key

        except Exception as e:
            logger.error(f"Error getting user key for service {service}: {e}")
            return None

    def _inject_api_key(
        self, params: Dict[str, Any], service: str, api_key: str
    ) -> Dict[str, Any]:
        """Inject an API key into method parameters based on service type.

        Args:
            params: Original parameters
            service: Service name
            api_key: API key to inject

        Returns:
            Parameters with API key injected
        """
        # Create a copy to avoid modifying the original
        injected_params = params.copy()

        # Service-specific key injection logic
        if service == "openai":
            injected_params["api_key"] = api_key
        elif service == "google_maps":
            injected_params["api_key"] = api_key
        elif service == "weather":
            injected_params["api_key"] = api_key
        elif service == "duffel" or service == "flights":
            injected_params["api_token"] = api_key
        elif service == "airbnb":
            injected_params["api_key"] = api_key
        elif service == "firecrawl":
            injected_params["api_key"] = api_key
        else:
            # Generic fallback
            injected_params["api_key"] = api_key

        return injected_params

    def _remove_api_key_injection(
        self, params: Dict[str, Any], service: str
    ) -> Dict[str, Any]:
        """Remove API key injection from parameters.

        Args:
            params: Parameters with potential API key
            service: Service name

        Returns:
            Parameters with API key injection removed
        """
        # Create a copy to avoid modifying the original
        clean_params = params.copy()

        # Remove common API key parameter names
        keys_to_remove = []

        if service == "duffel" or service == "flights":
            keys_to_remove = ["api_token"]
        else:
            keys_to_remove = ["api_key"]

        for key in keys_to_remove:
            clean_params.pop(key, None)

        return clean_params

    def _cache_user_key(self, user_id: str, service: str, api_key: str) -> None:
        """Cache a user's API key for faster access.

        Args:
            user_id: The user ID
            service: The service name
            api_key: The API key to cache
        """
        if user_id not in self._cache:
            self._cache[user_id] = {}
        self._cache[user_id][service] = api_key

    def _remove_from_cache(self, user_id: str, service: str) -> None:
        """Remove a user's API key from cache.

        Args:
            user_id: The user ID
            service: The service name
        """
        if user_id in self._cache:
            self._cache[user_id].pop(service, None)
            if not self._cache[user_id]:
                del self._cache[user_id]

    async def invalidate_user_cache(
        self, user_id: str, service: Optional[str] = None
    ) -> None:
        """Invalidate cached keys for a user.

        Args:
            user_id: The user ID
            service: Specific service to invalidate, or None for all services
        """
        if user_id in self._cache:
            if service:
                self._cache[user_id].pop(service, None)
            else:
                del self._cache[user_id]

    async def validate_user_key_for_service(self, user_id: str, service: str) -> bool:
        """Validate that a user's API key works for a service.

        Args:
            user_id: The user ID
            service: The service name

        Returns:
            True if the key is valid and works, False otherwise
        """
        try:
            # Get the user's key
            user_key = await self._get_user_key_for_service(user_id, service)
            if not user_key:
                return False

            # Try a simple validation call
            test_params = self._inject_api_key({}, service, user_key)

            # Use a lightweight validation method if available
            validation_method = self._get_validation_method(service)
            if validation_method:
                await self.mcp_manager.invoke(service, validation_method, test_params)
                return True
            else:
                # No specific validation method, assume valid if we have the key
                return True

        except Exception as e:
            logger.warning(f"User key validation failed for {service}: {e}")
            # Remove from cache if validation fails
            self._remove_from_cache(user_id, service)
            return False

    def _get_validation_method(self, service: str) -> Optional[str]:
        """Get the validation method name for a service.

        Args:
            service: The service name

        Returns:
            Validation method name or None if no specific method
        """
        validation_methods = {
            "openai": "list_models",  # Simple method to test API key
            "google_maps": "geocode",  # Simple geocoding test
            "weather": "current_weather",  # Current weather test
            "duffel": "get_airlines",  # List airlines test
        }

        return validation_methods.get(service)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics
        """
        total_users = len(self._cache)
        total_keys = sum(len(services) for services in self._cache.values())

        services = set()
        for user_services in self._cache.values():
            services.update(user_services.keys())

        return {
            "total_users": total_users,
            "total_cached_keys": total_keys,
            "cached_services": list(services),
            "cache_size": len(self._cache),
        }


# Global instance for easy access
key_mcp_integration = KeyMCPIntegrationService()
