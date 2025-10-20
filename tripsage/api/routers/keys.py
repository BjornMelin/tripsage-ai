"""API key management endpoints for the TripSage API.

This module provides endpoints for API key management, including BYOK (Bring Your
Own Key) functionality for user-provided API keys.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from tripsage.api.core.dependencies import (
    ApiKeyServiceDep,
    get_principal_id,
    require_principal,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.api_keys import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyRotateRequest,
    ApiKeyValidateRequest,
    ApiKeyValidateResponse,
)
from tripsage_core.services.infrastructure.key_monitoring_service import (
    KeyMonitoringService,
    get_key_health_metrics,
)


router = APIRouter()
logger = logging.getLogger(__name__)


def get_monitoring_service() -> KeyMonitoringService:
    """Dependency provider for the KeyMonitoringService."""
    return KeyMonitoringService()


@router.get(
    "",
    response_model=list[ApiKeyResponse],
    summary="List API keys",
)
async def list_keys(
    key_service: ApiKeyServiceDep,
    principal: Principal = Depends(require_principal),
):
    """List all API keys for the current user.

    Args:
        principal: Current authenticated principal
        key_service: Injected key service

    Returns:
        List of API keys
    """
    user_id = get_principal_id(principal)
    return await key_service.list_user_keys(user_id)


@router.post(
    "",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
)
async def create_key(
    key_data: ApiKeyCreate,
    key_service: ApiKeyServiceDep,
    principal: Principal = Depends(require_principal),
):
    """Create a new API key.

    Args:
        key_data: API key data
        principal: Current authenticated principal
        key_service: Injected key service

    Returns:
        The created API key

    Raises:
        HTTPException: If the key is invalid
    """
    try:
        # Validate the API key with the service
        validation = await key_service.validate_key(key_data.key, key_data.service)

        if not validation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid API key for {key_data.service}: {validation.message}",
            )

        # Create the API key
        user_id = get_principal_id(principal)
        return await key_service.create_key(user_id, key_data)
    except Exception as e:
        logger.exception(f"Error creating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {e!s}",
        ) from e


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an API key",
)
async def delete_key(
    key_service: ApiKeyServiceDep,
    principal: Principal = Depends(require_principal),
    key_id: str = Path(..., description="The API key ID"),
):
    """Delete an API key.

    Args:
        key_id: The API key ID
        principal: Current authenticated principal

    Raises:
        HTTPException: If the key is not found or does not belong to the user
    """
    # Check if the key exists and belongs to the user
    key = await key_service.get_key(key_id)

    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    user_id = get_principal_id(principal)
    if key["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this API key",
        )

    # Delete the key
    await key_service.delete_key(key_id)


@router.post(
    "/validate",
    response_model=ApiKeyValidateResponse,
    summary="Validate an API key",
)
async def validate_key(
    key_data: ApiKeyValidateRequest,
    key_service: ApiKeyServiceDep,
    principal: Principal = Depends(require_principal),
):
    """Validate an API key with the service.

    Args:
        key_data: API key data
        principal: Current authenticated principal

    Returns:
        Validation result
    """
    user_id = get_principal_id(principal)
    return await key_service.validate_key(key_data.key, key_data.service, user_id)


@router.post(
    "/{key_id}/rotate",
    response_model=ApiKeyResponse,
    summary="Rotate an API key",
)
async def rotate_key(
    key_data: ApiKeyRotateRequest,
    key_service: ApiKeyServiceDep,
    principal: Principal = Depends(require_principal),
    key_id: str = Path(..., description="The API key ID"),
):
    """Rotate an API key.

    Args:
        key_data: New API key data
        key_id: The API key ID
        principal: Current authenticated principal

    Returns:
        The updated API key

    Raises:
        HTTPException: If the key is not found or does not belong to the user
    """
    # Check if the key exists and belongs to the user
    key = await key_service.get_key(key_id)

    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    user_id = get_principal_id(principal)
    if key["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to rotate this API key",
        )

    # Validate the new key
    validation = await key_service.validate_key(
        key_data.new_key, key["service"], user_id
    )

    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid API key for {key['service']}: {validation.message}",
        )

    # Rotate the key
    return await key_service.rotate_key(key_id, key_data.new_key, user_id)


@router.get(
    "/metrics",
    response_model=dict[str, Any],
    summary="Get API key metrics",
)
async def get_metrics(
    principal: Principal = Depends(require_principal),
):
    """Get API key health metrics.

    Args:
        principal: Current authenticated principal

    Returns:
        Key health metrics
    """
    # Only allow admin users to access metrics
    # This would normally check user roles, but for now we'll use a simple approach
    return await get_key_health_metrics()


@router.get(
    "/audit",
    response_model=list[dict[str, Any]],
    summary="Get API key audit log",
)
async def get_audit_log(
    principal: Principal = Depends(require_principal),
    limit: int = Query(100, ge=1, le=1000),
    monitoring_service: KeyMonitoringService = Depends(get_monitoring_service),
):
    """Get API key audit log for a user.

    Args:
        principal: Current authenticated principal
        limit: Maximum number of entries to return

    Returns:
        List of audit log entries
    """
