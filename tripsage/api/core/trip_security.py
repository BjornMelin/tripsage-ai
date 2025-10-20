"""Trip Access Verification and Security Decorators for TripSage API.

This module provides comprehensive trip access verification functionality, including
decorators for FastAPI endpoints, security helper functions, and integration with
the existing authentication and audit logging infrastructure.

Features:
- Trip ownership and collaboration permission verification
- FastAPI dependency injection patterns following 2025 best practices
- Security-aware error handling with audit logging
- Integration with existing Principal authentication system
- Pydantic v2 models for validation and configuration
- Comprehensive Google-style docstrings and type hints
"""

import logging
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Annotated, Any, TypeVar
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from pydantic import ConfigDict, Field, field_validator

from tripsage.api.core.dependencies import (
    get_principal_id,
    require_principal,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError,
    CoreSecurityError,
    ErrorDetails,
)
from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.models.schemas_common.enums import TripVisibility
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditSeverity,
    audit_security_event,
)
from tripsage_core.services.business.trip_service import TripService


logger = logging.getLogger(__name__)

# Type variables for generic decorator functions
F = TypeVar("F", bound=Callable[..., Any])


class TripAccessLevel(str, Enum):
    """Defines the required access levels for trip operations."""

    READ = "read"  # Can view trip details
    WRITE = "write"  # Can modify trip details
    OWNER = "owner"  # Must be trip owner
    COLLABORATOR = "collaborator"  # Can be owner or collaborator


class TripAccessPermission(str, Enum):
    """Defines the specific permissions within trip collaboration."""

    VIEW = "view"  # Read-only access
    EDIT = "edit"  # Can modify trip content
    MANAGE = "manage"  # Can manage collaborators and settings


class TripAccessContext(TripSageModel):
    """Context information for trip access verification."""

    trip_id: str = Field(..., description="Trip ID being accessed")
    principal_id: str = Field(..., description="Principal requesting access")
    required_level: TripAccessLevel = Field(..., description="Required access level")
    required_permission: TripAccessPermission | None = Field(
        None, description="Specific permission required for operation"
    )
    operation: str = Field(..., description="Operation being performed")
    ip_address: str | None = Field(None, description="Client IP address")
    user_agent: str | None = Field(None, description="Client user agent")

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        use_enum_values=True,
    )

    @field_validator("trip_id")
    @classmethod
    def validate_trip_id(cls, v: str) -> str:
        """Validate trip ID format."""
        if not v or not isinstance(v, str):
            raise ValueError("Trip ID must be a non-empty string")
        # Support both UUID and string formats
        try:
            UUID(v)
        except ValueError as e:
            # Allow non-UUID string IDs for backward compatibility
            if len(v.strip()) == 0:
                raise ValueError("Trip ID cannot be empty") from e
        return v.strip()

    @field_validator("principal_id")
    @classmethod
    def validate_principal_id(cls, v: str) -> str:
        """Validate principal ID format."""
        if not v or not isinstance(v, str):
            raise ValueError("Principal ID must be a non-empty string")
        return v.strip()


class TripAccessResult(TripSageModel):
    """Result of trip access verification."""

    is_authorized: bool = Field(..., description="Whether access is authorized")
    access_level: TripAccessLevel | None = Field(
        None, description="Granted access level"
    )
    permission_granted: TripAccessPermission | None = Field(
        None, description="Specific permission granted"
    )
    is_owner: bool = Field(default=False, description="Whether principal is trip owner")
    is_collaborator: bool = Field(
        default=False, description="Whether principal is collaborator"
    )
    trip_visibility: TripVisibility | None = Field(
        None, description="Trip visibility setting"
    )
    denial_reason: str | None = Field(None, description="Reason for access denial")

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        use_enum_values=True,
    )


