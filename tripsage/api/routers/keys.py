"""API key management endpoints for the TripSage API.

This module provides endpoints for API key management, including BYOK (Bring Your Own Key)
functionality for user-provided API keys.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, status

from tripsage.api.middlewares.auth import get_current_user
from tripsage.api.models.api_key import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyRotateRequest,
    ApiKeyValidateRequest,
    ApiKeyValidateResponse,
)
from tripsage.api.services.key import KeyService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=List[ApiKeyResponse],
    summary="List API keys",
)
async def list_keys(
    user_id: str = Depends(get_current_user),
    key_service: KeyService = Depends(),
):
    """List all API keys for the current user.
    
    Args:
        user_id: Current user ID
        key_service: Key service for database operations
        
    Returns:
        List of API keys
    """
    return await key_service.list_keys(user_id)


@router.post(
    "",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
)
async def create_key(
    key_data: ApiKeyCreate,
    user_id: str = Depends(get_current_user),
    key_service: KeyService = Depends(),
):
    """Create a new API key.
    
    Args:
        key_data: API key data
        user_id: Current user ID
        key_service: Key service for database operations
        
    Returns:
        The created API key
        
    Raises:
        HTTPException: If the key is invalid
    """
    try:
        # Validate the API key with the service
        validation = await key_service.validate_key(
            key_data.key, key_data.service
        )
        
        if not validation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid API key for {key_data.service}: {validation.message}",
            )
        
        # Create the API key
        return await key_service.create_key(user_id, key_data)
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}",
        )


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an API key",
)
async def delete_key(
    key_id: str = Path(..., description="The API key ID"),
    user_id: str = Depends(get_current_user),
    key_service: KeyService = Depends(),
):
    """Delete an API key.
    
    Args:
        key_id: The API key ID
        user_id: Current user ID
        key_service: Key service for database operations
        
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
    
    if key.user_id != user_id:
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
    key_service: KeyService = Depends(),
):
    """Validate an API key with the service.
    
    Args:
        key_data: API key data
        key_service: Key service for database operations
        
    Returns:
        Validation result
    """
    return await key_service.validate_key(key_data.key, key_data.service)


@router.post(
    "/{key_id}/rotate",
    response_model=ApiKeyResponse,
    summary="Rotate an API key",
)
async def rotate_key(
    key_data: ApiKeyRotateRequest,
    key_id: str = Path(..., description="The API key ID"),
    user_id: str = Depends(get_current_user),
    key_service: KeyService = Depends(),
):
    """Rotate an API key.
    
    Args:
        key_data: New API key data
        key_id: The API key ID
        user_id: Current user ID
        key_service: Key service for database operations
        
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
    
    if key.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to rotate this API key",
        )
    
    # Validate the new key
    validation = await key_service.validate_key(key_data.new_key, key.service)
    
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid API key for {key.service}: {validation.message}",
        )
    
    # Rotate the key
    return await key_service.rotate_key(key_id, key_data.new_key)