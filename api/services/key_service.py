"""
Service for managing user-provided API keys (BYOK functionality).

This service acts as a thin wrapper around the core key management service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import Optional

from fastapi import Depends

from api.schemas.requests.keys import (
    CreateApiKeyRequest,
    RotateApiKeyRequest,
    ValidateApiKeyRequest,
)
from api.schemas.responses.keys import (
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeyServicesStatusResponse,
    ApiKeyServiceStatusResponse,
    ApiKeyValidationResponse,
    MessageResponse,
)
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.key_management_service import (
    ApiKeyCreateRequest as CoreApiKeyCreateRequest,
)
from tripsage_core.services.business.key_management_service import (
    ApiKeyValidationResult,
)
from tripsage_core.services.business.key_management_service import (
    KeyManagementService as CoreKeyManagementService,
)
from tripsage_core.services.business.key_management_service import (
    get_key_management_service as get_core_key_management_service,
)

logger = logging.getLogger(__name__)


class KeyService:
    """
    API key management service that delegates to core business services.

    This service acts as a façade, handling:
    - Model adaptation between API and core models
    - API-specific error handling
    - FastAPI dependency integration
    """

    def __init__(
        self,
        core_key_service: Optional[CoreKeyManagementService] = None,
    ):
        """
        Initialize the API key service.

        Args:
            core_key_service: Core key management service
        """
        self.core_key_service = core_key_service

    async def _get_core_key_service(self) -> CoreKeyManagementService:
        """Get or create core key service instance."""
        if self.core_key_service is None:
            self.core_key_service = await get_core_key_management_service()
        return self.core_key_service

    async def create_api_key(
        self, user_id: str, request: CreateApiKeyRequest
    ) -> ApiKeyResponse:
        """
        Create a new API key.

        Args:
            user_id: User ID
            request: API key creation request

        Returns:
            Created API key information

        Raises:
            ValidationError: If key data is invalid
            ServiceError: If creation fails
        """
        try:
            # Adapt API request to core model
            core_request = CoreApiKeyCreateRequest(
                name=request.name,
                service=request.service,
                key_value=request.key_value,
                description=request.description,
                expires_at=request.expires_at,
            )

            # Create key via core service
            core_key_service = await self._get_core_key_service()
            core_response = await core_key_service.create_api_key(user_id, core_request)

            # Adapt core response to API model
            return self._adapt_api_key_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"API key creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating API key: {str(e)}")
            raise ServiceError("Failed to create API key") from e

    async def get_user_api_keys(self, user_id: str) -> ApiKeyListResponse:
        """
        Get all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            List of user's API keys
        """
        try:
            # Get keys via core service
            core_key_service = await self._get_core_key_service()
            core_keys = await core_key_service.get_user_api_keys(user_id)

            # Adapt core response to API model
            api_keys = [self._adapt_api_key_response(key) for key in core_keys]

            return ApiKeyListResponse(
                keys=api_keys,
                total=len(api_keys),
            )

        except Exception as e:
            logger.error(f"Failed to get user API keys: {str(e)}")
            return ApiKeyListResponse(keys=[], total=0)

    async def get_api_key(self, user_id: str, key_id: str) -> Optional[ApiKeyResponse]:
        """
        Get a specific API key.

        Args:
            user_id: User ID
            key_id: API key ID

        Returns:
            API key information or None if not found
        """
        try:
            # Get all user keys and find the specific one
            # Note: Core service doesn't have get_single_key method yet
            core_key_service = await self._get_core_key_service()
            core_keys = await core_key_service.get_user_api_keys(user_id)

            for key in core_keys:
                if key.id == key_id:
                    return self._adapt_api_key_response(key)

            return None

        except Exception as e:
            logger.error(f"Failed to get API key: {str(e)}")
            return None

    async def get_service_status(
        self, user_id: str, service: str
    ) -> ApiKeyServiceStatusResponse:
        """
        Get API key status for a specific service.

        Args:
            user_id: User ID
            service: Service name

        Returns:
            Service API key status
        """
        try:
            # Get key for service via core service
            core_key_service = await self._get_core_key_service()
            key_value = await core_key_service.get_api_key_for_service(user_id, service)

            if key_value is None:
                return ApiKeyServiceStatusResponse(
                    service=service,
                    has_key=False,
                    is_valid=None,
                    last_validated=None,
                    last_used=None,
                )

            # Get key details from user keys
            core_keys = await core_key_service.get_user_api_keys(user_id)
            service_key = next((k for k in core_keys if k.service == service), None)

            if service_key:
                return ApiKeyServiceStatusResponse(
                    service=service,
                    has_key=True,
                    is_valid=service_key.is_valid,
                    last_validated=service_key.last_validated,
                    last_used=service_key.last_used,
                )

            return ApiKeyServiceStatusResponse(
                service=service,
                has_key=True,
                is_valid=None,
                last_validated=None,
                last_used=None,
            )

        except Exception as e:
            logger.error(f"Failed to get service status: {str(e)}")
            return ApiKeyServiceStatusResponse(
                service=service,
                has_key=False,
                is_valid=None,
                last_validated=None,
                last_used=None,
            )

    async def get_all_services_status(
        self, user_id: str
    ) -> ApiKeyServicesStatusResponse:
        """
        Get API key status for all services.

        Args:
            user_id: User ID

        Returns:
            Status for all services
        """
        try:
            # Define all supported services
            all_services = [
                "openai",
                "weather",
                "flights",
                "googlemaps",
                "accommodation",
                "webcrawl",
                "calendar",
                "email",
            ]

            # Get status for each service
            services_status = {}
            for service in all_services:
                status = await self.get_service_status(user_id, service)
                services_status[service] = status

            return ApiKeyServicesStatusResponse(services=services_status)

        except Exception as e:
            logger.error(f"Failed to get all services status: {str(e)}")
            return ApiKeyServicesStatusResponse(services={})

    async def validate_api_key(
        self, user_id: str, key_id: str
    ) -> ApiKeyValidationResponse:
        """
        Validate an API key.

        Args:
            user_id: User ID
            key_id: API key ID

        Returns:
            Validation result

        Raises:
            ValidationError: If validation fails
        """
        try:
            # Validate via core service
            core_key_service = await self._get_core_key_service()
            core_result = await core_key_service.validate_api_key(key_id, user_id)

            # Adapt core response to API model
            return self._adapt_validation_response(core_result)

        except ValidationError as e:
            logger.error(f"API key validation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error validating API key: {str(e)}")
            raise ValidationError("Validation failed") from e

    async def validate_key_value(
        self, request: ValidateApiKeyRequest
    ) -> ApiKeyValidationResponse:
        """
        Validate an API key value without storing it.

        Args:
            request: Validation request

        Returns:
            Validation result
        """
        try:
            # Use core service's internal validation method
            core_key_service = await self._get_core_key_service()
            core_result = await core_key_service._validate_api_key(
                request.service, request.key_value
            )

            # Adapt core response to API model
            return self._adapt_validation_response(core_result)

        except Exception as e:
            logger.error(f"API key value validation failed: {str(e)}")
            from datetime import datetime, timezone

            return ApiKeyValidationResponse(
                is_valid=False,
                service=request.service,
                message=f"Validation error: {str(e)}",
                details={"error": str(e)},
                validated_at=datetime.now(timezone.utc),
            )

    async def rotate_api_key(
        self, user_id: str, key_id: str, request: RotateApiKeyRequest
    ) -> ApiKeyResponse:
        """
        Rotate an API key with a new value.

        Args:
            user_id: User ID
            key_id: API key ID
            request: Rotation request

        Returns:
            Updated API key information

        Raises:
            ValidationError: If rotation fails
        """
        try:
            # Rotate via core service
            core_key_service = await self._get_core_key_service()
            core_response = await core_key_service.rotate_api_key(
                key_id, user_id, request.new_key_value
            )

            # Adapt core response to API model
            return self._adapt_api_key_response(core_response)

        except ValidationError as e:
            logger.error(f"API key rotation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error rotating API key: {str(e)}")
            raise ValidationError("Rotation failed") from e

    async def delete_api_key(self, user_id: str, key_id: str) -> MessageResponse:
        """
        Delete an API key.

        Args:
            user_id: User ID
            key_id: API key ID

        Returns:
            Success message

        Raises:
            ValidationError: If deletion fails
        """
        try:
            # Delete via core service
            core_key_service = await self._get_core_key_service()
            success = await core_key_service.delete_api_key(key_id, user_id)

            if not success:
                raise ValidationError("API key not found or deletion failed")

            return MessageResponse(
                message="API key deleted successfully",
                success=True,
            )

        except ValidationError as e:
            logger.error(f"API key deletion failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting API key: {str(e)}")
            raise ValidationError("Deletion failed") from e

    def _adapt_api_key_response(self, core_key) -> ApiKeyResponse:
        """
        Adapt core API key response to API model.

        Args:
            core_key: Core API key response

        Returns:
            API key response
        """
        return ApiKeyResponse(
            id=core_key.id,
            name=core_key.name,
            service=core_key.service,
            description=core_key.description,
            is_valid=core_key.is_valid,
            created_at=core_key.created_at,
            updated_at=core_key.updated_at,
            expires_at=core_key.expires_at,
            last_used=core_key.last_used,
            last_validated=core_key.last_validated,
            usage_count=core_key.usage_count,
        )

    def _adapt_validation_response(
        self, core_result: ApiKeyValidationResult
    ) -> ApiKeyValidationResponse:
        """
        Adapt core validation result to API model.

        Args:
            core_result: Core validation result

        Returns:
            API validation response
        """
        return ApiKeyValidationResponse(
            is_valid=core_result.is_valid,
            service=core_result.service,
            message=core_result.message,
            details=core_result.details,
            validated_at=core_result.validated_at,
        )


# Module-level dependency annotation
_core_key_service_dep = Depends(get_core_key_management_service)


# Dependency function for FastAPI
async def get_key_service(
    core_key_service: CoreKeyManagementService = _core_key_service_dep,
) -> KeyService:
    """
    Get key service instance for dependency injection.

    Args:
        core_key_service: Core key management service

    Returns:
        KeyService instance
    """
    return KeyService(core_key_service=core_key_service)