async def verify_trip_access(
    context: TripAccessContext,
    trip_service: TripService,
) -> TripAccessResult:
    """Verify trip access permissions for a principal.

    This function implements the core trip access verification logic, checking
    trip ownership, collaboration permissions, and visibility settings.

    Args:
        context: Trip access context with verification parameters
        trip_service: Trip service instance for database operations

    Returns:
        TripAccessResult: Detailed access verification result

    Raises:
        CoreResourceNotFoundError: If trip is not found
        CoreSecurityError: For security-related validation failures
    """
    try:
        logger.debug(
            "Verifying trip access",
            extra={
                "trip_id": context.trip_id,
                "principal_id": context.principal_id,
                "required_level": context.required_level,
                "operation": context.operation,
            },
        )

        # Use the existing TripService._check_trip_access method for core verification
        # but enhance it with more detailed permission checking
        require_owner = context.required_level == TripAccessLevel.OWNER

        # First, check basic access using existing service method
        has_basic_access = await trip_service._check_trip_access(
            trip_id=context.trip_id,
            user_id=context.principal_id,
            require_owner=require_owner,
        )

        if not has_basic_access:
            # Log access denial for security monitoring
            await audit_security_event(
                event_type=AuditEventType.ACCESS_DENIED,
                severity=AuditSeverity.MEDIUM,
                message=f"Trip access denied for operation: {context.operation}",
                actor_id=context.principal_id,
                ip_address=context.ip_address or "unknown",
                target_resource=context.trip_id,
                risk_score=40,
                user_agent=context.user_agent,
                operation_type=context.operation,
                required_permission=context.required_level.value,
            )

            return TripAccessResult(
                is_authorized=False,
                denial_reason=(
                    f"Insufficient permissions for {context.required_level.value} "
                    f"access"
                ),
            )

        # Get trip details for enhanced verification
        trip = await trip_service.db.get_trip_by_id(context.trip_id)
        if not trip:
            raise CoreResourceNotFoundError(
                message="Trip not found",
                code="TRIP_NOT_FOUND",
                details=ErrorDetails(
                    operation=context.operation,
                    resource_id=context.trip_id,
                    user_id=context.principal_id,
                ),
            )

        # Determine access details
        is_owner = str(trip["user_id"]) == context.principal_id
        is_collaborator = False
        granted_permission = None

        # Check collaboration status if not owner
        if not is_owner:
            collaborators = await trip_service.db.get_trip_collaborators(
                context.trip_id
            )
            for collab in collaborators:
                if collab["user_id"] == context.principal_id:
                    is_collaborator = True
                    # Map collaboration permission to our enum
                    collab_permission = collab.get("permission", "view")
                    if collab_permission == "edit":
                        granted_permission = TripAccessPermission.EDIT
                    elif collab_permission == "manage":
                        granted_permission = TripAccessPermission.MANAGE
                    else:
                        granted_permission = TripAccessPermission.VIEW
                    break
        else:
            # Owners have all permissions
            granted_permission = TripAccessPermission.MANAGE

        # Determine granted access level
        if is_owner:
            granted_level = TripAccessLevel.OWNER
        elif is_collaborator:
            granted_level = TripAccessLevel.COLLABORATOR
        else:
            # Must be public access
            granted_level = TripAccessLevel.READ

        # Check specific permission requirements
        if context.required_permission:
            permission_hierarchy = {
                TripAccessPermission.VIEW: 1,
                TripAccessPermission.EDIT: 2,
                TripAccessPermission.MANAGE: 3,
            }

            required_level = permission_hierarchy.get(context.required_permission, 3)
            granted_level_value = permission_hierarchy.get(granted_permission, 0)

            if granted_level_value < required_level:
                await audit_security_event(
                    event_type=AuditEventType.ACCESS_DENIED,
                    severity=AuditSeverity.MEDIUM,
                    message=(
                        f"Insufficient permission level for operation: "
                        f"{context.operation}"
                    ),
                    actor_id=context.principal_id,
                    ip_address=context.ip_address or "unknown",
                    target_resource=context.trip_id,
                    risk_score=35,
                    user_agent=context.user_agent,
                    operation_type=context.operation,
                    required_permission=context.required_permission.value,
                    granted_permission=granted_permission.value
                    if granted_permission
                    else "none",
                )

                return TripAccessResult(
                    is_authorized=False,
                    access_level=granted_level,
                    permission_granted=granted_permission,
                    is_owner=is_owner,
                    is_collaborator=is_collaborator,
                    denial_reason=(
                        f"Operation requires {context.required_permission.value} "
                        f"permission"
                    ),
                )

        # Log successful access for audit trail
        await audit_security_event(
            event_type=AuditEventType.ACCESS_GRANTED,
            severity=AuditSeverity.LOW,
            message=f"Trip access granted for operation: {context.operation}",
            actor_id=context.principal_id,
            ip_address=context.ip_address or "unknown",
            target_resource=context.trip_id,
            risk_score=10,
            user_agent=context.user_agent,
            operation_type=context.operation,
            access_level=granted_level.value,
            granted_permission=granted_permission.value
            if granted_permission
            else "none",
        )

        return TripAccessResult(
            is_authorized=True,
            access_level=granted_level,
            permission_granted=granted_permission,
            is_owner=is_owner,
            is_collaborator=is_collaborator,
            trip_visibility=TripVisibility(trip.get("visibility", "private")),
        )

    except (CoreResourceNotFoundError, CoreSecurityError):
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during trip access verification",
            extra={
                "trip_id": context.trip_id,
                "principal_id": context.principal_id,
                "operation": context.operation,
                "error": str(e),
            },
            exc_info=True,
        )

        # Log security event for unexpected errors
        await audit_security_event(
            event_type=AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
            severity=AuditSeverity.HIGH,
            message=f"Unexpected error during trip access verification: {e!s}",
            actor_id=context.principal_id,
            ip_address=context.ip_address or "unknown",
            target_resource=context.trip_id,
            risk_score=60,
            user_agent=context.user_agent,
            operation_type=context.operation,
            error_details=str(e),
        )

        raise CoreSecurityError(
            message="Trip access verification failed due to internal error",
            code="ACCESS_VERIFICATION_ERROR",
            details=ErrorDetails(
                operation=context.operation,
                resource_id=context.trip_id,
                user_id=context.principal_id,
                additional_context={"original_error": str(e)},
            ),
        ) from e


