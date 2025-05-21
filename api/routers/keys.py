"""
Router for managing user-provided API keys (BYOK functionality).

This module provides endpoints for managing API keys for external services,
allowing users to bring their own keys for services like OpenAI, weather APIs, etc.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.core.config import settings
from api.core.exceptions import KeyValidationError
from api.deps import get_current_user
from api.services.key_service import KeyService

logger = logging.getLogger(__name__)

router = APIRouter()

_key_service_singleton = KeyService()


def get_key_service() -> KeyService:
    """Dependency provider for the KeyService singleton."""
    return _key_service_singleton


# Models
class KeyResponse(BaseModel):
    """Response model for API key information."""

    service: str = Field(..., description="Service name")
    has_key: bool = Field(..., description="Whether a key is configured")
    is_valid: bool = Field(..., description="Whether the key is valid")
    last_validated: Optional[str] = Field(
        None, description="When the key was last validated"
    )
    last_used: Optional[str] = Field(None, description="When the key was last used")


class AllKeysResponse(BaseModel):
    """Response model for all API keys."""

    keys: Dict[str, KeyResponse] = Field(..., description="API keys by service")
    supported_services: List[str] = Field(..., description="List of supported services")


class AddKeyRequest(BaseModel):
    """Request model for adding an API key."""

    service: str = Field(..., description="Service name")
    api_key: str = Field(..., description="API key value")
    save: bool = Field(True, description="Whether to save the key for future use")


class AddKeyResponse(BaseModel):
    """Response model for adding an API key."""

    service: str = Field(..., description="Service name")
    is_valid: bool = Field(..., description="Whether the key is valid")
    message: str = Field(..., description="Status message")


class DeleteKeyResponse(BaseModel):
    """Response model for deleting an API key."""

    service: str = Field(..., description="Service name")
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Status message")


class ValidateKeyResponse(BaseModel):
    """Response model for validating an API key."""

    service: str = Field(..., description="Service name")
    is_valid: bool = Field(..., description="Whether the key is valid")
    message: str = Field(..., description="Status message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional validation details"
    )


# Routes
@router.get("/", response_model=AllKeysResponse)
async def get_all_keys(
    current_user: dict = Depends(get_current_user),
    key_service: KeyService = Depends(get_key_service),
):
    """Get all configured API keys for the current user.

    Returns:
        Dictionary of service names to key information
    """
    user_id = current_user["id"]
    keys = await key_service.get_all_keys(user_id)

    return {
        "keys": keys,
        "supported_services": settings.byok_services,
    }


@router.get("/{service}", response_model=KeyResponse)
async def get_key(
    service: str,
    current_user: dict = Depends(get_current_user),
    key_service: KeyService = Depends(get_key_service),
):
    """Get information about a specific API key.

    Args:
        service: The service name

    Returns:
        Key information
    """
    if service not in settings.byok_services:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service {service} is not supported for BYOK",
        )

    user_id = current_user["id"]
    key_info = await key_service.get_key(user_id, service)

    if key_info is None:
        return KeyResponse(
            service=service,
            has_key=False,
            is_valid=False,
        )

    return key_info


@router.post("/", response_model=AddKeyResponse)
async def add_key(
    request: AddKeyRequest,
    current_user: dict = Depends(get_current_user),
    key_service: KeyService = Depends(get_key_service),
):
    """Add or update an API key.

    Args:
        request: Add key request

    Returns:
        Status of the operation
    """
    if request.service not in settings.byok_services:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service {request.service} is not supported for BYOK",
        )

    user_id = current_user["id"]

    try:
        # Validate the key
        validation = await key_service.validate_key(request.service, request.api_key)

        if validation["is_valid"]:
            # Save the key if requested
            if request.save:
                await key_service.save_key(user_id, request.service, request.api_key)

            return AddKeyResponse(
                service=request.service,
                is_valid=True,
                message="API key is valid and has been saved",
            )
        else:
            raise KeyValidationError(
                message=validation["message"], details={"service": request.service}
            )

    except KeyValidationError as e:
        return AddKeyResponse(
            service=request.service,
            is_valid=False,
            message=str(e),
        )


@router.delete("/{service}", response_model=DeleteKeyResponse)
async def delete_key(
    service: str,
    current_user: dict = Depends(get_current_user),
    key_service: KeyService = Depends(get_key_service),
):
    """Delete an API key.

    Args:
        service: The service name

    Returns:
        Status of the operation
    """
    if service not in settings.byok_services:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service {service} is not supported for BYOK",
        )

    user_id = current_user["id"]
    success = await key_service.delete_key(user_id, service)

    return DeleteKeyResponse(
        service=service,
        success=success,
        message="API key has been deleted" if success else "No API key was found",
    )


@router.post("/validate", response_model=ValidateKeyResponse)
async def validate_key(
    request: AddKeyRequest,
    key_service: KeyService = Depends(get_key_service),
):
    """Validate an API key without saving it.

    Args:
        request: Add key request

    Returns:
        Validation result
    """
    if request.service not in settings.byok_services:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service {request.service} is not supported for BYOK",
        )

    try:
        validation = await key_service.validate_key(request.service, request.api_key)

        return ValidateKeyResponse(
            service=request.service,
            is_valid=validation["is_valid"],
            message=validation["message"],
            details=validation.get("details"),
        )

    except Exception as e:
        logger.exception(f"Error validating key for {request.service}: {str(e)}")

        return ValidateKeyResponse(
            service=request.service,
            is_valid=False,
            message=f"Error validating key: {str(e)}",
        )
