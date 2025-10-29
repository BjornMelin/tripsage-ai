"""API key management endpoints for the TripSage API.

This module provides endpoints for API key management, including BYOK (Bring Your
Own Key) functionality for user-provided API keys.
"""

import logging
import re
from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)

from tripsage.api.core.config import get_settings
from tripsage.api.core.dependencies import (
    AdminPrincipalDep,
    ApiKeyServiceDep,
    KeyMonitoringServiceDep,
    RequiredPrincipalDep,
    get_principal_id,
)
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

_SERVICE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_DISALLOWED_NAME_CHARS = set("*()|&`;$")
_SUSPICIOUS_SERVICE_SEQUENCES = (
    "../",
    "..\\",
    "%2f..",
    "..%2f",
    "%2e%2e%2f",
    "%2e%2f",
)
_MAX_DESCRIPTION_LENGTH = 4096
_MAX_KEY_LENGTH = 1024
_ALLOWED_ORIGINS = frozenset(origin.lower() for origin in get_settings().cors_origins)


def _contains_control_chars(value: str) -> bool:
    """Return True when the input string holds ASCII control characters."""
    return any(ord(char) < 32 and char not in ("\t", "\n", "\r") for char in value)


def _is_origin_allowed(request: Request) -> bool:
    """Return True when the request origin is empty or on the allow-list."""
    origin_header = request.headers.get("Origin")
    return not origin_header or origin_header.lower() in _ALLOWED_ORIGINS


def _enforce_allowed_origin(request: Request) -> None:
    """Reject requests from disallowed origins."""
    if not _is_origin_allowed(request):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Origin not allowed for API key operations.",
        )


def _validate_service_identifier(service: str) -> None:
    """Validate the service identifier for traversal and format issues."""
    lowered = service.lower()
    if _contains_control_chars(service):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Service contains control characters.",
        )
    if not _SERVICE_PATTERN.match(lowered):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid service identifier.",
        )
    if any(sequence in lowered for sequence in _SUSPICIOUS_SERVICE_SEQUENCES):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Potential path traversal detected in service identifier.",
        )


def _validate_create_payload(payload: ApiKeyCreate) -> None:
    """Enforce payload constraints to mitigate injection vectors."""
    if _contains_control_chars(payload.name):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name contains control characters.",
        )
    if any(char in payload.name for char in _DISALLOWED_NAME_CHARS):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name contains invalid characters.",
        )
    _validate_service_identifier(payload.service)
    if len(payload.key) > _MAX_KEY_LENGTH:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="API key value is too large.",
        )
    if payload.description and len(payload.description) > _MAX_DESCRIPTION_LENGTH:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Description exceeds maximum length.",
        )


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
    principal: RequiredPrincipalDep,
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
    suspicious_params = {"key", "service", "name", "description"}
    if any(param in request.query_params for param in suspicious_params):
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="GET cannot be used for state-changing API key operations.",
        )
    user_id = get_principal_id(principal)
    return await key_service.list_user_keys(user_id)


@router.options(
    "",
    include_in_schema=False,
)
async def preflight_options(request: Request) -> Response:
    """Handle CORS preflight checks for the API key collection endpoint."""
    if not _is_origin_allowed(request):
        return Response(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
    response = Response(status_code=status.HTTP_200_OK)
    origin_header = request.headers.get("Origin")
    if origin_header:
        response.headers["Access-Control-Allow-Origin"] = origin_header
    response.headers.update(
        {
            "Allow": "GET,POST,OPTIONS",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-API-Key",
        }
    )
    return response


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
    principal: RequiredPrincipalDep,
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
    _enforce_allowed_origin(request)
    user_id = get_principal_id(principal)
    _validate_create_payload(key_data)
    try:
        # Validate the API key with the service
        validation = await key_service.validate_key(
            key_data.key,
            key_data.service,
            user_id,
        )

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
    principal: RequiredPrincipalDep,
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
    _enforce_allowed_origin(request)
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
    principal: RequiredPrincipalDep,
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
    _enforce_allowed_origin(request)
    if _contains_control_chars(key_data.key):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="API key contains control characters.",
        )
    if len(key_data.key) > _MAX_KEY_LENGTH:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="API key value is too large.",
        )
    _validate_service_identifier(key_data.service)
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
    principal: RequiredPrincipalDep,
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
    _enforce_allowed_origin(request)
    if len(key_data.new_key) > _MAX_KEY_LENGTH:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="API key value is too large.",
        )
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
    principal: AdminPrincipalDep,
):
    """Get API key health metrics.

    Args:
        request: Raw HTTP request (required by SlowAPI for headers)
        response: Raw HTTP response (required by SlowAPI for headers)
        principal: Current authenticated principal

    Returns:
        Key health metrics
    """
    _ = principal  # Enforce admin gating (principal is validated upstream)
    metrics = await get_key_health_metrics()

    if metrics.error:
        return metrics.model_dump(mode="json")

    user_distribution: list[dict[str, int | str]] = [
        {"user_id": entry.user_id, "count": int(entry.count)}
        for entry in metrics.user_count
    ]

    total_users = len(user_distribution)
    total_keys: int = sum(int(details["count"]) for details in user_distribution)
    average = (total_keys / total_users) if total_users else 0.0

    payload = metrics.model_dump(mode="json", exclude={"user_count"})
    payload["user_distribution"] = {
        "unique_users": total_users,
        "total_keys": total_keys,
        "avg_keys_per_user": average,
        "distribution": user_distribution,
    }

    return payload


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
    principal: AdminPrincipalDep,
    limit: int = Query(20, ge=1, le=100),
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
    user_id = get_principal_id(principal)
    entries = await monitoring_service.get_user_operations(user_id, limit)

    def _mask_key_id(key_id: str) -> str:
        identifier = key_id
        if len(identifier) <= 8:
            return "***"
        return f"{identifier[:4]}***{identifier[-4:]}"

    sanitized: list[dict[str, Any]] = []
    for entry in entries:
        record: dict[str, Any] = {
            "timestamp": entry.timestamp.isoformat(),
            "operation": entry.operation.value,
            "service": entry.service,
            "success": entry.success,
            "metadata": entry.metadata,
        }

        if entry.key_id:
            record["key_id"] = _mask_key_id(entry.key_id)

        sanitized.append(record)

    return sanitized
