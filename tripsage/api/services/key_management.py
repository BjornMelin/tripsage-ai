"""Key management service for TripSage API.

This service acts as a thin wrapper around the core key management service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import Dict, List, Optional

from fastapi import Depends

from tripsage.api.schemas.requests.api_keys import (
    ApiKeyCreate,
    ApiKeyRotateRequest,
    ApiKeyValidateRequest,
)
from tripsage.api.schemas.responses.api_keys import (
    ApiKeyResponse,
    ApiKeyValidateResponse,
)
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.key_management_service import (
    KeyManagementService as CoreKeyManagementService,
)
from tripsage_core.services.business.key_management_service import (
    get_key_management_service as get_core_key_management_service,
)

logger = logging.getLogger(__name__)


class KeyManagementService:
    """
    API key management service that delegates to core business services.

    This service acts as a façade, handling:
    - Model adaptation between API and core models
    - API-specific error handling
    - FastAPI dependency integration
    """

    def __init__(
        self, core_key_management_service: Optional[CoreKeyManagementService] = None
    ):
        """
        Initialize the API key management service.

        Args:
            core_key_management_service: Core key management service
        """
        self.core_key_management_service = core_key_management_service

    async def _get_core_key_management_service(self) -> CoreKeyManagementService:
        """Get or create core key management service instance."""
        if self.core_key_management_service is None:
            self.core_key_management_service = await get_core_key_management_service()
        return self.core_key_management_service

    async def create_api_key(
        self, user_id: str, request: ApiKeyCreate
    ) -> ApiKeyResponse:
        """Create a new API key.

        Args:
            user_id: User ID
            request: API key creation request

        Returns:
            Created API key response

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If creation fails
        """
        try:
            logger.info(f"Creating API key for user: {user_id}")

            # Adapt API request to core model
            core_request = self._adapt_api_key_create_request(request)

            # Create API key via core service
            core_service = await self._get_core_key_management_service()
            core_response = await core_service.create_api_key(user_id, core_request)

            # Adapt core response to API model
            return self._adapt_api_key_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"API key creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating API key: {str(e)}")
            raise ServiceError("API key creation failed") from e

    async def list_api_keys(self, user_id: str) -> List[ApiKeyResponse]:
        """List API keys for a user.

        Args:
            user_id: User ID

        Returns:
            List of API keys

        Raises:
            ServiceError: If listing fails
        """
        try:
            logger.info(f"Listing API keys for user: {user_id}")

            # List API keys via core service
            core_service = await self._get_core_key_management_service()
            core_keys = await core_service.list_api_keys(user_id)

            # Adapt core response to API model
            return [self._adapt_api_key_response(key) for key in core_keys]

        except Exception as e:
            logger.error(f"Failed to list API keys: {str(e)}")
            raise ServiceError("Failed to list API keys") from e

    async def get_api_key(self, user_id: str, key_id: str) -> Optional[ApiKeyResponse]:
        """Get a specific API key.

        Args:
            user_id: User ID
            key_id: API key ID

        Returns:
            API key response if found, None otherwise

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting API key {key_id} for user: {user_id}")

            # Get API key via core service
            core_service = await self._get_core_key_management_service()
            core_response = await core_service.get_api_key(user_id, key_id)

            if core_response is None:
                return None

            # Adapt core response to API model
            return self._adapt_api_key_response(core_response)

        except Exception as e:
            logger.error(f"Failed to get API key: {str(e)}")
            raise ServiceError("Failed to get API key") from e

    async def update_api_key(
        self, user_id: str, key_id: str, updates: Dict
    ) -> Optional[ApiKeyResponse]:
        """Update an API key.

        Args:
            user_id: User ID
            key_id: API key ID
            updates: Fields to update

        Returns:
            Updated API key if successful, None if key not found

        Raises:
            ValidationError: If update data is invalid
            ServiceError: If update fails
        """
        try:
            logger.info(f"Updating API key {key_id} for user: {user_id}")

            # Update API key via core service
            core_service = await self._get_core_key_management_service()
            core_response = await core_service.update_api_key(user_id, key_id, updates)

            if core_response is None:
                return None

            # Adapt core response to API model
            return self._adapt_api_key_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"API key update failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating API key: {str(e)}")
            raise ServiceError("API key update failed") from e

    async def delete_api_key(self, user_id: str, key_id: str) -> bool:
        """Delete an API key.

        Args:
            user_id: User ID
            key_id: API key ID

        Returns:
            True if deleted successfully

        Raises:
            ServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting API key {key_id} for user: {user_id}")

            # Delete API key via core service
            core_service = await self._get_core_key_management_service()
            return await core_service.delete_api_key(user_id, key_id)

        except Exception as e:
            logger.error(f"Failed to delete API key: {str(e)}")
            raise ServiceError("Failed to delete API key") from e

    async def rotate_api_key(
        self, user_id: str, key_id: str, request: ApiKeyRotateRequest
    ) -> ApiKeyResponse:
        """Rotate an API key.

        Args:
            user_id: User ID
            key_id: API key ID
            request: Rotation request

        Returns:
            New API key response

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If rotation fails
        """
        try:
            logger.info(f"Rotating API key {key_id} for user: {user_id}")

            # Rotate API key via core service
            core_service = await self._get_core_key_management_service()
            core_response = await core_service.rotate_api_key(
                user_id, key_id, request.preserve_access
            )

            # Adapt core response to API model
            return self._adapt_api_key_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"API key rotation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error rotating API key: {str(e)}")
            raise ServiceError("API key rotation failed") from e

    async def validate_api_key(
        self, request: ApiKeyValidateRequest
    ) -> ApiKeyValidateResponse:
        """Validate an API key.

        Args:
            request: Validation request

        Returns:
            Validation response

        Raises:
            ServiceError: If validation fails
        """
        try:
            logger.info("Validating API key")

            # Validate API key via core service
            core_service = await self._get_core_key_management_service()
            core_response = await core_service.validate_api_key(
                request.api_key, request.service
            )

            # Adapt core response to API model
            return self._adapt_api_key_validate_response(core_response)

        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}")
            raise ServiceError("API key validation failed") from e

    async def get_key_usage_stats(self, user_id: str, key_id: str) -> Dict:
        """Get usage statistics for an API key.

        Args:
            user_id: User ID
            key_id: API key ID

        Returns:
            Usage statistics

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting usage stats for API key {key_id}")

            # Get usage stats via core service
            core_service = await self._get_core_key_management_service()
            return await core_service.get_key_usage_stats(user_id, key_id)

        except Exception as e:
            logger.error(f"Failed to get key usage stats: {str(e)}")
            raise ServiceError("Failed to get key usage stats") from e

    def _adapt_api_key_create_request(self, request: ApiKeyCreate) -> dict:
        """Adapt API key create request to core model."""
        return {
            "name": request.name,
            "service": request.service,
            "key_value": request.key_value,
            "description": getattr(request, "description", None),
            "permissions": getattr(request, "permissions", None),
            "expires_at": getattr(request, "expires_at", None),
        }

    def _adapt_api_key_response(self, core_response) -> ApiKeyResponse:
        """Adapt core API key response to API model."""
        return ApiKeyResponse(
            id=core_response.get("id", ""),
            user_id=core_response.get("user_id", ""),
            name=core_response.get("name", ""),
            service=core_response.get("service", ""),
            key_preview=core_response.get("key_preview", ""),
            description=core_response.get("description"),
            permissions=core_response.get("permissions", []),
            is_active=core_response.get("is_active", True),
            created_at=core_response.get("created_at", ""),
            updated_at=core_response.get("updated_at", ""),
            expires_at=core_response.get("expires_at"),
            last_used_at=core_response.get("last_used_at"),
            usage_count=core_response.get("usage_count", 0),
        )

    def _adapt_api_key_validate_response(self, core_response) -> ApiKeyValidateResponse:
        """Adapt core API key validate response to API model."""
        return ApiKeyValidateResponse(
            valid=core_response.get("valid", False),
            key_id=core_response.get("key_id"),
            user_id=core_response.get("user_id"),
            service=core_response.get("service"),
            permissions=core_response.get("permissions", []),
            expires_at=core_response.get("expires_at"),
            error_message=core_response.get("error_message"),
        )


# Module-level dependency annotation
_core_key_management_service_dep = Depends(get_core_key_management_service)


# Dependency function for FastAPI
async def get_key_management_service(
    core_key_management_service: CoreKeyManagementService = (
        _core_key_management_service_dep
    ),
) -> KeyManagementService:
    """
    Get key management service instance for dependency injection.

    Args:
        core_key_management_service: Core key management service

    Returns:
        KeyManagementService instance
    """
    return KeyManagementService(core_key_management_service=core_key_management_service)