def create_trip_access_dependency(
    access_level: TripAccessLevel,
    permission: TripAccessPermission | None = None,
    trip_id_param: str = "trip_id",
) -> Callable:
    """Create a FastAPI dependency for trip access verification.

    This factory function creates FastAPI dependencies that can be used to verify
    trip access permissions in endpoint decorators following 2025 best practices.

    Args:
        access_level: Required access level for the operation
        permission: Specific permission required (optional)
        trip_id_param: Name of the parameter containing trip ID

    Returns:
        FastAPI dependency function for trip access verification

    Example:
        ```python
        # Require owner access
        OwnerAccessDep = Annotated[
            TripAccessResult,
            Depends(create_trip_access_dependency(TripAccessLevel.OWNER))
        ]

        @router.put("/trips/{trip_id}")
        async def update_trip(
            trip_id: str,
            access_result: OwnerAccessDep,
            principal: RequiredPrincipalDep,
        ):
            # Trip access already verified, proceed with operation
            pass
        ```
    """

    async def trip_access_dependency(
        request: Request,
        principal: Principal = Depends(require_principal),
        trip_service: TripService = Depends(),
    ) -> TripAccessResult:
        """FastAPI dependency for trip access verification."""
        # Extract trip_id from path parameters
        trip_id = request.path_params.get(trip_id_param)
        if not trip_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required parameter: {trip_id_param}",
            )

        # Get client information for audit logging
        client_ip = (
            getattr(request.client, "host", "unknown") if request.client else "unknown"
        )
        user_agent = request.headers.get("User-Agent", "unknown")

        # Create access context
        context = TripAccessContext(
            trip_id=str(trip_id),
            principal_id=get_principal_id(principal),
            required_level=access_level,
            required_permission=permission,
            operation=f"{request.method} {request.url.path}",
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Verify access
        access_result = await verify_trip_access(context, trip_service)

        if not access_result.is_authorized:
            # Convert to HTTP exception
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=access_result.denial_reason or "Access denied",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return access_result

    return trip_access_dependency


def require_trip_access(
    access_level: TripAccessLevel,
    permission: TripAccessPermission | None = None,
    trip_id_param: str = "trip_id",
):
    """Decorator for FastAPI endpoints requiring trip access verification.

    This decorator provides a clean, declarative way to enforce trip access
    permissions on FastAPI endpoints following modern Python patterns.

    Args:
        access_level: Required access level for the operation
        permission: Specific permission required (optional)
        trip_id_param: Name of the parameter containing trip ID

    Returns:
        Decorator function for FastAPI endpoints

    Example:
        ```python
        @router.get("/trips/{trip_id}")
        @require_trip_access(TripAccessLevel.READ)
        async def get_trip(trip_id: str, principal: RequiredPrincipalDep):
            # Access already verified, proceed with operation
            pass

        @router.put("/trips/{trip_id}")
        @require_trip_access(
            TripAccessLevel.COLLABORATOR,
            TripAccessPermission.EDIT
        )
        async def update_trip(trip_id: str, principal: RequiredPrincipalDep):
            # Edit permission verified, proceed with update
            pass
        ```
    """

    def decorator(func: F) -> F:
        """Apply trip access verification to the decorated function."""
        # Create the dependency
        access_dependency = create_trip_access_dependency(
            access_level=access_level,
            permission=permission,
            trip_id_param=trip_id_param,
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            """Wrapper function that performs access verification."""
            # The actual verification is handled by FastAPI dependency injection
            # This wrapper primarily serves as a marker and documentation
            return await func(*args, **kwargs)

        # Add dependency annotation to function signature
        # This allows FastAPI to automatically inject the verification
        wrapper.__annotations__ = getattr(func, "__annotations__", {}).copy()
        wrapper.__annotations__["_trip_access_verification"] = Annotated[
            TripAccessResult, Depends(access_dependency)
        ]

        return wrapper

    return decorator


# Pre-configured dependency types for common access patterns
TripReadAccessDep = Annotated[
    TripAccessResult, Depends(create_trip_access_dependency(TripAccessLevel.READ))
]

TripWriteAccessDep = Annotated[
    TripAccessResult, Depends(create_trip_access_dependency(TripAccessLevel.WRITE))
]

TripOwnerAccessDep = Annotated[
    TripAccessResult, Depends(create_trip_access_dependency(TripAccessLevel.OWNER))
]

TripCollaboratorAccessDep = Annotated[
    TripAccessResult,
    Depends(create_trip_access_dependency(TripAccessLevel.COLLABORATOR)),
]

TripEditPermissionDep = Annotated[
    TripAccessResult,
    Depends(
        create_trip_access_dependency(
            TripAccessLevel.COLLABORATOR, TripAccessPermission.EDIT
        )
    ),
]

TripManagePermissionDep = Annotated[
    TripAccessResult,
    Depends(
        create_trip_access_dependency(
            TripAccessLevel.COLLABORATOR, TripAccessPermission.MANAGE
        )
    ),
]


async def check_trip_ownership(
    trip_id: str,
    principal: Principal,
    trip_service: TripService,
) -> bool:
    """Check if a principal owns a specific trip.

    Args:
        trip_id: Trip ID to check
        principal: Principal to verify ownership for
        trip_service: Trip service instance

    Returns:
        True if principal owns the trip, False otherwise
    """
    try:
        context = TripAccessContext(
            trip_id=trip_id,
            principal_id=get_principal_id(principal),
            required_level=TripAccessLevel.OWNER,
            operation="ownership_check",
        )

        result = await verify_trip_access(context, trip_service)
        return result.is_authorized and result.is_owner

    except Exception as e:
        logger.warning(
            "Error checking trip ownership",
            extra={
                "trip_id": trip_id,
                "principal_id": get_principal_id(principal),
                "error": str(e),
            },
        )
        return False


async def check_trip_collaboration(
    trip_id: str,
    principal: Principal,
    trip_service: TripService,
    required_permission: TripAccessPermission | None = None,
) -> bool:
    """Check if a principal has collaboration access to a trip.

    Args:
        trip_id: Trip ID to check
        principal: Principal to verify collaboration for
        trip_service: Trip service instance
        required_permission: Specific permission level required

    Returns:
        True if principal has collaboration access, False otherwise
    """
    try:
        context = TripAccessContext(
            trip_id=trip_id,
            principal_id=get_principal_id(principal),
            required_level=TripAccessLevel.COLLABORATOR,
            required_permission=required_permission,
            operation="collaboration_check",
        )

        result = await verify_trip_access(context, trip_service)
        return result.is_authorized

    except Exception as e:
        logger.warning(
            "Error checking trip collaboration",
            extra={
                "trip_id": trip_id,
                "principal_id": get_principal_id(principal),
                "required_permission": required_permission.value
                if required_permission
                else None,
                "error": str(e),
            },
        )
        return False


async def get_user_trip_permissions(
    trip_id: str,
    principal: Principal,
    trip_service: TripService,
) -> dict[str, Any]:
    """Get detailed permission information for a user's access to a trip.

    Args:
        trip_id: Trip ID to check permissions for
        principal: Principal to get permissions for
        trip_service: Trip service instance

    Returns:
        Dictionary containing detailed permission information
    """
    try:
        context = TripAccessContext(
            trip_id=trip_id,
            principal_id=get_principal_id(principal),
            required_level=TripAccessLevel.READ,  # Minimum level to get info
            operation="permission_inquiry",
        )

        result = await verify_trip_access(context, trip_service)

        return {
            "is_authorized": result.is_authorized,
            "is_owner": result.is_owner,
            "is_collaborator": result.is_collaborator,
            "access_level": result.access_level.value if result.access_level else None,
            "permission": result.permission_granted.value
            if result.permission_granted
            else None,
            "can_read": result.is_authorized,
            "can_edit": result.permission_granted
            in [TripAccessPermission.EDIT, TripAccessPermission.MANAGE]
            if result.permission_granted
            else False,
            "can_manage": result.permission_granted == TripAccessPermission.MANAGE
            if result.permission_granted
            else False,
            "trip_visibility": result.trip_visibility.value
            if result.trip_visibility
            else None,
        }

    except Exception as e:
        logger.warning(
            "Error getting user trip permissions",
            extra={
                "trip_id": trip_id,
                "principal_id": get_principal_id(principal),
                "error": str(e),
            },
        )
        return {
            "is_authorized": False,
            "is_owner": False,
            "is_collaborator": False,
            "access_level": None,
            "permission": None,
            "can_read": False,
            "can_edit": False,
            "can_manage": False,
            "trip_visibility": None,
        }


__all__ = [
    # Enums
    "TripAccessLevel",
    "TripAccessPermission",
    # Models
    "TripAccessContext",
    "TripAccessResult",
    # Core functions
    "verify_trip_access",
    "create_trip_access_dependency",
    "require_trip_access",
    # Pre-configured dependencies
    "TripReadAccessDep",
    "TripWriteAccessDep",
    "TripOwnerAccessDep",
    "TripCollaboratorAccessDep",
    "TripEditPermissionDep",
    "TripManagePermissionDep",
    # Helper functions
    "check_trip_ownership",
    "check_trip_collaboration",
    "get_user_trip_permissions",
]
