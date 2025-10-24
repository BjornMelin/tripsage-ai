"""API key management endpoints for the TripSage API.

This module provides endpoints for API key management, including BYOK (Bring Your
Own Key) functionality for user-provided API keys.
"""

import logging
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)

from tripsage.api.core.dependencies import (
    ApiKeyServiceDep,
    KeyMonitoringServiceDep,
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
from tripsage_core.observability.otel import (
    http_route_attr_fn,
    record_histogram,
    trace_span,
)
from tripsage_core.services.business.api_key_service import ValidationStatus
from tripsage_core.services.infrastructure.key_monitoring_service import (
    get_key_health_metrics,
)


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=list[ApiKeyResponse],
    summary="List API keys",
)
@trace_span(name="api.keys.list")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def list_keys(
    request: Request,
    response: Response,
    key_service: ApiKeyServiceDep,
    principal: Principal = Depends(require_principal),
):
    """List all API keys for the current user.

    Args:
        request: Raw HTTP request (required by SlowAPI for headers)
        response: Raw HTTP response (required by SlowAPI for headers)
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
@trace_span(name="api.keys.create")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def create_key(
    request: Request,
    response: Response,
    key_data: ApiKeyCreate,
    key_service: ApiKeyServiceDep,
    principal: Principal = Depends(require_principal),
):
    """Create a new API key.

    Args:
        request: Raw HTTP request (required by SlowAPI for headers)
        response: Raw HTTP response (required by SlowAPI for headers)
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
            validation_status = getattr(validation, "status", None)
            if validation_status == ValidationStatus.RATE_LIMITED:
                status_code_value = status.HTTP_429_TOO_MANY_REQUESTS
            elif validation_status == ValidationStatus.SERVICE_ERROR:
                status_code_value = status.HTTP_500_INTERNAL_SERVER_ERROR
            else:
                status_code_value = status.HTTP_400_BAD_REQUEST
            raise HTTPException(
                status_code=status_code_value,
                detail=f"Invalid API key for {key_data.service}: {validation.message}",
            )

        # Create the API key
        user_id = get_principal_id(principal)
        return await key_service.create_key(user_id, key_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creating API key")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {e!s}",
        ) from e


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an API key",
)
@trace_span(name="api.keys.delete")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def delete_key(
    request: Request,
    response: Response,
    key_service: ApiKeyServiceDep,
    principal: Principal = Depends(require_principal),
    key_id: str = Path(..., description="The API key ID"),
):
    """Delete an API key.

    Args:
        request: Raw HTTP request (required by SlowAPI for headers)
        response: Raw HTTP response (required by SlowAPI for headers)
        key_service: Injected key service
        principal: Current authenticated principal
        key_id: The API key ID

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
@trace_span(name="api.keys.validate")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def validate_key(
    request: Request,
    response: Response,
    key_data: ApiKeyValidateRequest,
    key_service: ApiKeyServiceDep,
    principal: Principal = Depends(require_principal),
):
    """Validate an API key with the service.

    Args:
        request: Raw HTTP request (required by SlowAPI for headers)
        response: Raw HTTP response (required by SlowAPI for headers)
        key_data: API key data
        principal: Current authenticated principal
        key_service: Injected key service

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
@trace_span(name="api.keys.rotate")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def rotate_key(  # pylint: disable=too-many-positional-arguments
    request: Request,
    response: Response,
    key_data: ApiKeyRotateRequest,
    key_service: ApiKeyServiceDep,
    principal: Principal = Depends(require_principal),
    key_id: str = Path(..., description="The API key ID"),
):
    """Rotate an API key.

    Args:
        request: Raw HTTP request (required by SlowAPI for headers)
        response: Raw HTTP response (required by SlowAPI for headers)
        key_data: New API key data
        key_id: The API key ID
        principal: Current authenticated principal
        key_service: Injected key service

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
@trace_span(name="api.keys.metrics")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def get_metrics(
    request: Request,
    response: Response,
    principal: Principal = Depends(require_principal),
):
    """Get API key health metrics.

    Args:
        request: Raw HTTP request (required by SlowAPI for headers)
        response: Raw HTTP response (required by SlowAPI for headers)
        principal: Current authenticated principal

    Returns:
        Key health metrics
    """
    # Only allow admin users to access metrics
    # This would normally check user roles, but for now we'll use a simple approach
    try:
        return await get_key_health_metrics()
    except Exception:  # pragma: no cover - defensive fallback
        logger.exception("Failed to retrieve API key metrics")
        return {}


@router.get(
    "/audit",
    response_model=list[dict[str, Any]],
    summary="Get API key audit log",
)
@trace_span(name="api.keys.audit")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def get_audit_log(
    request: Request,
    response: Response,
    monitoring_service: KeyMonitoringServiceDep,
    principal: Principal = Depends(require_principal),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get API key audit log for a user.

    Args:
        request: Raw HTTP request (required by SlowAPI for headers)
        response: Raw HTTP response (required by SlowAPI for headers)
        principal: Current authenticated principal
        limit: Maximum number of entries to return
        monitoring_service: Key monitoring service

    Returns:
        List of audit log entries
    """
